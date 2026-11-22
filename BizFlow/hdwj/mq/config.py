#mq配置文件

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # RabbitMQ 连接地址
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 业务交换机
    MQ_EXCHANGE_NAME: str = "app.exchange"

    # 死信交换机
    MQ_DLX_NAME: str = "app.dlx"

    # 业务队列
    MQ_TASK_QUEUE: str = "app.task.queue"

    # 死信队列
    MQ_DEAD_QUEUE: str = "app.dead.queue"

    # 业务路由键
    MQ_TASK_ROUTING_KEY: str = "task.excel"

    # 死信路由键
    MQ_DEAD_ROUTING_KEY: str = "task.dead"

    # 结果队列路由键
    task_queue_jg_key: str = "task.excel_jg"

    # 结果队列名称
    task_queue_jg: str = "task.excel_jgs"

    # 长期记忆专用队列与路由键（不占用业务任务队列 app.task.queue）
    MQ_MEMORY_QUEUE: str = "app.memory.queue"
    MQ_MEMORY_ROUTING_KEY: str = "task.memory"

    # MQ 不可用时是否降级为本地直算：
    # True  = 接口照常可用（推荐，开发环境友好）
    # False = 直接报 503，强制只走 MQ（用来证明 MQ 真的在跑）
    MQ_FALLBACK_LOCAL: bool = False

    # 连接前的 TCP 探测超时（秒）。
    # RabbitMQ 冷启动（Erlang VM + 应用加载）通常要几秒，
    # 0.6s 会把「还在启动」误判成「没装 MQ」；3s 是能容忍冷启动的正常值。
    # 探测只用于快速失败：端口不通时最多等这么久，不会无限挂住。
    MQ_PROBE_TIMEOUT: float = 3.0

    # 启动阶段（lifespan）连接重试：最多试几次、每次间隔多久。
    # 三次都失败后交给后台巡检继续重试，后端照常启动。
    MQ_STARTUP_RETRIES: int = 3
    MQ_STARTUP_RETRY_DELAY: float = 1.0


# 全局唯一配置实例；其它模块统一 from ...config import settings 使用
settings = Settings()
