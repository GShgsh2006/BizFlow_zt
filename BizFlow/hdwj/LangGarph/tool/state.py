from typing import TypedDict, Annotated, NotRequired
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

# 统一使用 messages（复数），与 LangGraph 惯例及 apps.py 的入参保持一致
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    # 最近一次人工审核结果："approved" | "denied"（由 node/approval.py 写入）
    approval_result: NotRequired[str]
