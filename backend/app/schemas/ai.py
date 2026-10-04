from pydantic import BaseModel, Field

class AIQueryRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=1000, pattern=r"\S")
    course_code: str = Field(default="EEE 311", max_length=32, pattern=r"^[A-Za-z]{2,8}\s*\d{2,4}[A-Za-z]?$")

class AICitation(BaseModel):
    source_id: str
    chunk_id: str
    document_name: str
    page_number: int | None = None
    section: str | None = None

class AIQueryResponse(BaseModel):
    answer: str
    citations: list[AICitation] = Field(default_factory=list)
    grounded: bool
    quota_remaining: int
