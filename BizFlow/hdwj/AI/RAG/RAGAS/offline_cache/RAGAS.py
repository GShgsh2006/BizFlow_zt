
# 离线评估（上下文 Context Recall）

import json
import re

from BizFlow.hdwj.AI.RAG.RAGAS.RAGas import _text, _judge


async def context(sxw: list, reference: str):
    prompt = f"""
    你是一名专业的 RAGAS 评估工程师。

    你的任务是评估给定的检索上下文是否能够覆盖标准答案中的全部关键信息。

    请按照以下步骤执行：

    1. 分析标准答案，将其拆解为多个独立的关键事实或信息点。
    2. 逐一检查检索上下文，判断每个关键事实是否能够从上下文中得到支持。
    3. 如果上下文能够明确支持该事实，标记为1。
    4. 如果上下文无法支持该事实，标记为0。
    5. 统计所有关键事实的判断结果，计算最终 Context Recall 得分。

    评分规则：
    - 每个关键事实只有被上下文明确支持时，才算覆盖。
    - 上下文没有提及或无法支持的事实，不算覆盖。
    - 不要因为上下文与标准答案主题相似就判定为覆盖。
    - 不允许遗漏标准答案中的关键事实。

    计算公式：
    Context Recall = score为1的关键事实数量 / 关键事实总数量。

    评分范围为0到1：
    0代表完全没有覆盖。
    1代表完整覆盖。

    最终得分保留两位小数。
    如果没有提取到有效的关键事实，得分返回0。

    检索上下文：
    {sxw}

    标准答案：
    {reference}

    请严格返回JSON：
    {{
        "score": 0.0,
        "reason": "说明关键事实的拆分情况、每个事实的覆盖情况以及最终得分的计算依据"
    }}
    """

    text = _text(await _judge.ainvoke(prompt))
    # prompt 要的是 {"score": 0.0, "reason": "..."} 对象，不是数组。
    # 原来用 _json_array 解析，永远只能拿到 []，得分恒为 0。
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return 0.0
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return 0.0
    if not isinstance(data, dict):
        return 0.0
    try:
        score = float(data.get("score", 0.0))
    except (TypeError, ValueError):
        return 0.0
    # 模型偶尔会给出 1.2 或 -0.3，夹到合法区间
    return max(0.0, min(1.0, round(score, 4)))
