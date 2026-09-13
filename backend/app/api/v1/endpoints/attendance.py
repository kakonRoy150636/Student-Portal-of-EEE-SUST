import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.attendance_service import AttendanceService
from app.schemas.attendance import AttendanceSessionCreate, AttendanceUpdateSchema
from app.api.dependencies import get_current_user, verify_course_teacher
from app.models.user import User

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.get("/my-summary")
async def get_my_summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = AttendanceService(db)
    return await service.get_student_summary(user.id)

@router.post("/sessions")
async def take_attendance(
    payload: AttendanceSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_course_teacher(payload.course_offering_id, user, db)
    service = AttendanceService(db)
    return await service.create_session(
        payload.course_offering_id, payload.session_date, payload.topic_discussed, user.id, payload.records
    )

@router.get("/courses/{offering_id}/summary")
async def get_attendance_summary(
    offering_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_course_teacher(offering_id, user, db)
    service = AttendanceService(db)
    return await service.get_course_summary(offering_id)

@router.put("/sessions/{session_id}")
async def update_attendance(
    session_id: uuid.UUID,
    payload: AttendanceUpdateSchema,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AttendanceService(db)
    return await service.update_records(session_id, payload.records)