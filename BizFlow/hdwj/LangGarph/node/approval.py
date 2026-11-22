##BizFlow 智能业务协作平台
#人工审核闸门：AI 调用第三方工具前必须经过人工审批（interrupt / resume）
#
# 图结构（见 picture/pictureaa.py）：
#   ai ──route_after_ai──> approval ──route_after_approval──> tool -> ai
#                │                                          └> ai（拒绝，携带 ToolMessage 说明）
#                ├> tool（免审核工具，白名单外自动放行）
#                └> END（没有工具调用）
#
# 机制：interrupt(payload) 抛出中断，图暂停并把快照写入 Checkpointer（按 thread_id）。
# 前端拿到 payload 弹窗审批，恢复时用 Command(resume={"approve": ...}) 重新进入本节点，
# interrupt() 直接返回恢复值、不再暂停；已完成的节点由快照直接跳过。
# 注意：恢复时本节点会从头重跑，interrupt() 之前只做纯计算，不要放副作用。

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.types import interrupt

from BizFlow.hdwj.LangGarph.tool.state import State
from BizFlow.hdwj.LangGarph.tool.tools import tools

logger = logging.getLogger(__name__)

# 前端展示文案：工具名 -> 中文名（SSE 事件与审核弹窗共用同一份映射）
TOOL_LABELS: dict[str, str] = {
    "yyxx": "年假查询",
    "salary": "工资查询",
    "distribute": "任务分配",
}

# 审核策略：当前接入的第三方工具全部需要人工审核。
# 将来新增内部工具时，不在本集合里的工具由 route_after_ai 自动放行。
APPROVAL_REQUIRED_TOOLS: frozenset[str] = frozenset(t.name for t in tools)

# approval_result 的取值，写入 State 供 route_after_approval 路由
APPROVED = "approved"
DENIED = "denied"

# 拒绝时回填给模型的工具结果：让模型据此向用户解释，历史不会停在半截工具调用上
_DENIED_TOOL_CONTENT = (
    "【人工审核未通过】用户拒绝授权调用第三方工具「{tool}」，本次调用无权限执行。"
    "请告知用户该操作未获授权。{note}"
)


def _describe_tool_calls(message: AIMessage) -> list[dict[str, Any]]:
    """把 AIMessage.tool_calls 转成前端弹窗需要的结构（必须可 JSON 序列化）。"""
    requests: list[dict[str, Any]] = []
    for call in message.tool_calls or []:
        name = call.get("name") or ""
        requests.append(
            {
                "tool": name,
                "label": TOOL_LABELS.get(name, name),
                "args": call.get("args") or {},
                "tool_call_id": call.get("id"),
            }
        )
    return requests


def route_after_ai(state: State) -> str:
    """ai 节点之后的路由：无工具调用结束；第三方工具先审核；免审核工具直接执行。"""
    last = state["messages"][-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    if not tool_calls:
        return END
    names = {call.get("name") for call in tool_calls}
    if names & APPROVAL_REQUIRED_TOOLS:
        return "approval"
    return "tool"


def approval_node(state: State, config: RunnableConfig) -> dict:
    """人工审核节点：interrupt 暂停图，等待前端提交审核结果。

    恢复值约定：
      {"approve": True}                  -> 放行，路由到 tool
      {"approve": False, "note": "..."}  -> 拒绝，回填无权限的 ToolMessage 并交回 ai 解释
    缺失或不合法的恢复值一律按拒绝处理（fail-closed）。
    """
    thread_id = (config.get("configurable") or {}).get("thread_id")
    last = state["messages"][-1]
    requests = _describe_tool_calls(last)

    payload = {
        "type": "tool_approval",
        "message": "AI 请求调用第三方工具，需要人工审核",
        "requests": requests,
    }
    decision = interrupt(payload)

    tool_names = ", ".join(req["tool"] for req in requests)
    if isinstance(decision, dict) and decision.get("approve") is True:
        logger.info("人工审核通过 | thread=%s | tools=%s", thread_id, tool_names)
        return {"approval_result": APPROVED}

    note = ""
    if isinstance(decision, dict):
        note = str(decision.get("note") or "").strip()
    logger.warning(
        "人工审核拒绝 | thread=%s | tools=%s | note=%s",
        thread_id,
        tool_names,
        note or "无",
    )

    denied_messages = [
        ToolMessage(
            content=_DENIED_TOOL_CONTENT.format(
                tool=req["tool"],
                note=f"（审核备注：{note}）" if note else "",
            ),
            tool_call_id=req["tool_call_id"] or "unknown",
            name=req["tool"],
        )
        for req in requests
    ]
    return {"approval_result": DENIED, "messages": denied_messages}


def route_after_approval(state: State) -> str:
    """审核之后的路由：通过 -> 执行工具；拒绝 -> 回到 ai 向用户说明。"""
    return "tool" if state.get("approval_result") == APPROVED else "ai"
