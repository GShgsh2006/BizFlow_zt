#excal表下载和浏览器展示
#两个导出接口逻辑一致，只有响应头 inline / attachment 不同，抽成一个内部函数复用。
import asyncio
import logging
import uuid
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from BizFlow.hdwj.Exception.exceptions import hdwjException
from BizFlow.hdwj.function.excal import build_excel
from BizFlow.hdwj.function.query import query_dsz
from BizFlow.hdwj.mq.bootstrap import ensure_started
from BizFlow.hdwj.mq.config import settings
from BizFlow.hdwj.mq.message import message
from BizFlow.hdwj.mq.ggwj.jgdl import create_future, futures
from BizFlow.hdwj.tool.jx_token import get_current_user

logger = logging.getLogger(__name__)

router_excal = APIRouter()

# 任务队列 / 业务函数 / 结果路由键
KEY_DL = settings.MQ_TASK_ROUTING_KEY
TASK_NAME = "query_dsz"
KEY_JS = settings.task_queue_jg_key

EXCEL_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _raise_biz(e: hdwjException):
    """把业务异常翻译成合适的 HTTP 状态码（权限类统一成 403）。"""
    status = 403 if e.code >= 500 else e.code
    raise HTTPException(status_code=status, detail=e.message)


async def _query_local(token: dict) -> list:
    """不走 MQ，直接在进程内查库（MQ 不可用时的兜底）。"""
    try:
        return await query_dsz({"task_id": f"local-{uuid.uuid4()}", "token": token})
    except hdwjException as e:
        _raise_biz(e)


async def _query_via_mq(token: dict) -> list:
    """投递任务到 RabbitMQ，等 worker 回传结果。"""

    channel = await ensure_started()

    task_id = str(uuid.uuid4())
    future = create_future(task_id)

    try:
        await message({"task_id": task_id, "token": token}, KEY_DL, TASK_NAME, KEY_JS, channel)
        return await asyncio.wait_for(future, timeout=60)

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="员工数据查询超时")
    except RuntimeError as e:
        # worker 处理失败时通过 Future 抛回来
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if futures.get(task_id) is future:
            futures.pop(task_id, None)


async def _fetch_dsz_rows(token: dict) -> tuple[list, str]:
    """优先走 MQ；MQ 不可用时按配置降级为本地直算。

    返回 (rows, 数据来源) —— 来源会写进 X-Data-Source 响应头，方便确认走的是哪条路。
    """

    try:
        rows = await _query_via_mq(token)
        logger.info("员工档案数据来源：mq")
        return rows, "mq"

    except HTTPException:
        # MQ 链路内部明确失败（超时 / worker 报错）直接抛，不掩盖
        raise

    except Exception as e:
        if not settings.MQ_FALLBACK_LOCAL:
            raise HTTPException(
                status_code=503,
                detail=f"RabbitMQ 不可用：{e}",
            )

        logger.warning("MQ 不可用，本次改为本地直算：%s", e)
        rows = await _query_local(token)
        logger.info("员工档案数据来源：local")
        return rows, "local"


async def _build_dsz_response(token: dict, disposition: str) -> StreamingResponse:
    """取数据 -> 生成 xlsx -> 按指定方式返回。"""

    rows, source = await _fetch_dsz_rows(token)

    excel_bytes = build_excel(rows)
    filename = quote("员工信息.xlsx")

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type=EXCEL_MEDIA_TYPE,
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{filename}",
            "X-Data-Source": source,
        },
    )


@router_excal.get("/dsz/employees/preview")
async def preview_dsz(token: dict = Depends(get_current_user)):
    """返回 JSON 列表，供前端表格预览（[{"name","tasks","salary"}]）"""
    rows, source = await _fetch_dsz_rows(token)
    return JSONResponse(content=rows, headers={"X-Data-Source": source})


@router_excal.get("/dsz/employees/view")
async def view_dsz_excel(
    token: dict = Depends(get_current_user),
):
    """浏览器内预览员工信息表"""
    return await _build_dsz_response(token, "inline")


@router_excal.get("/dsz/employees/download")
async def download_dsz_excel(
    token: dict = Depends(get_current_user),
):
    """下载员工信息表"""
    return await _build_dsz_response(token, "attachment")
