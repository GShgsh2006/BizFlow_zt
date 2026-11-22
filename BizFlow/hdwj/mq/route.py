# mq/route.py
# MQ 运行状态接口：前端用来展示「MQ 是否连接 / 后台任务执行到哪一步」

from fastapi import APIRouter

from BizFlow.hdwj.mq.bootstrap import is_ready
from BizFlow.hdwj.mq.config import settings
from BizFlow.hdwj.mq.worker import STATS, TASK_HANDLERS

router_mq = APIRouter()


@router_mq.get("/mq/status")
async def mq_status():
    return {
        "connected": is_ready(),
        "queue": settings.MQ_TASK_QUEUE,
        "memory_queue": settings.MQ_MEMORY_QUEUE,
        "handlers": sorted(TASK_HANDLERS),
        "stats": dict(STATS),
    }
