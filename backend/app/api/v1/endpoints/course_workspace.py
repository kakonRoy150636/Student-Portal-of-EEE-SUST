"""Course workspace, announcement lifecycle and scoped resource endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import RequireRole, get_current_user
from app.api.request_limits import (
    limit_course_announcement_write,
    limit_course_question_write,
    limit_course_workspace,
    limit_resource_upload,
)
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.course_workspace import (
    AnnouncementPinRequest,
    AnnouncementStatusValue,
    AnnouncementTypeValue,
    CourseAnnouncementCreate,
    CourseAnnouncementFeedResponse,
    CourseAnnouncementReadResponse,
    CourseAnnouncementResponse,
    CourseAnnouncementUpdate,
    CourseEventCreate,
    CourseEventResponse,
    CourseEventUpdate,
    CourseQuestionAnswer,
    CourseQuestionCreate,
    CourseQuestionResponse,
    CourseResourceResponse,
    CourseResourceUpdate,
    CourseWorkspaceResponse,
)
from app.schemas.resource import (
    FinalizeResourceRequest,
    FinalizeResourceResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.services.course_workspace_service import CourseWorkspaceService

router = APIRouter(tags=["Course Workspace"])

LEARNER_ROLES = [UserRole.STUDENT, UserRole.CR]


async def require_workspace_manager(
    offering_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    await CourseWorkspaceService(db).require_manager(offering_id, user)
    return user


@router.get(
    "/course-offerings/{offering_id}/workspace",
    response_model=CourseWorkspaceResponse,
    dependencies=[Depends(limit_course_workspace)],
)
async def get_course_workspace(
    offering_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).workspace(offering_id, user)


@router.get(
    "/student/course-offerings/{offering_id}/workspace",
    response_model=CourseWorkspaceResponse,
    dependencies=[Depends(limit_course_workspace)],
)
async def get_student_course_workspace(
    offering_id: uuid.UUID,
    user: User = Depends(RequireRole(LEARNER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).workspace(offering_id, user)


@router.get(
    "/student/course-offerings/{offering_id}/announcements",
    response_model=CourseAnnouncementFeedResponse,
    dependencies=[Depends(limit_course_workspace)],
    include_in_schema=False,
)
@router.get(
    "/course-offerings/{offering_id}/announcements",
    response_model=CourseAnnouncementFeedResponse,
    dependencies=[Depends(limit_course_workspace)],
)
async def list_course_announcements(
    offering_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=100),
    q: str | None = Query(default=None, max_length=100),
    announcement_status: AnnouncementStatusValue | None = Query(default=None, alias="status"),
    announcement_status_filter: AnnouncementStatusValue | None = Query(default=None, alias="announcement_status"),
    announcement_type: AnnouncementTypeValue | None = Query(default=None, alias="type"),
    announcement_type_filter: AnnouncementTypeValue | None = Query(default=None, alias="announcement_type"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).list_announcements(
        offering_id,
        user,
        limit=limit,
        offset=offset,
        search=search or q,
        status=announcement_status or announcement_status_filter,
        announcement_type=announcement_type or announcement_type_filter,
    )


@router.get(
    "/course-offerings/{offering_id}/announcements/{announcement_id}",
    response_model=CourseAnnouncementResponse,
    dependencies=[Depends(limit_course_workspace)],
)
async def get_course_announcement(
    offering_id: uuid.UUID,
    announcement_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).get_announcement(offering_id, announcement_id, user)


@router.post(
    "/course-offerings/{offering_id}/announcements",
    response_model=CourseAnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_course_announcement_write)],
)
async def create_course_announcement(
    offering_id: uuid.UUID,
    payload: CourseAnnouncementCreate,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).create_announcement(offering_id, user, payload)


@router.patch(
    "/course-offerings/{offering_id}/announcements/{announcement_id}",
    response_model=CourseAnnouncementResponse,
    dependencies=[Depends(limit_course_announcement_write)],
)
async def update_course_announcement(
    offering_id: uuid.UUID,
    announcement_id: uuid.UUID,
    payload: CourseAnnouncementUpdate,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).update_announcement(offering_id, announcement_id, user, payload)


@router.patch(
    "/course-offerings/{offering_id}/announcements/{announcement_id}/publish",
    response_model=CourseAnnouncementResponse,
    dependencies=[Depends(limit_course_announcement_write)],
    include_in_schema=False,
)
@router.post(
    "/course-offerings/{offering_id}/announcements/{announcement_id}/publish",
    response_model=CourseAnnouncementResponse,
    dependencies=[Depends(limit_course_announcement_write)],
)
async def publish_course_announcement(
    offering_id: uuid.UUID,
    announcement_id: uuid.UUID,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).publish_announcement(offering_id, announcement_id, user)


@router.patch(
    "/course-offerings/{offering_id}/announcements/{announcement_id}/archive",
    response_model=CourseAnnouncementResponse,
    dependencies=[Depends(limit_course_announcement_write)],
    include_in_schema=False,
)
@router.post(
    "/course-offerings/{offering_id}/announcements/{announcement_id}/archive",
    response_model=CourseAnnouncementResponse,
    dependencies=[Depends(limit_course_announcement_write)],
)
async def archive_course_announcement(
    offering_id: uuid.UUID,
    announcement_id: uuid.UUID,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).archive_announcement(offering_id, announcement_id, user)


@router.patch(
    "/course-offerings/{offering_id}/announcements/{announcement_id}/pin",
    response_model=CourseAnnouncementResponse,
    dependencies=[Depends(limit_course_announcement_write)],
)
@router.post(
    "/course-offerings/{offering_id}/announcements/{announcement_id}/pin",
    response_model=CourseAnnouncementResponse,
    dependencies=[Depends(limit_course_announcement_write)],
    include_in_schema=False,
)
async def pin_course_announcement(
    offering_id: uuid.UUID,
    announcement_id: uuid.UUID,
    payload: AnnouncementPinRequest,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).pin_announcement(
        offering_id,
        announcement_id,
        user,
        payload.pinned,
    )


@router.patch(
    "/course-announcements/{announcement_id}/read",
    response_model=CourseAnnouncementReadResponse,
    dependencies=[Depends(limit_course_workspace)],
)
async def mark_course_announcement_read(
    announcement_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).mark_read(announcement_id, user)


@router.get(
    "/course-offerings/{offering_id}/resources",
    response_model=list[CourseResourceResponse],
    dependencies=[Depends(limit_course_workspace)],
)
async def list_course_workspace_resources(
    offering_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).list_resources(offering_id, user)


@router.post(
    "/course-offerings/{offering_id}/resources/presigned-upload",
    response_model=PresignedUploadResponse,
    dependencies=[Depends(limit_resource_upload)],
)
async def create_course_resource_upload(
    offering_id: uuid.UUID,
    payload: PresignedUploadRequest,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    from app.services.resource_service import ResourceService

    try:
        return await ResourceService(db).create_presigned_upload(payload, user)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(exc))


@router.post(
    "/course-offerings/{offering_id}/resources/finalize",
    response_model=FinalizeResourceResponse,
    dependencies=[Depends(limit_resource_upload)],
)
async def finalize_course_resource_upload(
    offering_id: uuid.UUID,
    payload: FinalizeResourceRequest,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    try:
        resource = await CourseWorkspaceService(db).finalize_resource_upload(offering_id, user, payload)
    except PermissionError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail=str(exc))
    except FileNotFoundError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(exc))
    return FinalizeResourceResponse(
        status="finalized",
        resource_id=resource.id,
        title=resource.title,
        file_name=resource.file_name,
    )


@router.patch(
    "/course-offerings/{offering_id}/resources/{resource_id}",
    response_model=CourseResourceResponse,
    dependencies=[Depends(limit_course_announcement_write)],
)
async def update_course_resource(
    offering_id: uuid.UUID,
    resource_id: uuid.UUID,
    payload: CourseResourceUpdate,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).update_resource(
        offering_id,
        resource_id,
        user,
        is_published=payload.is_published,
        archived=payload.archived,
    )


@router.get(
    "/course-offerings/{offering_id}/events",
    response_model=list[CourseEventResponse],
    dependencies=[Depends(limit_course_workspace)],
)
async def list_course_events(
    offering_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).list_events(offering_id, user)


@router.post(
    "/course-offerings/{offering_id}/events",
    response_model=CourseEventResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_course_announcement_write)],
)
async def create_course_event(
    offering_id: uuid.UUID,
    payload: CourseEventCreate,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).create_event(offering_id, user, payload)


@router.patch(
    "/course-offerings/{offering_id}/events/{event_id}",
    response_model=CourseEventResponse,
    dependencies=[Depends(limit_course_announcement_write)],
)
async def update_course_event(
    offering_id: uuid.UUID,
    event_id: uuid.UUID,
    payload: CourseEventUpdate,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).update_event(offering_id, event_id, user, payload)


@router.post(
    "/course-offerings/{offering_id}/events/{event_id}/archive",
    response_model=dict[str, object],
    dependencies=[Depends(limit_course_announcement_write)],
)
async def archive_course_event(
    offering_id: uuid.UUID,
    event_id: uuid.UUID,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).archive_event(offering_id, event_id, user)


@router.get(
    "/course-offerings/{offering_id}/questions",
    response_model=list[CourseQuestionResponse],
    dependencies=[Depends(limit_course_workspace)],
)
async def list_course_questions(
    offering_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).list_questions(offering_id, user)


@router.post(
    "/course-offerings/{offering_id}/questions",
    response_model=CourseQuestionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_course_question_write)],
)
async def create_course_question(
    offering_id: uuid.UUID,
    payload: CourseQuestionCreate,
    user: User = Depends(RequireRole(LEARNER_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).create_question(offering_id, user, payload)


@router.patch(
    "/course-offerings/{offering_id}/questions/{question_id}/answer",
    response_model=CourseQuestionResponse,
    dependencies=[Depends(limit_course_question_write)],
)
async def answer_course_question(
    offering_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: CourseQuestionAnswer,
    user: User = Depends(require_workspace_manager),
    db: AsyncSession = Depends(get_db),
):
    return await CourseWorkspaceService(db).answer_question(offering_id, question_id, user, payload)


__all__ = ["router"]
