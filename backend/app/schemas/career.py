import uuid
from datetime import date
from pydantic import BaseModel

class OpportunityCreate(BaseModel):
    title: str
    organization_name: str
    type: str
    location: str | None = None
    application_deadline: date
    application_target: str
    description: str
    tags: list[str] = []


class CareerOpportunityResponse(BaseModel):
    id: uuid.UUID
    title: str
    organization_name: str
    type: str
    location: str | None = None
    application_deadline: date
    application_target: str
    description: str
    tags: list[str] = []

    class Config:
        from_attributes = True
