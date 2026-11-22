#异常处理器
from starlette.responses import JSONResponse
from fastapi import Request
from BizFlow.hdwj.Exception.exceptions import hdwjException
def exception_handler(
        request: Request, exception:hdwjException
):
    return JSONResponse(
        status_code=exception.code,
        content={
            "code": exception.code,
            "message": exception.message,
            "detail": exception.message,
        },
    )