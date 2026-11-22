##BizFlow 智能业务协作平台
#长期记忆：用本地模型从一轮对话里抽取出「值得跨会话记住」的用户信息，并落库
#
# 这一层只做「抽取 + 读写」，
# 抽取动作由 MQ 消费者在后台触发（见 mq_consumer.py），不占用用户这次请求的响应时间。
#
# 与短期记忆的区别：
#   短期记忆 = 某个会话的原始聊天记录（由 Checkpointer 存，按 thread_id 取）
#   长期记忆 = 从聊天里提炼出来的、和会话无关的用户事实（本文件，按 user_id 取）

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from BizFlow.shujuku.user import AiLongMemory

logger = logging.getLogger(__name__)

# 抽取用的小模型：只做信息提取，不需要大模型；
# 拉不到模型也没关系，抽取失败只会「这一轮没记下东西」，不影响用户回答。
_EXTRACT_MODEL = "qwen3:1.7b"

_EXTRACT_PROMPT = """你负责从用户和 AI 的本轮对话中，提取值得长期保存的信息。

提取规则：
1. 只提取关于用户本人的、未来对话里还用得上的信息。
2. 优先提取长期目标、稳定偏好、项目情况、学习进度、身份信息等。
3. 不要提取普通知识问答、临时问题、无长期价值的信息。
4. 不要把 AI 自己说的话当成用户事实。
5. 不确定的信息不要提取。
6. 没有值得保存的信息时，返回空列表。

只输出 JSON，格式：
{"memories": ["...", "..."]}
"""

_llm: Any = None


def _get_llm():
    """惰性创建模型：导入模块时不碰 ollama，抽取失败只影响本轮记忆。"""
    global _llm
    if _llm is None:
        from langchain_ollama import ChatOllama

        _llm = ChatOllama(
            model=_EXTRACT_MODEL,
            temperature=0.0,
            format="json",
        )
    return _llm


def extract_memories(human_message: str, ai_message: str) -> list[str]:
    """让本地模型从本轮对话里抽取长期记忆；任何失败都返回空列表，不往外抛。"""
    prompt = f"用户消息：\n{human_message}\n\nAI 回答：\n{ai_message}"
    try:
        result = _get_llm().invoke(
            [
                SystemMessage(content=_EXTRACT_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
    except Exception as e:
        logger.warning("长期记忆抽取失败（跳过本轮）: %s", e)
        return []

    return _parse_memories(getattr(result, "content", result))


def _parse_memories(raw: Any) -> list[str]:
    """把模型输出解析成字符串列表；模型不听话时尽量兜底，兜不住就返回空。"""
    if not isinstance(raw, str):
        raw = str(raw or "")
    text = raw.strip()
    if not text:
        return []

    # 去掉 ```json ... ``` 这种包裹
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text[:4].lower() == "json":
            text = text[4:].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end <= start:
            # 退化成按行取，去掉常见的前缀符号
            return [
                line.strip(" -•*\t")
                for line in text.splitlines()
                if line.strip(" -•*\t")
            ][:10]
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return []

    if isinstance(data, dict):
        data = data.get("memories") or data.get("memory") or []
    if isinstance(data, str):
        data = [data]
    if not isinstance(data, list):
        return []

    return [str(item).strip() for item in data if str(item).strip()]


def save_memories(
    db: Session,
    *,
    user_id: Any,
    session_id: str | None,
    thread_id: str | None,
    memories: list[str],
    human_message: str,
    ai_message: str,
) -> int:
    """把抽取结果写进 ai_long_memory，返回实际新增条数（同一用户重复内容会跳过）。"""
    if not memories:
        return 0

    user_id_str = str(user_id)
    existed = {
        row[0]
        for row in db.query(AiLongMemory.memory)
        .filter(AiLongMemory.user_id == user_id_str)
        .all()
    }

    now = datetime.now()
    saved = 0
    for memory in memories:
        if memory in existed:
            continue
        db.add(
            AiLongMemory(
                user_id=user_id_str,
                session_id=session_id,
                thread_id=thread_id,
                memory=memory,
                source_human=(human_message or "")[:1000],
                source_ai=(ai_message or "")[:1000],
                created_at=now,
            )
        )
        existed.add(memory)
        saved += 1

    if saved:
        db.commit()
    return saved


def load_long_term_prompt(
    db: Session | None, user_id: Any, limit: int = 20
) -> str | None:
    """取这个用户最近 limit 条长期记忆，拼成一段可直接放进 system prompt 的文字。

    没有记忆时返回 None，调用方据此决定不拼 system 消息。
    """
    if db is None or user_id is None:
        return None

    try:
        rows = (
            db.query(AiLongMemory.memory)
            .filter(AiLongMemory.user_id == str(user_id))
            .order_by(AiLongMemory.id.desc())
            .limit(limit)
            .all()
        )
    except Exception as e:
        # 表还没建出来（迁移没跑）等情况，不能让 AI 调用跟着挂
        logger.warning("读取长期记忆失败，本轮不拼接长期记忆: %s", e)
        return None

    items = [row[0] for row in reversed(rows)]
    if not items:
        return None

    lines = "\n".join(f"- {item}" for item in items)
    return (
        "以下是你在此前与该用户的对话中记住的长期记忆，"
        f"回答时请自然地结合（不要逐条复述）：\n{lines}"
    )
