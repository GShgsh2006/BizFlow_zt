from BizFlow.hdwj.LangGarph.tool.tools import tools
from langgraph.prebuilt import ToolNode
from BizFlow.hdwj.Exception.exceptions import hdwjException
from fastapi import HTTPException
# 模型懒构建：导入路由时不碰 langchain_ollama，
# 否则本机代理环境 / 未装 ollama 都会让整个 Agent 路由导入失败。
_model_with_tools = None


def get_model_with_tools():
    global _model_with_tools
    if _model_with_tools is None:
        # 复用 lifespan 里初始化好的模型单例，避免重复创建/重复加载
        from BizFlow.hdwj.AI.RAG.model import get_llm

        _model_with_tools = get_llm().bind_tools(tools)
        if _model_with_tools is None:
            raise hdwjException(404,"模型连接失败请重新尝试")
    return _model_with_tools


_tool_node = ToolNode(tools)
