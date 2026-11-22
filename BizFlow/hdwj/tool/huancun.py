#缓存文件
import json
import time
from typing import Any, Optional

import redis.asyncio as redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

# ---------- Redis 连接 ----------
# 关键：必须显式设短超时 + 关掉重试。
# 不设的话 Redis 没启动时，redis-py 默认 socket_connect_timeout=5，
# 再叠加重试和 localhost 双栈解析，单次 get 就要白等 4 秒以上
# （读缓存 + 写缓存 = 8 秒，Excel 导出慢的根因就在这里）。
redis_client = redis.from_url(
    "redis://localhost:6379/0",
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=0.5,
    retry=Retry(NoBackoff(), 0),
    retry_on_timeout=False,
    health_check_interval=0,
)

# ---------- Redis 熔断 ----------
# 冷却期内直接当作未命中，连尝试都不尝试。
# 这样 Redis 压根没装的时候，导出接口不会每个请求都白等 0.5 秒。
_REDIS_DOWN_COOLDOWN = 15.0
_redis_down_until = 0.0


def _redis_available() -> bool:
    return time.monotonic() >= _redis_down_until


def _mark_redis_down(reason) -> None:
    global _redis_down_until
    if _redis_available():
        _redis_down_until = time.monotonic() + _REDIS_DOWN_COOLDOWN
        print(f"[缓存] Redis 不可用，{_REDIS_DOWN_COOLDOWN:.0f} 秒内跳过缓存：{reason}")


class Huancun:
    def __init__(self, redis_client) -> None:
        self.redis_client = redis_client

    #缓存查询函数
    async def huancun_dq(self,key:str):
       if not _redis_available():
           return None                      # 熔断中：直接当未命中
       try:
           a=await self.redis_client.get(key)
       except RedisError as e:
           _mark_redis_down(e)
           raise
       if a is None:
           return None
       try:
           return json.loads(a)
       except json.JSONDecodeError:
           await self.redis_client.delete(key)
           return None
    #缓存写入函数
    async def huancun_xr(self,key:str,value,time:int=1000):
        # redis-asyncio 的签名是 set(name, value, ex=秒)；
        # value 必须是 str/bytes，list/dict 要先 json.dumps
        if not _redis_available():
            return                           # 熔断中：不写缓存
        if not isinstance(value, (str, bytes)):
            value = json.dumps(value, ensure_ascii=False, default=str)
        try:
            await self.redis_client.set(key, value, ex=time)
        except RedisError as e:
            _mark_redis_down(e)
            raise

    #删除缓存
    async def huancun_sc(self,*key:str):
        if not key:
            return
        # 删除不做熔断短路：宁可慢一点，也不能让脏缓存留在 Redis 里
        try:
            await self.redis_client.delete(*key)
        except RedisError as e:
            _mark_redis_down(e)
            raise


