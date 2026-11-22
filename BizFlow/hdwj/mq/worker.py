# mq/worker.py
# 任务消费者：收消息 -> 调业务函数 -> 回传结果

import json
import logging
from datetime import datetime

import aio_pika
from aio_pika import IncomingMessage
from sqlalchemy.orm import Session

from BizFlow.hdwj.mq.config import settings
from BizFlow.hdwj.mq.topologt import exchange
from BizFlow.hdwj.function.query import query_dsz
from BizFlow.shujuku.user import mq_mdj
logger = logging.getLogger(__name__)

# 实时统计，供 /mq/status 给前端展示后台任务的执行情况。
# 业务 worker、长期记忆消费者与路由在同一进程，模块级字典可以直接共享。
STATS = {
    "received": 0,
    "success": 0,
    "failed": 0,
    "processing": 0,
    "last_handler": None,
    "last_task_id": None,
    "last_time": None,
}

# 任务标识与业务函数的映射关系
# 长期记忆不走这里：它有独立队列 app.memory.queue 和独立消费者（见 ai_Memory/mq_consumer.py）
TASK_HANDLERS = {
    "query_dsz": query_dsz,
}


async def _publish_result(channel, routing_key: str, payload: dict) -> None:
    topo = await exchange(channel)
    try:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("业务函数返回结果无法序列化为 JSON") from exc

    await topo["exchange"].publish(
        aio_pika.Message(
            body=body,
            content_type="application/json",
            content_encoding="utf-8",
        ),
        routing_key=routing_key,
        mandatory=True,
    )


async def process_message(message: IncomingMessage) -> None:
    """接收消息、查找函数、执行任务并发送结果"""

    channel = message.channel

    async with message.process(requeue=False):
        try:
            data = json.loads(message.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("消息体不是有效的 UTF-8 JSON 数据") from exc

        if not isinstance(data, dict):
            raise ValueError("消息体必须是一个字典对象")

        task_id = data.get("task_id")
        key = data.get("hanshu_name")
        result_key = data.get("result_key") or settings.task_queue_jg_key

        if not task_id:
            raise ValueError("消息体缺少 task_id")

        if not isinstance(key, str) or not key:
            raise ValueError("消息体缺少有效的 hanshu_name")

        logger.info("收到任务，task_id=%s，hanshu_name=%s", task_id, key)

        handler = TASK_HANDLERS.get(key)

        STATS["received"] += 1
        STATS["processing"] += 1
        STATS["last_handler"] = key
        STATS["last_task_id"] = task_id
        STATS["last_time"] = datetime.now().isoformat(timespec="seconds")

        try:
            if handler is None:
                raise ValueError(f"没有找到对应的任务处理函数：{key}")
            result = await handler(data)
        except Exception as exc:
            STATS["failed"] += 1
            logger.exception("任务执行失败，task_id=%s，hanshu_name=%s", task_id, key)
            # 把失败结果回传给等待中的路由，避免前端一直等到超时
            try:
                await _publish_result(
                    channel,
                    result_key,
                    {"task_id": task_id, "success": False, "error": str(exc)},
                )
            except Exception:
                logger.exception("失败结果回传失败，task_id=%s", task_id)
            raise
        else:
            STATS["success"] += 1
        finally:
            STATS["processing"] -= 1

        logger.info("任务执行成功，task_id=%s，hanshu_name=%s", task_id, key)

        # 键名必须和 ggwj/jgdl.py 里的 handle_result 对齐
        await _publish_result(
            channel,
            result_key,
            {"task_id": task_id, "success": True, "data": result},
        )
#幂等性
# from BizFlow.hdwj.mq.bootstrap import ensure_started
# async def worker_cs(message: IncomingMessage,db:Session) -> None:
#     data = json.loads(message.body.decode("utf-8"))
#     taskid=data["task_id"]
#     a=db.query(mq_mdj).filter(mq_mdj.task_id == taskid).first()
#     if a and a.zhuangtai=="success":
#         return
#     else:
#       channel= await ensure_started()
#       await start_worker(channel)


async def start_worker(channel) -> None:
    topo = await exchange(channel)

    await topo["task_queue"].consume(process_message)

    logger.info(
        "Worker 已启动，正在监听任务队列：%s，已注册任务：%s",
        settings.MQ_TASK_QUEUE,
        ", ".join(sorted(TASK_HANDLERS)),
    )
