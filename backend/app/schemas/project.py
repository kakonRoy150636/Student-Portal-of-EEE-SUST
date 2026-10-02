import uuid
from pydantic import BaseModel

class ProjectCreate(BaseModel):
    title: str
    abstract: str
    tier: str = "capstone_thesis"
    semester_id: int
    github_repo_url: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    title: str
    abstract: str
    tier: str
    supervisor_name: str | None = None
    github_repo_url: str | None = None
    member_count: int = 0

    class Config:
        from_attributes = True
