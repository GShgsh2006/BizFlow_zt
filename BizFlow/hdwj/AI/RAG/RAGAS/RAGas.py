#11（源码编译），12 15 14

#bizFlow 智能业务协作平台
#RAGAS 评估指标：faithfulness(忠实度) + answer_relevancy(答案相关性)
import asyncio
import json
import re

from langchain_ollama import ChatOllama
from sqlalchemy.orm import Session

from BizFlow.hdwj.AI.RAG.tool.yyqga import get_embeddings

_judge = ChatOllama(
    model="qwen3:1.7b",
    base_url="http://localhost:11434",
    temperature=0,
    reasoning=False,
    num_predict=256,
)

_VERIFY_BATCH = 4


def _text(msg) -> str:
    """ChatOllama 返回 AIMessage，这里统一取成正文字符串。"""
    content = getattr(msg, "content", msg)
    return content if isinstance(content, str) else str(content)


def _json_array(text: str) -> list[str]:
    """模型有时会包 ```json 或用中文引号，稳健地抠出第一个 JSON 数组。"""
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        return []
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return [str(v) for v in value] if isinstance(value, list) else []


async def decompose(answer: str) -> list[str]:
    """把回答拆成原子声明列表"""
    prompt = f"""将下面的回答拆解为若干条独立的、可验证的原子事实声明。
每条声明只包含一个事实。只输出 JSON 数组，不要输出其他内容。

回答：
{answer}

输出格式：["声明1", "声明2"]
"""
    return _json_array(_text(await _judge.ainvoke(prompt)))


async def verify(statement: str, contexts: list[str]) -> bool:
    """判断一条声明能否从 contexts 推出"""
    prompt = f"""判断下面这条声明能否从给定的上下文中直接推出。
只回答 "yes" 或 "no"，不要解释。

上下文：
{chr(10).join(contexts)}

声明：
{statement}
"""
    return _text(await _judge.ainvoke(prompt)).strip().lower().startswith(("yes", "true", "是", "能", "可以", "正确"))


async def _supported_ratio(text: str, contexts: list[str]) -> float:
    """把 text 拆成原子声明，逐条验证能否被 contexts 支撑，返回占比。"""
    # 封顶 8 条：长回答能拆出几十条声明，逐条问模型会把一次评估拖到分钟级
    statements = (await decompose(text))[:8]
    if not statements:
        return 1.0

    # 每条声明互不依赖，分批并发发出去；串行的话 5 条声明要等 5 次模型
    verdicts: list[bool] = []
    for i in range(0, len(statements), _VERIFY_BATCH):
        verdicts += await asyncio.gather(
            *(verify(s, contexts) for s in statements[i : i + _VERIFY_BATCH])
        )
    return round(sum(verdicts) / len(verdicts), 4)


async def faithfulness(answer: str, contexts: list[str]) -> float:
    """faithfulness = 能被检索片段支撑的声明数 / 总声明数

    1.0 表示回答里每句话都有据可查，0.0 表示整段都在编（幻觉）。
    没有 contexts 就判 0：没给依据，谈不上有据可依。
    """
    if not answer.strip() or not contexts:
        return 0.0
    return await _supported_ratio(answer, contexts)


async def Context_Recall(ground_truth: str, contexts: list[str]) -> float:
    """Context Recall = 标准答案里能被检索片段支撑的声明占比。

    算法与 faithfulness 完全相同，差别只在于输入：
    faithfulness 看「模型的回答」，Context Recall 看「标准答案」。

    没有人工标注的标准答案时，调用方会传回答本身，此时两个分数会非常接近——
    这是指标定义决定的，不是 bug。想让它真正独立，需要一份黄金集。
    """
    if not ground_truth.strip() or not contexts:
        return 0.0
    return await _supported_ratio(ground_truth, contexts)


async def _reverse_questions(answer: str, n: int = 3) -> list[str]:
    """从回答反推它可能在回答什么问题（AnswerRelevancy 的第一步）"""
    prompt = f"""根据下面这段回答，反推出 {n} 个它最可能回答的问题。
只输出 JSON 数组，不要输出其他内容。

回答：
{answer}

输出格式：["问题1", "问题2", "问题3"]
"""
    questions = _json_array(_text(await _judge.ainvoke(prompt)))[:n]
    # 模型不听话时兜底：拿回答自己当"问题"，分数会偏低但不会崩
    return questions or [answer[:80]]


async def answer_relevancy(question: str, answer: str, n: int = 3) -> float:
    """answer_relevancy = 反推问题与原问题的平均余弦相似度

    分数低说明回答跑题，或者答案里塞了大段与问题无关的内容。
    """
    if not question.strip() or not answer.strip():
        return 0.0

    embed = get_embeddings()
    loop = asyncio.get_running_loop()
    # encode 是 CPU 同步计算，丢线程池，别卡住事件循环
    q_vec = await loop.run_in_executor(None, embed.embed_query, question)

    sims = []
    for gq in await _reverse_questions(answer, n):
        g_vec = await loop.run_in_executor(None, embed.embed_query, gq)
        # LocalEmbeddings 用了 normalize_embeddings=True，点积即余弦相似度
        sims.append(sum(x * y for x, y in zip(q_vec, g_vec)))

    return round(sum(sims) / len(sims), 4) if sims else 0.0
async def Context_Precision(
    question: str,
    contexts: list[str]
) -> float:

    prompt = f"""
    你是一个 RAGAS 评估专家。

    请判断下面每个上下文是否与用户问题相关。

    问题：
    {question}

    上下文：
    {contexts}

    按照原本顺序逐条判断：
    相关返回 1，不相关返回 0。

    只返回 JSON 数组，例如：
    [1, 0, 1, 0]
    """

    result = _json_array(
        _text(await _judge.ainvoke(prompt))
    )
    # _json_array 统一返回字符串列表（["1","0",...]），
    # 直接和数字 1 比较永远不相等，必须先转成 int。
    flags: list[int] = []
    for v in result:
        try:
            flags.append(int(float(v)))
        except (TypeError, ValueError):
            flags.append(0)

    relevant_count = 0
    precision_sum = 0.0

    for rank, flag in enumerate(flags, start=1):

        if flag == 1:
            relevant_count += 1


            precision = relevant_count / rank
            precision_sum += precision

    if relevant_count == 0:
        return 0.0

    return precision_sum / relevant_count