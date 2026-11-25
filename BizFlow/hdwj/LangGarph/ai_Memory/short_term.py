##BizFlow 智能业务协作平台
#短期记忆：thread_id 会话管理
#
# 短期记忆 = 「当前这个会话里的聊天记录」，边界由 LangGraph 的 thread_id 决定：
#   同一个 thread_id 反复调用多轮，LangGraph 会自动从 Checkpointer 里
#   把上一次的消息读回来，再叠加这一轮的输入 —— 这就是多轮记忆。
#
# 这里负责三件小事：
#   build_thread_id  按「用户 + 会话」算 thread_id
#   ensure_thread    第一次用到某个 thread 时，把归属登记到 ai_ckpt_threads
#   thread_owner     反查 thread 属于谁（长期记忆消费者用来校验任务归属）
#   load_history     手动取某个 thread 的历史消息（排查 / 复用）

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from BizFlow.hdwj.LangGarph.ai_Memory.checkpointer import get_checkpointer
from BizFlow.shujuku.user import AiCkptThread

logger = logging.getLogger(__name__)


def build_thread_id(user_id: Any, session_id: str | None = None) -> str:
    """算 thread_id。

    每个会话一个线程：传了 session_id 就是「用户 + 会话」，
    没传（前端还没改造）就退化成「一个用户一个线程」，也能跑出多轮记忆。
    """
    if session_id:
        return f"u{user_id}-s{session_id}"
    return f"u{user_id}"


def ensure_thread(
    db: Session,
    thread_id: str,
    user_id: Any,
    session_id: str | None = None,
) -> None:
    """登记 thread 归属；已存在就只刷新会话信息。"""
    row = db.query(AiCkptThread).filter(AiCkptThread.thread_id == thread_id).first()
    if row is not None:
        row.user_id = str(user_id)
        if session_id and row.session_id != session_id:
            row.session_id = session_id
        db.commit()
        return

    db.add(
        AiCkptThread(
            thread_id=thread_id,
            user_id=str(user_id),
            session_id=session_id,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        # 并发请求同时第一次进来，另一个已经把行插好了，忽略即可
        db.rollback()


def thread_owner(db: Session, thread_id: str | None) -> str | None:
    """反查 thread 属于哪个用户；查不到返回 None。"""
    if not thread_id:
        return None
    row = db.query(AiCkptThread).filter(AiCkptThread.thread_id == thread_id).first()
    return str(row.user_id) if row is not None else None


async def load_history(thread_id: str) -> list[Any]:
    """手动读取某个线程最近一次 checkpoint 里的 messages（短期记忆的原始形态）。

    AsyncSqliteSaver 只有异步接口，所以这里也只能是 async。
    """
    tup = await get_checkpointer().aget_tuple(
        {"configurable": {"thread_id": thread_id}}
    )
    if tup is None:
        return []
    values = tup.checkpoint.get("channel_values") or {}
    values_sxw=list(values.get("messages") or [])
    context=values_sxw[-5:]
    return context
