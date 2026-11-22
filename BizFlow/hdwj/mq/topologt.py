# mq/topologt.py
# 拓扑声明（文件名保留历史拼写 topologt，避免改动 import）

import aio_pika

from BizFlow.hdwj.mq.config import settings


async def exchange(channel) -> dict:

    if channel is None:
        raise ValueError("exchange() 需要传入已连接的 channel")

    # 1. 普通（业务）交换机
    normal_exchange = await channel.declare_exchange(
        name=settings.MQ_EXCHANGE_NAME,
        type=aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    # 2. 死信交换机
    dead_exchange = await channel.declare_exchange(
        name=settings.MQ_DLX_NAME,
        type=aio_pika.ExchangeType.DIRECT,
        durable=True,
    )

    # 3. 死信队列
    dead_queue = await channel.declare_queue(
        name=settings.MQ_DEAD_QUEUE,
        durable=True,
    )

    # 注意：绑定的是队列，不是交换机
    await dead_queue.bind(
        exchange=dead_exchange,
        routing_key=settings.MQ_DEAD_ROUTING_KEY,
    )

    # 4. 任务队列（消费失败进死信）
    task_queue = await channel.declare_queue(
        name=settings.MQ_TASK_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": settings.MQ_DLX_NAME,
            "x-dead-letter-routing-key": settings.MQ_DEAD_ROUTING_KEY,
        },
    )

    # 5. 结果队列
    result_queue = await channel.declare_queue(
        name=settings.task_queue_jg,
        durable=True,
        arguments={
            "x-dead-letter-exchange": settings.MQ_DLX_NAME,
            "x-dead-letter-routing-key": settings.MQ_DEAD_ROUTING_KEY,
        },
    )

    # 5.1 长期记忆专用队列（独立消费者，不经过业务任务队列）
    memory_queue = await channel.declare_queue(
        name=settings.MQ_MEMORY_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": settings.MQ_DLX_NAME,
            "x-dead-letter-routing-key": settings.MQ_DEAD_ROUTING_KEY,
        },
    )

    # 6. 绑定：任务键 -> 任务队列
    await task_queue.bind(
        exchange=normal_exchange,
        routing_key=settings.MQ_TASK_ROUTING_KEY,
    )

    # 7. 绑定：结果键 -> 结果队列（原来错绑到了 task_queue 上）
    await result_queue.bind(
        exchange=normal_exchange,
        routing_key=settings.task_queue_jg_key,
    )

    # 8. 绑定：长期记忆路由键 -> 长期记忆队列
    await memory_queue.bind(
        exchange=normal_exchange,
        routing_key=settings.MQ_MEMORY_ROUTING_KEY,
    )

    return {
        "exchange": normal_exchange,
        "dead_exchange": dead_exchange,
        "dead_queue": dead_queue,
        "task_queue": task_queue,
        "result_queue": result_queue,
        "memory_queue": memory_queue,
    }
