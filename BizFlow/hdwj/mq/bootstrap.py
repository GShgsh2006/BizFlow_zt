# mq/bootstrap.py
# 保证「连接 + 消费者」都就绪，可反复调用（惰性初始化）
#
# 场景：后端启动时 RabbitMQ 还没起来（或根本没装）。
# 以前只在 lifespan 里连一次，之后永远 503；现在：
#   - 每个请求前调 ensure_started()：已就绪直接返回 channel，没就绪就现连
#   - lifespan 启动 start_supervisor()：后台定时巡检，MQ 晚启动 / 重启后
#     会自动重新连上并把消费者挂回去，不需要重启后端

import asyncio
import logging
import time

from BizFlow.hdwj.Exception.exceptions import hdwjException
from BizFlow.hdwj.mq.config import settings
from BizFlow.hdwj.mq.connextion import ensure_channel
from BizFlow.hdwj.mq.ggwj.jgdl import start_result_listener
from BizFlow.hdwj.mq.worker import start_worker
from BizFlow.hdwj.LangGarph.ai_Memory.mq_consumer import start_memory_consumer

logger = logging.getLogger(__name__)

# 失败后的冷却时间（秒）：避免每个请求都去白等一次 TCP 探测
RETRY_COOLDOWN = 10.0

# 后台巡检参数
RETRY_INTERVAL = 5.0        # MQ 没起来时的首次重试间隔
MAX_RETRY_INTERVAL = 30.0   # 重试间隔上限
CHECK_INTERVAL = 30.0       # 已就绪时的巡检间隔（确认连接还在）

_ready = False
_last_fail = 0.0
_init_lock: asyncio.Lock | None = None

# 消费者挂在哪个 channel 上。channel 被重建（断线重连换了对象）时，
# 说明新 channel 上还没有消费者，需要重新注册。
_listener_channel = None
_worker_channel = None
_memory_channel = None

_supervisor: asyncio.Task | None = None


def _lock() -> asyncio.Lock:
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


def is_ready() -> bool:
    return _ready


async def _ensure_consumers(channel) -> None:
    """把结果监听 + 任务消费挂到 channel 上；同一个 channel 只挂一次。"""
    global _listener_channel, _worker_channel, _memory_channel, _ready

    if _listener_channel is not channel:
        await start_result_listener(channel)
        _listener_channel = channel

    if _worker_channel is not channel:
        await start_worker(channel)
        _worker_channel = channel

    if _memory_channel is not channel:
        await start_memory_consumer(channel)
        _memory_channel = channel

    if not _ready:
        logger.info("RabbitMQ 就绪：结果监听 + 任务消费 + 长期记忆消费已启动")
    _ready = True


async def ensure_started(force: bool = False):
    """返回可用的 channel；连不上则抛 hdwjException(503)。

    force=True 时跳过失败冷却，用于启动阶段 / 后台巡检的主动重试。
    """

    global _ready, _last_fail

    if _ready:
        try:
            return await ensure_channel()
        except Exception as e:
            # 之前连上过、现在断了：标记为未就绪，交给后台巡检重连并重新挂消费者
            _ready = False
            _last_fail = time.monotonic()
            logger.warning("RabbitMQ 连接已断开：%s", e)

    if not force and time.monotonic() - _last_fail < RETRY_COOLDOWN:
        raise hdwjException(503, "RabbitMQ 暂不可用（稍后会自动重试）")

    async with _lock():
        # 双重检查：等锁期间可能已经有人初始化好了
        if _ready:
            return await ensure_channel()

        try:
            channel = await ensure_channel()
            await _ensure_consumers(channel)
            return channel

        except Exception as e:
            _last_fail = time.monotonic()
            logger.warning("RabbitMQ 初始化失败：%s", e)
            raise hdwjException(503, f"RabbitMQ 未连接：{e}")


async def start_with_retry() -> bool:
    """启动阶段用：连不上就按配置重试几次。

    全部失败返回 False（不抛异常）——后端照常启动，交给后台巡检继续重试。
    """
    for attempt in range(1, settings.MQ_STARTUP_RETRIES + 1):
        try:
            await ensure_started(force=attempt > 1)
            return True
        except Exception as e:
            if attempt >= settings.MQ_STARTUP_RETRIES:
                logger.warning(
                    "RabbitMQ 启动连接失败（已试 %s 次），交给后台巡检继续重试：%s",
                    attempt,
                    e,
                )
                return False
            logger.warning(
                "RabbitMQ 第 %s/%s 次连接失败，%.1f 秒后重试：%s",
                attempt,
                settings.MQ_STARTUP_RETRIES,
                settings.MQ_STARTUP_RETRY_DELAY,
                e,
            )
            await asyncio.sleep(settings.MQ_STARTUP_RETRY_DELAY)
    return False


async def _supervise() -> None:
    """后台巡检：连不上就退避重试，连上了定期确认 channel 仍可用。"""
    delay = RETRY_INTERVAL
    while True:
        try:
            channel = await ensure_channel()
            await _ensure_consumers(channel)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("RabbitMQ 未就绪，%.0f 秒后自动重试：%s", delay, e)
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_RETRY_INTERVAL)
        else:
            delay = RETRY_INTERVAL
            await asyncio.sleep(CHECK_INTERVAL)


def start_supervisor() -> None:
    """在 lifespan 里调用一次：启动后台巡检任务。"""
    global _supervisor
    if _supervisor is None or _supervisor.done():
        _supervisor = asyncio.create_task(_supervise(), name="mq-supervisor")


async def stop_supervisor() -> None:
    """关闭服务时调用。"""
    global _supervisor
    task, _supervisor = _supervisor, None
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
