#BizFlow 智能业务协作平台
#调用RAG路由文件
import asyncio
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from BizFlow.shujuku.Management import get_db
from BizFlow.hdwj.AI.RAG.model import call_ai, ai_cx
from BizFlow.hdwj.AI.RAG.RAGAS.RAGas import (
    Context_Precision,
    Context_Recall,
    answer_relevancy,
    faithfulness,
)
from BizFlow.hdwj.tool.jx_token import get_current_user
from BizFlow.hdwj.tool.rag import add
from BizFlow.hdwj.AI.RAG.rag import rag_b
from BizFlow.hdwj.AI.RAG.RAGAS.offline_cache.zsd import a
from BizFlow.hdwj.AI.RAG.RAGAS.offline_cache.RAGAS import context
from BizFlow.shujuku.user import RAGAS
from BizFlow.hdwj.tool.RAGAS_mb import Ragas
routerk=APIRouter()

last_request_time = {}

@routerk.post('/ai/{id}')
async def ai(
    request: add,
    id: int,
    db: Session = Depends(get_db)
):
    now = time.time()

    last_time = last_request_time.get(id)

    if last_time is not None:
        if now - last_time < 1:
            raise HTTPException(
                status_code=429,
                detail="请求过于频繁"
            )

    # 记录本次请求时间
    last_request_time[id] = now

    return StreamingResponse(
        call_ai(request.premot, id, db),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"}
    )
#访问ai页面展示ai记录
@routerk.get('/ai_jl/{id}')
def ai_jl_list(
        id:int,db:Session=Depends(get_db)
):
    return [{"HumanMessage":i.HumanMessage,"AIMessage":i.AIMessage} for i in ai_cx(db,id)]

#RAGAS 评估：对一条已生成的回答打分
class RAGAS_body(BaseModel):
    question: str = Field(...)
    answer: str = Field(...)
    contexts: list[str] = Field(default_factory=list)
    # 可选：人工标注的标准答案。不传就把回答本身当参考，
    # 此时 context_recall 会与 faithfulness 完全一致（同算法同输入）。
    ground_truth: str = ""
    # 只算需要的指标：点一个按钮不必把四个都算一遍
    metrics: list[str] = Field(
        default_factory=lambda: ["faithfulness", "answer_relevancy", "context_precision"]
    )


_ALL_METRICS = {"faithfulness", "answer_relevancy", "context_precision", "context_recall"}


@routerk.post('/ragas')
async def ragas(
    body: RAGAS_body,
    token: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按 metrics 指定的指标打分，返回 0~1。

    contexts 由 /ai 的 SSE contexts 事件下发，前端点评估时原样带回。
    互不依赖的指标并发跑，总耗时取最慢的那个。
    """
    want = set(body.metrics) & _ALL_METRICS
    if not want:
        raise HTTPException(status_code=400, detail="metrics 里没有可用的指标")

    # 没给标注答案时，参考文本就是回答本身
    same_reference = not body.ground_truth.strip()
    reference = body.ground_truth.strip() or body.answer

    tasks: dict = {}
    # 参考文本与回答相同时，faithfulness 和 context_recall 是同一次计算，
    # 只跑一遍，context_recall 直接复用（省一轮 9 次模型调用）。
    if "faithfulness" in want or ("context_recall" in want and same_reference):
        tasks["faithfulness"] = faithfulness(body.answer, body.contexts)
    if "answer_relevancy" in want:
        tasks["answer_relevancy"] = answer_relevancy(body.question, body.answer)
    if "context_precision" in want:
        tasks["context_precision"] = Context_Precision(body.question, body.contexts)
    if "context_recall" in want and not same_reference:
        tasks["context_recall"] = Context_Recall(reference, body.contexts)

    values = await asyncio.gather(*tasks.values())
    scores = dict(zip(tasks.keys(), values))

    if "context_recall" in want and same_reference:
        scores["context_recall"] = scores["faithfulness"]

    result = {k: round(scores[k], 4) for k in want if k in scores}

    # 入库：四个指标都算出来了才存，缺项的行横向对比没意义
    if _ALL_METRICS <= set(result):
        # 这几列是 Integer，存 0~100 整数（存 0.85 会被 MySQL 四舍五入成 1）
        db.add(RAGAS(
            name=body.question[:500],
            faithfulness=round(result["faithfulness"] * 100),
            answer_relevancy=round(result["answer_relevancy"] * 100),
            Context_Precision=round(result["context_precision"] * 100),
            context_recall=round(result["context_recall"] * 100),
        ))
        try:
            db.commit()
        except Exception:
            db.rollback()
            logging.exception("RAGAS 结果落库失败")

    return result


@routerk.get("/ragas", response_model=list[Ragas])
async def get_ragas(limit: int = 20, db: Session = Depends(get_db)):
    """读库里已存下的评估记录，最新的在前。只读，不重新打分。"""
    rows = (
        db.query(RAGAS)
        .order_by(RAGAS.id.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    # 库里是 0~100 整数，对外统一成 0~1
    return [
        Ragas(
            id=r.id,
            name=r.name,
            faithfulness=r.faithfulness / 100,
            answer_relevancy=r.answer_relevancy / 100,
            Context_Precision=r.Context_Precision / 100,
            context_recall=r.context_recall / 100,
        )
        for r in rows
    ]


@routerk.get('/lxhc')
async def lxhc():
    wt = a.Question
    bzda = a.Reference

    sxw = await rag_b(wt)
    fs = await context(sxw, bzda)
    return {"Offline_detection": fs}

