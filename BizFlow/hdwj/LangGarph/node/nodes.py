##BizFlow 智能业务协作平台
#节点函数
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from BizFlow.hdwj.LangGarph.model.model import get_model_with_tools
from BizFlow.hdwj.LangGarph.tool.state import State
from BizFlow.hdwj.LangGarph.ai_Memory.long_term import load_long_term_prompt

logger = logging.getLogger(__name__)


# 调用模型
# config 由 LangGraph 自动注入（函数签名里有 config: RunnableConfig 就会传）。
def dall_model(state: State, config: RunnableConfig):
    messages = state["messages"]

    # 记忆拼接：
    #   短期记忆 —— state["messages"] 里已经包含 Checkpointer 按 thread_id 恢复的历史消息
    #   长期记忆 —— 从 ai_long_memory 取出该用户的长期记忆，作为 SystemMessage 拼在最前面
    # 只在「用户这一轮刚提问」时拼（此时最后一条是 HumanMessage），
    # 工具回环时不再重复拼，避免 system 提示词被反复叠加。
    request = messages
    if messages and isinstance(messages[-1], HumanMessage):
        conf = config.get("configurable") or {}
        long_term = load_long_term_prompt(conf.get("db"), conf.get("user_id"))
        if long_term:
            request = [SystemMessage(content=long_term), *messages]

    answer = get_model_with_tools().invoke(request)
    # 每轮都打出模型是否真的发出了结构化工具调用：
    # tool_calls=无 说明这一轮不经过审核节点（模型直接文字回答，
    # 或小模型把"工具调用"写进正文而没走结构化 tool_calls）。
    tool_names = [c.get("name") for c in getattr(answer, "tool_calls", None) or []]
    logger.info(
        "ai 节点输出 | tool_calls=%s | 文本长度=%d",
        tool_names or "无",
        len(answer.content or ""),
    )
    # 直接把模型返回的 AIMessage（含 tool_calls）放回 messages，
    # 不要再用 AIMessage(content=answer) 二次包裹，否则会把对象塞进 content
    return {"messages": [answer]}

# 工具调用路由见 node/approval.py 的 route_after_ai：
# 第三方工具先过人工审核，免审核工具直接执行，无工具调用结束。
