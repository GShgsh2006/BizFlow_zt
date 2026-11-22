
import asyncio
import json
import logging

from aio_pika import IncomingMessage

from BizFlow.hdwj.mq.config import settings
from BizFlow.hdwj.mq.topologt import exchange

logger = logging.getLogger(__name__)

# task_id -> Future
futures: dict[str, asyncio.Future] = {}


def create_future(task_id: str) -> asyncio.Future:
    """创建 Future，并保存任务 ID 与 Future 的对应关系。"""
    loop = asyncio.get_running_loop()

    if task_id in futures:
        raise ValueError(f"重复的任务 ID：{task_id}")

    future = loop.create_future()
    futures[task_id] = future

    return future


async def handle_result(message: IncomingMessage) -> None:
    """公共结果监听器处理每一条返回消息。"""

    async with message.process():
        try:
            result = json.loads(message.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.error("结果消息不是有效的 JSON，已丢弃")
            return

        task_id = result.get("task_id")

        if not task_id:
            logger.error("结果消息缺少 task_id")
            return

        future = futures.get(task_id)

        if future is None:
            logger.warning("未找到对应的 Future：%s", task_id)
            return

        if future.done():
            logger.warning("Future 已完成：%s", task_id)
            futures.pop(task_id, None)
            return

        if result.get("success", True):
            future.set_result(result.get("data"))
        else:
            future.set_exception(
                RuntimeError(
                    result.get("error", "Worker 执行任务失败")
                )
            )

        futures.pop(task_id, None)


async def start_result_listener(channel) -> None:
    """在结果队列上启动公共监听（队列/绑定由 topology 统一创建）。"""

    topo = await exchange(channel)

    await topo["result_queue"].consume(handle_result)

    logger.info(
        "结果监听器已启动：queue=%s, routing_key=%s",
        settings.task_queue_jg,
        settings.task_queue_jg_key,
    )
