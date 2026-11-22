# mq/message.py
# 投递任务消息

import json

import aio_pika

from BizFlow.hdwj.mq.topologt import exchange


async def message(zd: dict, key_dl: str, key: str, key_js: str, channel):

    topo = await exchange(channel)

    # aio_pika 的 publish 只认 message / routing_key 这些参数，
    # 业务标识必须塞进消息体，worker 才能读到。
    body_data = dict(zd)
    body_data["hanshu_name"] = key
    body_data["result_key"] = key_js

    body = json.dumps(body_data, ensure_ascii=False).encode("utf-8")

    await topo["exchange"].publish(
        message=aio_pika.Message(
            body=body,
            content_type="application/json",
            content_encoding="utf-8",
        ),
        routing_key=key_dl,
    )
