# BizFlow/hdwj/mq/connextion.py
# RabbitMQ 连接管理（文件名保留历史拼写，避免改动大量 import）

import asyncio
from urllib.parse import urlparse

import aio_pika

from aio_pika.abc import (
    AbstractRobustConnection,
    AbstractRobustChannel,
)

from BizFlow.hdwj.mq.config import settings
from BizFlow.hdwj.Exception.exceptions import hdwjException


def _broker_addr() -> tuple[str, int]:
    """从 RABBITMQ_URL 解析出主机和端口。"""
    parsed = urlparse(settings.RABBITMQ_URL)
    return parsed.hostname or "localhost", parsed.port or 5672


async def _broker_reachable(timeout: float | None = None) -> bool:
    """先探测端口。

    connect_robust 在首次连不上时抛异常但后台仍会无限重连刷日志，
    而且后连上了也不会重新注册消费者，容易造成“日志显示连上了但功能没用”。
    这里先探测，连不上就不建连接。
    """
    if timeout is None:
        timeout = settings.MQ_PROBE_TIMEOUT
    host, port = _broker_addr()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


class RabbitMQManager:
    def __init__(self):
        self.connection: AbstractRobustConnection | None = None
        self.channel: AbstractRobustChannel | None = None

    async def connect(self):
        # 连接已经建立且仍然可用，就不重复创建
        if self.connection is not None and not self.connection.is_closed:
            return self.channel

        if not await _broker_reachable():
            host, port = _broker_addr()
            raise ConnectionError(
                f"RabbitMQ 暂不可用（{host}:{port} 没有响应）；"
                "Excel 导出会自动降级为本地直算，MQ 起来后下一次请求会自动切回"
            )

        # 建立 RabbitMQ 连接
        self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

        # 创建 Channel
        self.channel = await self.connection.channel()

        # 记录全局唯一实例，供 message / worker / 路由使用
        global _manager
        _manager = self

        return self.channel

    async def close(self):
        # 关闭 RabbitMQ 连接
        if self.connection is not None and not self.connection.is_closed:
            await self.connection.close()

        self.connection = None
        self.channel = None


# 全局管理器：应用启动时由 lifespan 调用 connect() 写入
_manager: RabbitMQManager | None = None


def get_manager() -> RabbitMQManager | None:
    return _manager


# 并发请求可能同时触发惰性连接，用一把锁串行化
_connect_lock: asyncio.Lock | None = None


def _lock() -> asyncio.Lock:
    global _connect_lock
    if _connect_lock is None:
        _connect_lock = asyncio.Lock()
    return _connect_lock


async def ensure_channel() -> AbstractRobustChannel:
    """确保存在可用 channel；没连接过或已断开就当场连。

    这样 RabbitMQ 比后端晚启动也不需要重启后端。
    """
    global _manager

    async with _lock():
        if _manager is None:
            _manager = RabbitMQManager()

        if _manager.channel is None or _manager.channel.is_closed:
            await _manager.connect()

        return _manager.channel


async def get_channel() -> AbstractRobustChannel:
    """取当前可用的 channel；连不上时抛业务异常。"""
    try:
        return await ensure_channel()
    except Exception as e:
        raise hdwjException(503, f"RabbitMQ 未连接：{e}")
