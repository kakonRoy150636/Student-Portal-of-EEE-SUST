from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return {"id": user.id, "identifier": user.identifier, "name": user.full_name, "role": user.role}
