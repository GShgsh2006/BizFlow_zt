##BizFlow 智能业务协作平台
#人工审核闸门测试：不依赖 Ollama / MySQL / RabbitMQ
#
# 覆盖：
#   1. 第三方工具调用前图会停在 approval（interrupt）
#   2. 同意 -> 工具执行，流程正常结束
#   3. 拒绝 -> 工具不执行，模型收到"无权限"的 ToolMessage
#   4. 非法恢复值 fail-closed（按拒绝处理）

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from BizFlow.hdwj.LangGarph.node.approval import (
    APPROVED,
    DENIED,
    approval_node,
    route_after_ai,
    route_after_approval,
)
from BizFlow.hdwj.LangGarph.tool.state import State

executed = {"count": 0}


def fake_ai(state: State):
    results = [m for m in state["messages"] if isinstance(m, ToolMessage)]
    if results:
        return {"messages": [AIMessage(content=f"最终回答：{results[-1].content}")]}
    return {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "salary", "args": {"ids": 1}, "id": "call_1"}],
            )
        ]
    }


def fake_tool(state: State):
    executed["count"] += 1
    return {
        "messages": [ToolMessage("工资 100 元", tool_call_id="call_1", name="salary")]
    }


def build_graph():
    g = StateGraph(State)
    g.add_node("ai", fake_ai)
    g.add_node("approval", approval_node)
    g.add_node("tool", fake_tool)
    g.add_edge(START, "ai")
    g.add_conditional_edges("ai", route_after_ai, ["approval", "tool", END])
    g.add_conditional_edges(
        "approval", route_after_approval, {"tool": "tool", "ai": "ai"}
    )
    g.add_edge("tool", "ai")
    return g.compile(checkpointer=InMemorySaver())


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


async def _flush(graph, graph_input, config) -> None:
    async for _chunk in graph.astream(
        graph_input, config=config, stream_mode="updates"
    ):
        pass


@pytest.mark.asyncio
async def test_third_party_tool_pauses_for_approval():
    graph = build_graph()
    config = _config("ask-approval")
    await _flush(graph, {"messages": [HumanMessage("查工资")]}, config)

    snapshot = await graph.aget_state(config)
    assert snapshot.next == ("approval",)
    assert snapshot.interrupts
    payload = snapshot.interrupts[0].value
    assert payload["type"] == "tool_approval"
    assert payload["requests"][0]["tool"] == "salary"
    assert executed["count"] == 0


@pytest.mark.asyncio
async def test_approve_runs_tool_and_finishes():
    executed["count"] = 0
    graph = build_graph()
    config = _config("approve")
    await _flush(graph, {"messages": [HumanMessage("查工资")]}, config)
    await _flush(graph, Command(resume={"approve": True}), config)

    snapshot = await graph.aget_state(config)
    assert snapshot.next == ()
    assert snapshot.values["approval_result"] == APPROVED
    assert executed["count"] == 1
    assert "最终回答" in snapshot.values["messages"][-1].content


@pytest.mark.asyncio
async def test_deny_blocks_tool_and_explains():
    executed["count"] = 0
    graph = build_graph()
    config = _config("deny")
    await _flush(graph, {"messages": [HumanMessage("查工资")]}, config)
    await _flush(graph, Command(resume={"approve": False, "note": "金额不对"}), config)

    snapshot = await graph.aget_state(config)
    assert snapshot.values["approval_result"] == DENIED
    assert executed["count"] == 0
    tool_messages = [
        m for m in snapshot.values["messages"] if isinstance(m, ToolMessage)
    ]
    assert tool_messages and "无权限" in tool_messages[0].content
    assert "金额不对" in tool_messages[0].content
    assert "最终回答" in snapshot.values["messages"][-1].content


@pytest.mark.asyncio
async def test_invalid_resume_value_fails_closed():
    executed["count"] = 0
    graph = build_graph()
    config = _config("bad-resume")
    await _flush(graph, {"messages": [HumanMessage("查工资")]}, config)
    await _flush(graph, Command(resume={"approve": "yes"}), config)

    snapshot = await graph.aget_state(config)
    assert snapshot.values["approval_result"] == DENIED
    assert executed["count"] == 0
