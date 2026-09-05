from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.resource_service import ResourceService
from app.schemas.resource import PresignedUploadRequest, FinalizeResourceRequest
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/resources", tags=["Resources"])

@router.get("/search")
async def search(q: str | None = None, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    service = ResourceService(db)
    return await service.search_resources(q)

@router.post("/presigned-upload")
async def presigned_upload(payload: PresignedUploadRequest, user: User = Depends(get_current_user)):
    return {"upload_url": f"http://localhost:9000/sust-eee-resources/{payload.file_name}", "file_key": payload.file_name}

@router.post("/finalize")
async def finalize(payload: FinalizeResourceRequest, user: User = Depends(get_current_user)):
    return {"status": "finalized", "resource_id": "res-123"}
