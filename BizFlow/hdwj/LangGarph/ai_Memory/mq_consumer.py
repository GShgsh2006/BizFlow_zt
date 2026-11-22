##BizFlow 智能业务协作平台
#长期记忆 MQ 消费端（独立队列 + 独立消费者）
#
# 长期记忆任务不走业务任务队列 app.task.queue：
#   mq_producer 投递到 task.memory -> app.memory.queue
#   本模块的 start_memory_consumer() 在 app.memory.queue 上监听
#   收到消息后调 ai_memory_save() 抽取长期记忆并写进 ai_long_memory
#
# 这类任务纯后台写库，没有等待结果的调用方，所以不回传结果消息；
# 执行统计写入 worker.STATS，/mq/status 仍能看到它。

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from aio_pika import IncomingMessage

from BizFlow.hdwj.LangGarph.ai_Memory.long_term import extract_memories, save_memories
from BizFlow.hdwj.LangGarph.ai_Memory.short_term import thread_owner
from BizFlow.hdwj.mq.config import settings
from BizFlow.hdwj.mq.topologt import exchange
from BizFlow.hdwj.mq.worker import STATS
from BizFlow.shujuku.Management import SessionLocal

logger = logging.getLogger(__name__)

# 消息体里的任务标识（日志 / 前端状态展示用）
MEMORY_HANDLER_NAME = "ai_memory_save"


async def ai_memory_save(zd: dict) -> dict:
    """长期记忆任务的执行函数。

    zd 里应该带：user_id / thread_id / session_id / human / ai
    """
    user_id = str(zd.get("user_id") or "")
    thread_id = zd.get("thread_id")
    session_id = zd.get("session_id")
    human_message = zd.get("human") or ""
    ai_message = zd.get("ai") or ""

    if not user_id:
        logger.warning("长期记忆任务缺少 user_id，已丢弃")
        return {"saved": 0, "skipped": "missing_user_id"}

    if not ai_message:
        logger.info("长期记忆任务没有 AI 回答内容，跳过")
        return {"saved": 0, "skipped": "empty_answer"}

    db = SessionLocal()
    try:
        # ---- 校验任务归属：这个 thread 是不是这个用户的 ----
        owner = thread_owner(db, thread_id)
        if owner is not None and owner != user_id:
            logger.warning(
                "长期记忆任务归属校验失败，已丢弃：任务 user_id=%s，线程归属=%s",
                user_id,
                owner,
            )
            return {"saved": 0, "skipped": "owner_mismatch"}

        # ---- 抽取（本地模型是阻塞调用，丢线程池，别卡住 MQ 消费者的循环） ----
        memories = await asyncio.to_thread(extract_memories, human_message, ai_message)

        saved = save_memories(
            db,
            user_id=user_id,
            session_id=session_id,
            thread_id=thread_id,
            memories=memories,
            human_message=human_message,
            ai_message=ai_message,
        )
        if saved:
            logger.info("长期记忆已写入 %s 条：user_id=%s", saved, user_id)
        return {"saved": saved}
    finally:
        db.close()


async def handle_memory_message(message: IncomingMessage) -> None:
    """app.memory.queue 的消费回调：解析 -> 执行 -> ack（失败进死信）。"""
    async with message.process(requeue=False):
        try:
            data = json.loads(message.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("长期记忆消息不是有效的 UTF-8 JSON") from exc

        if not isinstance(data, dict):
            raise ValueError("长期记忆消息体必须是一个字典对象")

        task_id = data.get("task_id")
        if not task_id:
            raise ValueError("长期记忆消息缺少 task_id")

        STATS["received"] += 1
        STATS["processing"] += 1
        STATS["last_handler"] = MEMORY_HANDLER_NAME
        STATS["last_task_id"] = task_id
        STATS["last_time"] = datetime.now().isoformat(timespec="seconds")

        try:
            result = await ai_memory_save(data)
        except Exception:
            STATS["failed"] += 1
            logger.exception("长期记忆任务执行失败，task_id=%s", task_id)
            raise
        else:
            STATS["success"] += 1
            logger.info("长期记忆任务执行成功，task_id=%s，结果=%s", task_id, result)
        finally:
            STATS["processing"] -= 1


async def start_memory_consumer(channel) -> None:
    """在长期记忆专用队列上启动消费者。"""
    topo = await exchange(channel)

    await topo["memory_queue"].consume(handle_memory_message)

    logger.info(
        "长期记忆消费者已启动：queue=%s, routing_key=%s",
        settings.MQ_MEMORY_QUEUE,
        settings.MQ_MEMORY_ROUTING_KEY,
    )
