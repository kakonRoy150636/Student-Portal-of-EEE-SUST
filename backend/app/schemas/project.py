import uuid
from pydantic import BaseModel

class ProjectCreate(BaseModel):
    title: str
    abstract: str
    tier: str = "capstone_thesis"
    semester_id: int
    github_repo_url: str | None = None
