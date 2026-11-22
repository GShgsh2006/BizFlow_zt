#验证token检查是否登入
import os

from dotenv import load_dotenv
from fastapi import  Request
from fastapi.responses import JSONResponse
from jose import jwt
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

PUBLIC_PATHS = {
    "/sign_in",
    "/sign_up",
    "/sign_up_yz",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
}

async def auth_middleware(request: Request, call_next):
    # 预检请求
    if request.method == "OPTIONS":
        return await call_next(request)

    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    auth = request.headers.get("Authorization")
    token = auth.split(" ")[1] if auth and auth.startswith("Bearer ") else None

    if not token:
        return JSONResponse(status_code=401, content={"detail": "未登录，请先登录"})

    # 真正校验签名与过期：之前只判断 token 存不存在，
    # 随便一个 "Bearer x" 都能过。密钥与签发端同源，验签才有效。
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "登录已失效，请重新登录"})

    return await call_next(request)