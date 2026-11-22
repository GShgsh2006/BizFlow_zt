##BizFlow 智能业务协作平台
#短期记忆落库：直接用 LangGraph 官方 SQLite Checkpointer
#
# 不再自己实现 BaseCheckpointSaver。
#   checkpoint（每轮对话的完整状态快照）由官方 AsyncSqliteSaver 写进本地
#   checkpoints.sqlite，编译图时注入即可 —— config 里带 thread_id，
#   LangGraph 就按线程自动恢复历史消息，这就是多轮记忆。
#
# 为什么是 AsyncSqliteSaver：
#   graph.astream() 是异步的，同步 SqliteSaver 会阻塞事件循环。
#
# 生命周期：
#   get_checkpointer()    import / 编译图时调，只创建对象，不连库
#   init_checkpointer()   FastAPI 启动时 await 一次：真正连库 + 建表
#   close_checkpointer()  关闭服务时释放连接
#
# 注意：这里的表是 LangGraph 自己的 schema，不参与 shujuku 的 MySQL 迁移。

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

logger = logging.getLogger(__name__)

# 数据库文件跟代码放一起，随项目走
DB_PATH = Path(__file__).resolve().parent / "checkpoints.sqlite"

_checkpointer: AsyncSqliteSaver | None = None
_conn: aiosqlite.Connection | None = None


def get_checkpointer() -> AsyncSqliteSaver:
    """全局单例；编译图时注入用。

    aiosqlite 的连接是惰性的：这里只创建对象，真正连库在 init_checkpointer()。
    """
    global _checkpointer, _conn
    if _checkpointer is None:
        _conn = aiosqlite.connect(str(DB_PATH))
        _checkpointer = AsyncSqliteSaver(_conn)
    return _checkpointer


async def init_checkpointer() -> None:
    """启动时调用：建立连接并建表（幂等）。"""
    saver = get_checkpointer()
    conn = _conn
    if conn is not None:
        await conn  # aiosqlite 的 __await__ 会启动后台线程并连接
    await saver.setup()
    logger.info("短期记忆 Checkpointer 就绪：%s", DB_PATH)


async def close_checkpointer() -> None:
    """服务关闭时调用。"""
    global _checkpointer, _conn
    if _conn is not None:
        try:
            await _conn.close()
        except Exception as e:
            logger.warning("关闭 Checkpointer 失败: %s", e)
    _conn = None
    _checkpointer = None
