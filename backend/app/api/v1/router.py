from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, users, courses, schedules, rooms, attendance,
    notifications, resources, labs, projects, career, ai
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(courses.router)
api_router.include_router(schedules.router)
api_router.include_router(rooms.router)
api_router.include_router(attendance.router)
api_router.include_router(notifications.router)
api_router.include_router(resources.router)
api_router.include_router(labs.router)
api_router.include_router(projects.router)
api_router.include_router(career.router)
api_router.include_router(ai.router)
