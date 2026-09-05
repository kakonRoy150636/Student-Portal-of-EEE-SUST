from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/courses", tags=["Courses"])

@router.get("")
async def list_courses(user: User = Depends(get_current_user)):
    return [
        {"course_code": "EEE 311", "title": "Electrical Machines II", "credits": 3.0},
        {"course_code": "EEE 312", "title": "Machines II Lab", "credits": 1.5}
    ]
