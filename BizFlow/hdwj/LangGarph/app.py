#BizFlow 智能业务协作平台
#Agent大脑后端函数（SSE 流式返回）
#
# 两个入口共用同一张图和同一个 thread_id：
#   apps()         首次运行；图跑到 approval 节点的 interrupt() 时暂停并落快照
#   resume_apps()  人工审核后恢复运行（Command(resume=...)），从中断点继续执行
import json
import logging
from typing import Any, AsyncIterator

from fastapi import HTTPException
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from BizFlow.hdwj.LangGarph.picture.pictureaa import pictures
from BizFlow.hdwj.LangGarph.node.approval import TOOL_LABELS
from BizFlow.hdwj.LangGarph.ai_Memory.memory_service import (
    prepare_turn,
    schedule_long_term,
)
from BizFlow.hdwj.LangGarph.ai_Memory.short_term import load_history
from BizFlow.hdwj.tool.LangGraph import AgentApproval

logger = logging.getLogger(__name__)


def _sse(payload: dict) -> str:
    return f"data:{json.dumps(payload, ensure_ascii=False)}\n\n"


def _events_from_chunk(
    mode: str, payload: Any, announced_tools: set[str]
) -> list[dict]:
    """把 LangGraph 的流块翻译成前端 SSE 事件（纯函数，两个入口共用）。"""
    if mode == "messages":
        chunk, metadata = payload
        node = metadata.get("langgraph_node") if isinstance(metadata, dict) else None
        if node != "ai":
            return []
        events: list[dict] = []
        calls = list(getattr(chunk, "tool_call_chunks", None) or [])
        calls += list(getattr(chunk, "tool_calls", None) or [])
        for call in calls:
            name = (
                call.get("name")
                if isinstance(call, dict)
                else getattr(call, "name", None)
            )
            if name and name not in announced_tools:
                announced_tools.add(name)
                events.append(
                    {
                        "type": "tool_start",
                        "tool": name,
                        "label": TOOL_LABELS.get(name, name),
                    }
                )
        content = getattr(chunk, "content", "")
        if content:
            events.append({"type": "content", "content": content})
        return events

    if mode != "updates" or not isinstance(payload, dict):
        return []

    events = []
    # 人工审核：图暂停，interrupt 的 payload 原样交给前端弹窗
    for item in payload.get("__interrupt__") or []:
        value = getattr(item, "value", None)
        if isinstance(value, dict):
            events.append(
                {
                    "type": "approval_required",
                    "payload": value,
                    "interrupt_id": getattr(item, "id", None),
                }
            )
    # approval 节点写回审核结果：approved / denied
    approval_update = payload.get("approval")
    if isinstance(approval_update, dict) and approval_update.get("approval_result"):
        events.append(
            {"type": "approval_result", "result": approval_update["approval_result"]}
        )
    # ToolNode 执行完成：updates 里会出现 {"tool": {"messages": [ToolMessage...]}}
    tool_update = payload.get("tool")
    if isinstance(tool_update, dict):
        for msg in tool_update.get("messages") or []:
            name = getattr(msg, "name", None) or "tool"
            events.append(
                {"type": "tool_end", "tool": name, "label": TOOL_LABELS.get(name, name)}
            )
    return events


async def _stream_turn(
    graph: CompiledStateGraph,
    config: RunnableConfig,
    graph_input: Any,
    collected: list[str],
) -> AsyncIterator[dict]:
    """跑一轮图，把流块翻译成事件；顺带收集回答正文（长期记忆用）。"""
    announced_tools: set[str] = set()
    async for mode, payload in graph.astream(
        graph_input,
        config=config,
        stream_mode=["messages", "updates"],
    ):
        for event in _events_from_chunk(mode, payload, announced_tools):
            if event["type"] == "content":
                collected.append(event["content"])
            yield event


async def _is_paused(graph: CompiledStateGraph, config: RunnableConfig) -> bool:
    """图是否停在 interrupt 上等人工审核（快照里 next 非空即未完成）。"""
    snapshot = await graph.aget_state(config)
    return bool(snapshot.next)


