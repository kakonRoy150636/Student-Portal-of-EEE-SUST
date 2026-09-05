import uuid
from pydantic import BaseModel

class PresignedUploadRequest(BaseModel):
    file_name: str
    file_size: int
    mime_type: str

class FinalizeResourceRequest(BaseModel):
    file_key: str
    title: str
    category: str
    course_code: str
    file_name: str
    file_size_bytes: int
    mime_type: str
