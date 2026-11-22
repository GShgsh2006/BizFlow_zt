##BizFlow 智能业务协作平台
# 图函数：把节点组装成 LangGraph 状态图
#
# 流程：
#   START -> ai -> (route_after_ai)
#                  ├─ 无工具调用 ─────────────> END
#                  ├─ 第三方工具需要人工审核 ──> approval -> (route_after_approval)
#                  │                                ├─ 通过 -> tool -> ai
#                  │                                └─ 拒绝 -> ai（带拒绝结果的 ToolMessage）
#                  └─ 免审核工具直接执行 ──────> tool -> ai
#
# approval 节点里的 interrupt() 会把图暂停并把快照写入 Checkpointer（按 thread_id），
# 恢复走 /agent/approval（Command(resume=...)），见 LangGarph/app.py。
from langgraph.graph import StateGraph, START, END
from BizFlow.hdwj.LangGarph.tool.state import State
from BizFlow.hdwj.LangGarph.node.nodes import dall_model
from BizFlow.hdwj.LangGarph.node.approval import (
    approval_node,
    route_after_ai,
    route_after_approval,
)
from BizFlow.hdwj.LangGarph.model.model import _tool_node
# 短期记忆：编译时注入 Checkpointer，之后只要 config 里带 thread_id，
# 同一线程的多轮对话就会被自动记住并恢复。
from BizFlow.hdwj.LangGarph.ai_Memory.checkpointer import get_checkpointer
from BizFlow.hdwj.LangGarph.ai_Memory.short_term import build_thread_id


def _build_graph():
    g = StateGraph(State)
    g.add_node("ai", dall_model)
    g.add_node("approval", approval_node)
    g.add_node("tool", _tool_node)
    g.add_edge(START, "ai")
    # 第三方工具必须先过人工审核；无工具调用直接 END
    g.add_conditional_edges("ai", route_after_ai, ["approval", "tool", END])
    # 审核通过 -> 执行工具；拒绝 -> 回 ai 向用户说明
    g.add_conditional_edges(
        "approval", route_after_approval, {"tool": "tool", "ai": "ai"}
    )
    g.add_edge("tool", "ai")
    return g


_GRAPH = None


def _get_graph():
    """懒编译：官方 AsyncSqliteSaver 必须在事件循环里构造，
    所以不能放在模块导入时编译。
    """
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph().compile(checkpointer=get_checkpointer())
    return _GRAPH


# 供 LangGarph/app.py 调用的入口：把数据库会话 + 线程标识注入到 configurable 里
def pictures(db, token: dict, thread_id: str | None = None):
    name = token["role"]
    id = token["id"]
    user_id = str(id)
    config = {
        "configurable": {
            "db": db,
            "token_zw": name,
            "token_id": id,
            # 短期记忆的边界：thread_id 相同 => 同一段多轮记忆
            "thread_id": thread_id or build_thread_id(user_id),
            # ai 节点用它去取长期记忆（见 node/nodes.py）
            "user_id": user_id,
        }
    }
    return _get_graph(), config
