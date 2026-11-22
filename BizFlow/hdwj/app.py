#BizFlow 智能业务协作平台
import os
def _normalize_no_proxy() -> None:
    for key in ("NO_PROXY", "no_proxy"):
        raw = os.environ.get(key)
        if not raw:
            continue
        hosts = []
        for host in raw.split(","):
            host = host.strip()
            if host.startswith("[") and host.endswith("]"):
                host = host[1:-1]
            if host:
                hosts.append(host)
        os.environ[key] = ",".join(hosts)


_normalize_no_proxy()

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import threading
logging.basicConfig(level=logging.INFO)
from BizFlow.hdwj.tool.token_yz import auth_middleware
from BizFlow.hdwj.Route.crud_Route import router
from BizFlow.hdwj.Route.sign_in_up import routers
from BizFlow.hdwj.Route.notice_ly import router_notice
from BizFlow.hdwj.Route.Salary_ly import router_gz
from BizFlow.hdwj.Route.excal import router_excal
from BizFlow.hdwj.tool.zjj import LoggingMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from BizFlow.hdwj.Exception.exception_handlers import exception_handler
from BizFlow.hdwj.Exception.exceptions import hdwjException
from BizFlow.hdwj.mq.bootstrap import start_supervisor, start_with_retry, stop_supervisor
from BizFlow.hdwj.mq.connextion import get_manager
from BizFlow.hdwj.mq.route import router_mq
# AI/RAG/LangGraph 依赖较重(需要下载模型 / 连 Ollama / Milvus 等)。
# 这里容错导入:装好且可用才挂载，失败只跳过，不影响核心业务启动。
routerk = None
routeragent = None
file = None

try:
    from BizFlow.hdwj.AI.RAG.route.ai_ly import routerk
except Exception:
    logging.exception("AI(RAG) 路由导入失败，已跳过")

try:
    from BizFlow.hdwj.LangGraph_ly.app import routeragent
except Exception:
    logging.exception("LangGraph Agent 路由导入失败，已跳过")

try:
    from BizFlow.hdwj.AI.RAG.file_interoperability import file
except Exception:
    logging.exception("RAG 知识库链路导入失败，已跳过")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from BizFlow.shujuku.migrate import migrate

        created, added, manual = migrate()
        if created or added:
            logging.info("数据库结构已自动补齐 | 新建表=%s | 新增列=%s", created, added)
        else:
            logging.info("数据库结构已是最新，无需迁移")
        if manual:
            logging.warning("以下列需人工处理(NOT NULL 且无默认值): %s", manual)
    except Exception as e:
        # 迁移失败不让服务起不来，只是接口该报错还是会报错，日志里能看到原因
        logging.error("数据库自动迁移失败(不影响启动): %s", e)

    # ---------- 2. RAG 初始化（后台线程，避免卡住启动） ----------
    if file is not None:
        def _init_rag():
            try:
                from BizFlow.hdwj.AI.RAG.tool.yyqga import load_embedding_model
                load_embedding_model()
                logging.info("Embedding 模型加载完成")
            except Exception as e:
                logging.error("Embedding 模型加载失败: %s", str(e))
            try:
                import asyncio as _asyncio
                _asyncio.run(file())
            except Exception as e:
                logging.error("RAG 知识库初始化失败: %s", str(e))

        threading.Thread(target=_init_rag, daemon=True).start()

    # ---------- 3. 短期记忆 Checkpointer（官方 SQLite，Agent 多轮记忆） ----------
    if routeragent is not None:
        try:
            from BizFlow.hdwj.LangGarph.ai_Memory.checkpointer import (
                init_checkpointer,
            )

            await init_checkpointer()
        except Exception as e:
            logging.error("短期记忆 Checkpointer 初始化失败(Agent 记忆不可用): %s", e)

    # ---------- 4. RabbitMQ ----------
    # 启动阶段直接连，失败按配置重试；仍失败也不阻塞启动，后台巡检继续重试
    connected = await start_with_retry()
    app.state.mq_manager = get_manager() if connected else None
    if not connected:
        logging.warning(
            "RabbitMQ 暂未就绪，Excel 导出先走本地直算；"
            "后台巡检会自动重试，连上后任务消费(含长期记忆)自动上线"
        )
    # 巡检器必须无条件启动：MQ 晚启动 / 重启后，消费者自动重新挂回去
    start_supervisor()

    yield

    # ---------- 5. 关闭资源 ----------
    await stop_supervisor()

    if routeragent is not None:
        try:
            from BizFlow.hdwj.LangGarph.ai_Memory.checkpointer import (
                close_checkpointer,
            )

            await close_checkpointer()
        except Exception as e:
            logging.warning("关闭 Checkpointer 失败: %s", e)

    mq_manager = getattr(app.state, "mq_manager", None) or get_manager()
    if mq_manager is not None:
        try:
            await mq_manager.close()
        except Exception as e:
            logging.warning("关闭 RabbitMQ 连接失败: %s", e)

    print("项目关闭")


app = FastAPI(lifespan=lifespan)

app.include_router(router)
app.include_router(routers)
if routerk is not None:
    app.include_router(routerk)
if routeragent is not None:
    app.include_router(routeragent)
app.include_router(router_notice)
app.include_router(router_gz)
app.include_router(router_excal)
app.include_router(router_mq)

app.add_middleware(LoggingMiddleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)
app.add_exception_handler(
    hdwjException,
    exception_handler  # type: ignore
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:2020"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
