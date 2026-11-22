##BizFlow 智能业务协作平台
#记忆服务：Agent 一次请求前后的记忆编排（对外统一入口）
#
# 一次请求的完整时序：
#   1. prepare_turn   —— 按「用户 + 会话」算 thread_id，登记线程归属
#                        （thread_id 就是短期记忆的边界）
#   2. 交给 LangGraph —— 历史消息由 Checkpointer 依据 thread_id 自动恢复（短期记忆），
#                        ai 节点调用模型前再把长期记忆拼到最前面（见 node/nodes.py）
#   3. 流式回答结束    —— schedule_long_term 把本轮对话丢进长期记忆专用队列，
#                        后台消费者异步抽取长期记忆并落库（见 mq_consumer.py）
#
# 也就是说，「长期记忆 + 短期记忆」的拼接发生在第 2 步：
#   短期记忆 = Checkpointer 按 thread_id 恢复出来的消息列表
#   长期记忆 = 从 ai_long_memory 里取出来、拼成的一条 SystemMessage

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from BizFlow.hdwj.LangGarph.ai_Memory.mq_producer import publish_memory_task
from BizFlow.hdwj.LangGarph.ai_Memory.short_term import build_thread_id, ensure_thread

logger = logging.getLogger(__name__)


def prepare_turn(
    db: Session, token: dict, session_id: str | None = None
) -> tuple[str, str]:
    """请求开始时的准备：返回 (thread_id, user_id)。"""
    user_id = str(token["id"])
    thread_id = build_thread_id(user_id, session_id)
    ensure_thread(db, thread_id, user_id, session_id)
    return thread_id, user_id


async def schedule_long_term(
    *,
    user_id: str,
    session_id: str | None,
    thread_id: str,
    human: str,
    ai: str,
) -> bool:
    """回答结束后，把本轮对话投递到 MQ，交给后台抽取长期记忆。"""
    return await publish_memory_task(
        user_id=user_id,
        session_id=session_id,
        thread_id=thread_id,
        human_message=human,
        ai_message=ai,
    )
