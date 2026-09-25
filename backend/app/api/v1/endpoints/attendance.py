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
    # This route previously had no authorisation check at all, unlike its
    # siblings below, so any authenticated user -- including a student --
    # could rewrite the attendance of any session in the system by guessing
    # a UUID. Ownership is resolved first so that only the teacher who took
    # the session (or an admin) may amend it.
    offering_id = await AttendanceService(db).get_offering_id_for_session(session_id)
    await verify_course_teacher(offering_id, user, db)
    service = AttendanceService(db)
    return await service.update_records(session_id, payload.records)
