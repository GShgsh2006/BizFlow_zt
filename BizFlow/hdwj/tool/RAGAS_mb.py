from pydantic import BaseModel
class Ragas(BaseModel):
    id: int
    name: str
    faithfulness: float
    answer_relevancy: float
    Context_Precision: float
    context_recall: float
