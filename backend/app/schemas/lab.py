import uuid
from datetime import datetime
from pydantic import BaseModel

class BorrowRequestCreate(BaseModel):
    asset_id: uuid.UUID
    supervising_teacher_id: uuid.UUID
    purpose: str
    borrow_start: datetime
    expected_return: datetime
