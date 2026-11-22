##BizFlow 智能业务协作平台
#长期记忆任务的 MQ 生产端
#
# 用户这一轮 AI 回答结束后，把「用户消息 + AI 回答」投递到长期记忆专用队列，
# 由后台消费者异步抽取长期记忆并落库 —— 不阻塞用户的响应。
#
# 说明：
#   * 长期记忆走独立队列 app.memory.queue（路由键 task.memory），
#     不占用业务任务队列 app.task.queue；
#   * 消息体里带 hanshu_name 标识 + user_id，消费者按 user_id 校验任务归属。

from __future__ import annotations

import logging
import uuid

from BizFlow.hdwj.mq.bootstrap import ensure_started
from BizFlow.hdwj.mq.config import settings
from BizFlow.hdwj.mq.message import message
from BizFlow.hdwj.LangGarph.ai_Memory.mq_consumer import MEMORY_HANDLER_NAME

logger = logging.getLogger(__name__)


async def publish_memory_task(
    *,
    user_id: str,
    session_id: str | None,
    thread_id: str,
    human_message: str,
    ai_message: str,
) -> bool:
    """把本轮对话投递到长期记忆专用队列，返回是否投递成功。

    MQ 没起来 / 投递失败都只记日志返回 False：
    长期记忆是「锦上添花」，绝不能因为它把用户的回答搞失败。
    """
    body = {
        "task_id": uuid.uuid4().hex,
        "user_id": str(user_id),
        "session_id": session_id,
        "thread_id": thread_id,
        "human": human_message or "",
        "ai": ai_message or "",
    }

    try:
        channel = await ensure_started()
        # key_dl 是路由键（决定进哪个队列），key 是日志用的 hanshu_name
        await message(
            body,
            settings.MQ_MEMORY_ROUTING_KEY,
            MEMORY_HANDLER_NAME,
            settings.task_queue_jg_key,
            channel,
        )
        return True
    except Exception as e:
        logger.warning("长期记忆任务投递失败（不影响本次回答）: %s", e)
        return False
