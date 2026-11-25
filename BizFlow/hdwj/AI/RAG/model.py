#BizFlow 智能业务协作平台
#调用ai模型实现RAG检索
from langchain_ollama import ChatOllama
from sqlalchemy.orm import Session
from BizFlow.hdwj.AI.RAG.rag import rag_b
from BizFlow.hdwj.AI.RAG.pormpt.prompt_RAG_ai import Prompts
import json
import logging
import uuid
from BizFlow.shujuku.user import ai_jl

# 模型名不能带空格，否则 Ollama 找不到模型
MODEL_NAME = "qwen3.5:9b-q4_K_M"

# 全局单例：在 app.py 的 lifespan 里初始化，其它文件通过 get_llm() 拿。
# 不要在模块导入时创建，避免导入即连 Ollama、启动顺序不可控。
llm = None


def init_llm():
    """创建模型客户端并预热（供 lifespan 调用）。重复调用返回同一个实例。"""
    global llm
    if llm is None:
        llm = ChatOllama(
            model=MODEL_NAME,
            base_url="http://localhost:11434",
            temperature=0.7,
            reasoning=True,
            keep_alive="30m",  # 30 分钟内不卸载，避免反复冷加载
        )
    # 只生成 1 个 token，目的把模型加载进显存，不在启动时真的长篇输出。
    # num_predict 属于 Ollama 的 options，必须放在 options 里传
    try:
        llm.bind(options={"num_predict": 1}).invoke("你好")
        logging.info("AI 模型预热完成: %s", MODEL_NAME)
    except Exception as e:
        logging.warning("AI 模型预热失败(不影响使用，首次请求会再加载): %s", e)
    return llm


def get_llm():
    """其它文件统一从这里取模型。"""
    return llm or init_llm()


class LLMServiceError(Exception):
    """业务层主动抛出的异常，带错误码和给用户看的文案。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _friendly_error(e: Exception) -> tuple[str, str]:
    """把底层异常翻译成(错误码, 用户能看懂的提示)。

    原始异常(含堆栈)只写服务端日志，不下发给前端，避免泄露内部细节。
    """
    if isinstance(e, LLMServiceError):
        return e.code, e.message
    raw = str(e).lower()
    if "timeout" in raw or "timed out" in raw:
        return "LLM_TIMEOUT", "AI 响应超时，请重试"
    if "out of memory" in raw or "cuda" in raw or "oom" in raw:
        return "LLM_OOM", "AI 资源不足，请稍后重试"
    if "not found" in raw and "model" in raw:
        return "MODEL_NOT_FOUND", "AI 模型未就绪，请联系管理员"
    if "connection" in raw or "refused" in raw:
        return "LLM_UNAVAILABLE", "AI 服务暂时不可用，请稍后重试"
    return "LLM_ERROR", "AI 生成失败，请重试"

async def call_ai(
        user_question: str,rw_id:int,db:Session
):
    """
    system_role:
        AI角色设定

    user_question:
        用户输入的问题
    """
    answer_parts = []
    try:
        rag=await rag_b(user_question)

        # 先把这一轮检索到的片段发给前端。RAGAS 的 faithfulness 必须拿它当依据，
        # 前端点"评估"时原样回传，不再走模块级全局变量（多人并发会串号）。
        yield f"data: {json.dumps({'type': 'contexts', 'content': rag}, ensure_ascii=False)}\n\n"
        # 记忆直接从库里按登录人 id 取（最近 10 条），不再依赖 ai_ly 的模块级全局 a：
        # 全局是所有请求共享的，多个人同时用会互相串号
        aijiyi= [
            {"HumanMessage":i.HumanMessage,"AIMessage":i.AIMessage}
            for i in ai_cx(db,rw_id)
        ]

        # 创建调用链
        chain = Prompts|get_llm()

        # 调用模型
        async for chunk in chain.astream({
            "jiyi":aijiyi,
            "zsd": rag,
            "request_ku": user_question
        }):
            # 1. 思考过程
            reasoning = chunk.additional_kwargs.get("reasoning_content", "")
            if reasoning:
                yield f"data: {json.dumps({'type': 'thinking', 'content': reasoning}, ensure_ascii=False)}\n\n"

            # ChatOllama 的 content 是 str；判一下类型，
            # 避免多模态返回 list 时把它当字符串拼
            if isinstance(chunk.content, str) and chunk.content:
                answer_parts.append(chunk.content)
                yield f"data: {json.dumps({'type': 'answer', 'content': chunk.content}, ensure_ascii=False)}\n\n"

        # 一次问答只落一行。原来把 db.add/commit 写在循环里，
        # 每吐一个 token 就插一行，ai_jl 历史会被切成一堆碎片。
        db.add(ai_jl(name_id=rw_id, HumanMessage=user_question, AIMessage="".join(answer_parts)))
        db.commit()

    except Exception as e:
        code, msg = _friendly_error(e)
        trace_id = uuid.uuid4().hex[:8]
        logging.exception("call_ai 流式生成失败 code=%s trace_id=%s", code, trace_id)
        try:
            db.rollback()  # 失败时不要留下半截事务
        except Exception:
            pass
        yield f"data: {json.dumps({'type': 'error', 'code': code, 'message': msg, 'trace_id': trace_id}, ensure_ascii=False)}\n\n"

    yield "data: [DONE]\n\n"

#查询ai记录函数
def ai_cx(db:Session,name_id:int):
    # 取最近 10 条，再翻成时间正序，直接当对话上下文用
    rows = (
        db.query(ai_jl)
        .filter(ai_jl.name_id == name_id)
        .order_by(ai_jl.id.desc())
        .limit(10)
        .all()
    )
    rows.reverse()
    return rows