async def _mq_event(
    *,
    user_id: str,
    session_id: str | None,
    thread_id: str,
    human: str,
    ai: str,
) -> dict:
    """回答结束后把本轮对话投递到 MQ，由后台消费者异步抽取长期记忆。

    投递失败只记日志，绝不影响本次回答（schedule_long_term 内部已有兜底）。
    """
    delivered = False
    try:
        delivered = await schedule_long_term(
            user_id=user_id,
            session_id=session_id,
            thread_id=thread_id,
            human=human,
            ai=ai,
        )
    except Exception as e:
        logger.warning("长期记忆任务投递异常（不影响回答）: %s", e)

    return {
        "type": "mq",
        "stage": "queued" if delivered else "skipped",
        "content": (
            "长期记忆任务已投递 MQ，后台正在抽取"
            if delivered
            else "MQ 未连接，本轮长期记忆任务未提交"
        ),
    }


async def apps(request: str, db: Session, token: dict, session_id: str | None = None):
    thread_id, user_id = prepare_turn(db, token, session_id)

    graph, config = pictures(db, token, thread_id=thread_id)
    collected: list[str] = []
    async for event in _stream_turn(
        graph, config, {"messages": [HumanMessage(request)]}, collected
    ):
        yield _sse(event)

    # 图停在人工审核点：本轮记忆由 resume_apps 恢复结束时提交，避免写入半截对话
    if await _is_paused(graph, config):
        return

    yield _sse(
        await _mq_event(
            user_id=user_id,
            session_id=session_id,
            thread_id=thread_id,
            human=request,
            ai="".join(collected),
        )
    )


async def resume_apps(
    approval: AgentApproval, db: Session, token: dict
) -> AsyncIterator[str]:
    """人工审核后恢复图运行。

    没有等待审核的操作时在返回流之前抛 409（前端据提示刷新/重新提问）。
    """
    thread_id, user_id = prepare_turn(db, token, approval.session_id)
    graph, config = pictures(db, token, thread_id=thread_id)

    snapshot = await graph.aget_state(config)
    pending_ids = {item.id for item in snapshot.interrupts}

    # 前端带了 interrupt_id：必须与当前挂起的审核精确匹配。
    # 不匹配说明这次点击对应的审核已被消费（重复提交/过期弹窗），
    # 直接放行可能把确认误用到另一条审核上，因此拒绝。
    if approval.interrupt_id:
        if approval.interrupt_id not in pending_ids:
            raise HTTPException(
                status_code=409, detail="该审核已处理或已过期，请刷新页面后重试"
            )
    elif not pending_ids:
        raise HTTPException(status_code=409, detail="当前没有等待人工审核的操作")

    return _resume_stream(graph, config, approval, thread_id, user_id)


async def _resume_stream(
    graph: CompiledStateGraph,
    config: RunnableConfig,
    approval: AgentApproval,
    thread_id: str,
    user_id: str,
) -> AsyncIterator[str]:
    collected: list[str] = []
    resume_value = {"approve": approval.approve, "note": approval.note}
    async for event in _stream_turn(
        graph, config, Command(resume=resume_value), collected
    ):
        yield _sse(event)

    # 审核通过后模型可能又发起另一批工具调用，图会再次暂停：继续等下一次审核
    if await _is_paused(graph, config):
        return

    # 恢复请求没有用户原文，从快照历史里取本轮最后一条 HumanMessage
    human = ""
    try:
        history = await load_history(thread_id)
        human = next(
            (m.content for m in reversed(history) if isinstance(m, HumanMessage)),
            "",
        )
    except Exception as e:
        logger.warning("读取线程历史失败（长期记忆降级为空输入）: %s", e)

    yield _sse(
        await _mq_event(
            user_id=user_id,
            session_id=approval.session_id,
            thread_id=thread_id,
            human=human,
            ai="".join(collected),
        )
    )
