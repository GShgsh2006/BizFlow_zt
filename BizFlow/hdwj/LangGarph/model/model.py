from BizFlow.hdwj.LangGarph.tool.tools import tools
from langgraph.prebuilt import ToolNode

# 模型懒构建：导入路由时不碰 langchain_ollama，
# 否则本机代理环境 / 未装 ollama 都会让整个 Agent 路由导入失败。
_model_with_tools = None


def get_model_with_tools():
    global _model_with_tools
    if _model_with_tools is None:
        from langchain_ollama import ChatOllama

        model = ChatOllama(
            model="qwen3:1.7b",
            temperature=0.7,
        )
        _model_with_tools = model.bind_tools(tools)
    return _model_with_tools


_tool_node = ToolNode(tools)
