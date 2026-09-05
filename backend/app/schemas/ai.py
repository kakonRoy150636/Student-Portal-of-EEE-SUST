from pydantic import BaseModel

class AIQueryRequest(BaseModel):
    prompt: str
    course_code: str = "EEE 311"

class AIQueryResponse(BaseModel):
    answer: str
    citations: list[str] = []
