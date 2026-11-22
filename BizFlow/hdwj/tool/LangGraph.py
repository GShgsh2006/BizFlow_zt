#LangHraph文件路由输入模板
from pydantic import BaseModel,Field


class appskk(BaseModel):
    request: str=Field(...)
    # 会话 id：同一个 session_id 复用同一个线程，就形成多轮记忆。
    # 前端不传也没关系，后端会退化成「一个用户一个线程」，一样能记住上下文。
    session_id: str | None = Field(default=None, description="会话 id，用于区分多轮对话")


class AgentApproval(BaseModel):
    """人工审核结果：/agent/approval 的请求体。

    session_id 必须与发起提问时一致，后端据此还原同一个 thread_id（快照所在线程）。
    """
    approve: bool = Field(..., description="是否同意本次第三方工具调用")
    session_id: str | None = Field(default=None, description="会话 id，与提问时保持一致")
    note: str = Field(default="", max_length=500, description="审核备注（拒绝原因会转告模型）")
    # 弹窗对应的 interrupt id：后端据此确认「这次点击针对的正是当前挂起的审核」，
    # 重复提交 / 过期弹窗会被 409 拒绝，避免误放行另一条审核
    interrupt_id: str | None = Field(default=None, description="弹窗收到的 interrupt id，原样回传")
