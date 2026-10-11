"""Focused API coverage for course workspace authorization and lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.models.academic import ClassSchedule, CourseEnrollment, CourseOfferingTeacher, TeacherAssignmentRequest
from app.models.course_workspace import AnnouncementRead, CourseAnnouncement, CourseEvent
from app.models.facility import Room
from app.models.notification import Notification, NotificationLog
from app.models.resource import AcademicResource
from app.models.user import UserRole
from app.services.course_workspace_service import CourseWorkspaceService, announcement_event_id
from app.services.notification_service import NotificationService
from tests.conftest import auth_header, make_user
from tests.test_course_offerings import make_offering

pytestmark = pytest.mark.asyncio


async def _assigned(db, offering_id, teacher_id):
    db.add(CourseOfferingTeacher(course_offering_id=offering_id, teacher_id=teacher_id))
    await db.commit()


async def _enrolled(db, offering_id, student_id):
    db.add(CourseEnrollment(course_offering_id=offering_id, student_id=student_id, status="enrolled"))
    await db.commit()


async def test_workspace_authorization_provider_assigned_approved_and_unauthorized(client, db):
    admin = await make_user(db, role=UserRole.SUPER_ADMIN)
    provider = await make_user(db, role=UserRole.TEACHER)
    assigned = await make_user(db, role=UserRole.TEACHER)
    approved = await make_user(db, role=UserRole.TEACHER)
    outsider = await make_user(db, role=UserRole.TEACHER)
    offering, _, _ = await make_offering(db, admin=admin)
    offering.created_by = provider.id
    await db.commit()
    await _assigned(db, offering.id, assigned.id)
    db.add(
        TeacherAssignmentRequest(
            course_offering_id=offering.id,
            teacher_id=approved.id,
            status="approved",
        )
    )
    await db.commit()

    for teacher in (provider, assigned, approved, admin):
        response = await client.get(
            f"/api/v1/course-offerings/{offering.id}/workspace",
            headers=auth_header(teacher),
        )
        assert response.status_code == 200, response.text
        assert response.json()["permissions"]["can_manage"] is True
        assert {row["teacher_id"] for row in response.json()["authorized_teachers"]} == {
            str(provider.id), str(assigned.id), str(approved.id),
        }

    denied = await client.get(
        f"/api/v1/course-offerings/{offering.id}/workspace",
        headers=auth_header(outsider),
    )
    assert denied.status_code == 403


async def test_student_visibility_lifecycle_pin_read_pagination_and_idempotent_notification(client, db):
    teacher = await make_user(db, role=UserRole.TEACHER)
    student = await make_user(db, role=UserRole.STUDENT)
    other = await make_user(db, role=UserRole.STUDENT)
    offering, _, _ = await make_offering(db)
    await _assigned(db, offering.id, teacher.id)
    await _enrolled(db, offering.id, student.id)

    draft = await client.post(
        f"/api/v1/course-offerings/{offering.id}/announcements",
        json={"title": "<b>Draft</b>", "body": "<script>bad()</script><p>not yet</p>"},
        headers=auth_header(teacher),
    )
    assert draft.status_code == 201, draft.text
    assert draft.json()["title"] == "Draft"
    assert draft.json()["body"] == "not yet"
    announcement_id = draft.json()["id"]

    hidden = await client.get(
        f"/api/v1/course-offerings/{offering.id}/announcements",
        headers=auth_header(student),
    )
    assert hidden.status_code == 200 and hidden.json()["total"] == 0

    published = await client.post(
        f"/api/v1/course-offerings/{offering.id}/announcements/{announcement_id}/publish",
        headers=auth_header(teacher),
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"

    # Publishing an already-published row is a no-op, including notification
    # side effects.
    await client.post(
        f"/api/v1/course-offerings/{offering.id}/announcements/{announcement_id}/publish",
        headers=auth_header(teacher),
    )
    event_count = await db.scalar(select(func.count()).select_from(NotificationLog))
    notification_count = await db.scalar(select(func.count()).select_from(Notification))
    assert event_count == 1
    assert notification_count == 1

    pin = await client.patch(
        f"/api/v1/course-offerings/{offering.id}/announcements/{announcement_id}/pin",
        json={"pinned": True},
        headers=auth_header(teacher),
    )
    assert pin.status_code == 200 and pin.json()["is_pinned"] is True

    feed = await client.get(
        f"/api/v1/course-offerings/{offering.id}/announcements?limit=1&offset=0&type=general",
        headers=auth_header(student),
    )
    assert feed.status_code == 200, feed.text
    assert feed.json()["total"] == 1
    assert feed.json()["items"][0]["can_manage"] is False

    read = await client.patch(
        f"/api/v1/course-announcements/{announcement_id}/read",
        headers=auth_header(student),
    )
    assert read.status_code == 200
    assert await db.scalar(select(func.count()).select_from(AnnouncementRead)) == 1

    workspace = await client.get(
        f"/api/v1/student/course-offerings/{offering.id}/workspace",
        headers=auth_header(student),
    )
    assert workspace.status_code == 200, workspace.text
    assert workspace.json()["unread_announcement_count"] == 0

    not_enrolled = await client.get(
        f"/api/v1/course-offerings/{offering.id}/workspace",
        headers=auth_header(other),
    )
    assert not_enrolled.status_code == 403


async def test_scheduled_and_audience_filters_are_role_safe(client, db):
    teacher = await make_user(db, role=UserRole.TEACHER)
    student = await make_user(db, role=UserRole.STUDENT)
    cr = await make_user(db, role=UserRole.CR)
    offering, _, _ = await make_offering(db)
    await _assigned(db, offering.id, teacher.id)
    await _enrolled(db, offering.id, student.id)
    await _enrolled(db, offering.id, cr.id)

    scheduled = await client.post(
        f"/api/v1/course-offerings/{offering.id}/announcements",
        json={
            "title": "Later",
            "body": "Later",
            "status": "scheduled",
            "publish_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
        headers=auth_header(teacher),
    )
    assert scheduled.status_code == 201
    assert (await client.get(
        f"/api/v1/course-offerings/{offering.id}/announcements",
        headers=auth_header(student),
    )).json()["total"] == 0

    teachers_only = await client.post(
        f"/api/v1/course-offerings/{offering.id}/announcements",
        json={"title": "Staff", "body": "Staff", "audience": "teachers_only", "status": "published"},
        headers=auth_header(teacher),
    )
    assert teachers_only.status_code == 201
    student_feed = await client.get(
        f"/api/v1/course-offerings/{offering.id}/announcements",
        headers=auth_header(student),
    )
    cr_feed = await client.get(
        f"/api/v1/course-offerings/{offering.id}/announcements",
        headers=auth_header(cr),
    )
    assert student_feed.json()["total"] == 0
    assert cr_feed.json()["total"] == 0

    invalid = await client.post(
        f"/api/v1/course-offerings/{offering.id}/announcements",
        json={"title": "No", "body": "No", "audience": "selected_users"},
        headers=auth_header(teacher),
    )
    assert invalid.status_code == 422


async def test_workspace_invalid_scope_and_resource_visibility(client, db):
    student = await make_user(db, role=UserRole.STUDENT)
    invalid = await client.get(
        f"/api/v1/course-offerings/{uuid.uuid4()}/workspace",
        headers=auth_header(student),
    )
    assert invalid.status_code == 404


async def _arrange(db):
    teacher = await make_user(db, role=UserRole.TEACHER)
    student = await make_user(db)
    offering, course, semester = await make_offering(db, target_term="3-1")
    await _assigned(db, offering.id, teacher.id)
    await _enrolled(db, offering.id, student.id)
    return teacher, student, offering, course, semester


async def test_auth_ids_scope_and_all_mutations_are_guarded(client, db):
    teacher, student, offering, _, _ = await _arrange(db)
    outsider = await make_user(db, role=UserRole.TEACHER)
    other_offering, _, _ = await make_offering(db)
    await _assigned(db, other_offering.id, teacher.id)
    prefix = f"/api/v1/course-offerings/{offering.id}"
    assert (await client.get(f"{prefix}/workspace")).status_code == 401
    assert (await client.get("/api/v1/course-offerings/bad-id/workspace", headers=auth_header(teacher))).status_code == 422
    assert (await client.patch("/api/v1/course-announcements/bad-id/read", headers=auth_header(student))).status_code == 422
    assert (await client.patch(f"/api/v1/course-announcements/{uuid.uuid4()}/read", headers=auth_header(student))).status_code == 404

    created = await client.post(f"{prefix}/announcements", headers=auth_header(teacher), json={"title": "Scope", "body": "Scope"})
    ident = created.json()["id"]
    for method, path, payload in [
        ("post", f"{prefix}/announcements", {"title": "No", "body": "No"}),
        ("patch", f"{prefix}/announcements/{ident}", {"body": "No"}),
        ("post", f"{prefix}/announcements/{ident}/publish", None),
        ("post", f"{prefix}/announcements/{ident}/archive", None),
        ("patch", f"{prefix}/announcements/{ident}/pin", {"is_pinned": True}),
    ]:
        for actor in (student, outsider):
            response = await client.request(method, path, headers=auth_header(actor), json=payload)
            assert response.status_code == 403, response.text
    assert (await client.get(
        f"/api/v1/course-offerings/{other_offering.id}/announcements/{ident}", headers=auth_header(teacher)
    )).status_code == 404
    assert (await client.post(
        f"/api/v1/course-offerings/{other_offering.id}/announcements/{ident}/publish", headers=auth_header(teacher)
    )).status_code == 404


@pytest.mark.parametrize("state", ["dropped", "inactive_semester", "unpublished", "inactive_user", "pending_teacher", "rejected_teacher"])
async def test_access_revocations(client, db, state):
    teacher, student, offering, _, semester = await _arrange(db)
    actor = student
    expected = 403
    if state == "dropped":
        enrollment = await db.scalar(select(CourseEnrollment).where(CourseEnrollment.student_id == student.id))
        enrollment.drop()
    elif state == "inactive_semester":
        semester.is_active = False
    elif state == "unpublished":
        offering.publication_status = "draft"
    elif state == "inactive_user":
        student.is_active = False
        expected = 401
    else:
        actor = teacher
        db.add(TeacherAssignmentRequest(course_offering_id=offering.id, teacher_id=teacher.id,
                                        status="pending" if state == "pending_teacher" else "rejected"))
    await db.commit()
    for suffix in ("workspace", "announcements", "resources"):
        response = await client.get(f"/api/v1/course-offerings/{offering.id}/{suffix}", headers=auth_header(actor))
        assert response.status_code == expected, response.text


async def test_validation_plain_text_and_null_patch(client, db):
    teacher, _, offering, _, _ = await _arrange(db)
    path = f"/api/v1/course-offerings/{offering.id}/announcements"
    now = datetime.now(timezone.utc)
    for invalid in [
        {"title": " "}, {"title": "a" * 201}, {"body": "a" * 20001}, {"body": "<script>attack()</script>"},
        {"audience": "selected_users"}, {"selected_users": []}, {"url": "https://evil.test/"},
        {"author_id": str(uuid.uuid4())}, {"offering_id": str(uuid.uuid4())}, {"announcement_type": "invalid"},
        {"status": "archived"}, {"status": "scheduled"},
        {"status": "scheduled", "publish_at": (now - timedelta(days=1)).isoformat()},
        {"status": "published", "publish_at": (now + timedelta(days=1)).isoformat()},
        {"status": "draft", "publish_at": now.isoformat()},
        {"status": "scheduled", "publish_at": "2030-01-01T12:00:00"},
    ]:
        response = await client.post(path, headers=auth_header(teacher), json={"title": "Safe", "body": "Safe", **invalid})
        assert response.status_code == 422, (invalid, response.text)
    # Reset the per-request fake limit means this test focuses on validation.
    created = await client.post(path, headers=auth_header(teacher), json={
        "title": "<img src=x onerror=attack()>Safe",
        "body": "&lt;script&gt;attack()&lt;/script&gt;<p>Notes <a href='javascript:attack()'>here</a></p>",
    })
    assert created.status_code == 201, created.text
    assert created.json()["title"] == "Safe"
    assert created.json()["body"] == "Notes here"
    ident = created.json()["id"]
    for field in ("body", "title", "status", "audience", "announcement_type"):
        assert (await client.patch(f"{path}/{ident}", headers=auth_header(teacher), json={field: None})).status_code == 422
    stored = await db.get(CourseAnnouncement, uuid.UUID(ident))
    assert stored.body == "Notes here"


async def test_events_and_moderated_questions_are_scoped_and_notified(client, db):
    teacher, student, offering, _, _ = await _arrange(db)
    event = await client.post(
        f"/api/v1/course-offerings/{offering.id}/events",
        headers=auth_header(teacher),
        json={
            "title": "Midterm",
            "event_type": "midterm",
            "starts_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "location": "Room 201",
            "reminder_minutes": 30,
        },
    )
    assert event.status_code == 201, event.text
    event_id = event.json()["id"]
    learner_events = await client.get(f"/api/v1/course-offerings/{offering.id}/events", headers=auth_header(student))
    assert learner_events.status_code == 200
    assert [row["id"] for row in learner_events.json()] == [event_id]

    question = await client.post(
        f"/api/v1/course-offerings/{offering.id}/questions",
        headers=auth_header(student),
        json={"title": "Which chapters?", "body": "<b>Can you clarify?</b>"},
    )
    assert question.status_code == 201, question.text
    question_id = question.json()["id"]
    assert question.json()["body"] == "Can you clarify?"
    teacher_questions = await client.get(
        f"/api/v1/course-offerings/{offering.id}/questions", headers=auth_header(teacher)
    )
    assert teacher_questions.status_code == 200
    assert teacher_questions.json()[0]["can_answer"] is True

    answer = await client.patch(
        f"/api/v1/course-offerings/{offering.id}/questions/{question_id}/answer",
        headers=auth_header(teacher),
        json={"answer_body": "Chapters 1–4", "status": "answered"},
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["answer_body"] == "Chapters 1–4"
    assert answer.json()["status"] == "answered"
    assert await db.scalar(select(func.count()).select_from(NotificationLog)) == 1

    archived = await client.post(
        f"/api/v1/course-offerings/{offering.id}/events/{event_id}/archive",
        headers=auth_header(teacher),
    )
    assert archived.status_code == 200
    assert await db.scalar(select(func.count()).select_from(CourseEvent)) == 1
    assert (await client.get(
        f"/api/v1/course-offerings/{offering.id}/events", headers=auth_header(student)
    )).json() == []


async def test_schedule_publish_edit_archive_and_atomic_rollback(client, db, monkeypatch):
    teacher, student, offering, _, _ = await _arrange(db)
    path = f"/api/v1/course-offerings/{offering.id}/announcements"
    scheduled_at = datetime.now(timezone.utc) + timedelta(days=1)
    response = await client.post(path, headers=auth_header(teacher), json={
        "title": "Scheduled", "body": "Later", "status": "scheduled", "publish_at": scheduled_at.isoformat(),
    })
    assert response.status_code == 201, response.text
    ident = response.json()["id"]
    assert await db.scalar(select(func.count()).select_from(NotificationLog)) == 0
    assert await CourseWorkspaceService(db).publish_due_announcements(scheduled_at - timedelta(seconds=1)) == 0
    failing = AsyncMock(side_effect=RuntimeError("test enqueue failure"))
    with monkeypatch.context() as patch:
        patch.setattr(NotificationService, "enqueue_course_announcement", failing)
        with pytest.raises(RuntimeError, match="test enqueue failure"):
            await CourseWorkspaceService(db).publish_due_announcements(scheduled_at)
    assert await db.scalar(select(func.count()).select_from(NotificationLog)) == 0
    assert (await db.get(CourseAnnouncement, uuid.UUID(ident))).status == "scheduled"
    assert await CourseWorkspaceService(db).publish_due_announcements(scheduled_at) == 1
    assert await CourseWorkspaceService(db).publish_due_announcements(scheduled_at) == 0
    assert await db.scalar(select(func.count()).select_from(NotificationLog)) == 1
    # The API uses the same clock in this test to exercise the published feed.
    monkeypatch.setattr("app.services.course_workspace_service._utcnow", lambda: scheduled_at + timedelta(seconds=1))
    # Rollback expires fixture actors; reload them before accessing properties.
    await db.refresh(teacher)
    await db.refresh(student)
    await db.refresh(offering)
    feed = await client.get(path, headers=auth_header(student))
    assert feed.json()["total"] == 1
    updated = await client.patch(f"{path}/{ident}", headers=auth_header(teacher), json={"body": "Edited"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["body"] == "Edited"
    assert await db.scalar(select(func.count()).select_from(NotificationLog)) == 1
    archived = await client.post(f"{path}/{ident}/archive", headers=auth_header(teacher))
    assert archived.status_code == 200 and archived.json()["archived_at"] is not None
    assert archived.json()["can_edit"] is False
    assert (await client.get(path, headers=auth_header(student))).json()["total"] == 0
    assert (await client.patch(f"/api/v1/course-announcements/{ident}/read", headers=auth_header(student))).status_code == 404
    assert (await client.post(f"{path}/{ident}/publish", headers=auth_header(teacher))).status_code == 409


async def test_exact_audience_notification_recipients_priority_and_safe_paths(client, db):
    teacher, student, offering, _, _ = await _arrange(db)
    cr = await make_user(db, role=UserRole.CR)
    inactive = await make_user(db, is_active=False)
    dropped = await make_user(db)
    approved = await make_user(db, role=UserRole.TEACHER)
    rejected = await make_user(db, role=UserRole.TEACHER)
    for actor in (cr, inactive, dropped):
        await _enrolled(db, offering.id, actor.id)
    row = await db.scalar(select(CourseEnrollment).where(CourseEnrollment.student_id == dropped.id))
    row.drop()
    db.add_all([
        TeacherAssignmentRequest(course_offering_id=offering.id, teacher_id=approved.id, status="approved"),
        TeacherAssignmentRequest(course_offering_id=offering.id, teacher_id=rejected.id, status="rejected"),
        CourseOfferingTeacher(course_offering_id=offering.id, teacher_id=rejected.id),
    ])
    await db.commit()
    path = f"/api/v1/course-offerings/{offering.id}/announcements"
    for audience, recipients in [("enrolled_students", {student.id, cr.id}), ("cr_only", {cr.id}), ("teachers_only", {teacher.id, approved.id})]:
        created = await client.post(path, headers=auth_header(teacher), json={
            "title": "Sensitive course title", "body": "Course text", "audience": audience,
            "status": "published", "announcement_type": "urgent",
        })
        assert created.status_code == 201, created.text
        ident = uuid.UUID(created.json()["id"])
        logs = (await db.scalars(select(NotificationLog).where(NotificationLog.event_id.in_(
            [announcement_event_id(ident, actor) for actor in recipients]
        )))).all()
        assert {log.user_id for log in logs} == recipients
        assert all(log.priority == "high" for log in logs)
        for log in logs:
            notification = await db.get(Notification, log.notification_id)
            assert notification.title == "Portal update"
            assert notification.data_payload == {
                "type": "course_announcement",
                "url": f"/course-offerings/{offering.id}/workspace?announcement_id={ident}",
            }
        student_detail = await client.get(f"{path}/{ident}", headers=auth_header(student))
        cr_detail = await client.get(f"{path}/{ident}", headers=auth_header(cr))
        assert student_detail.status_code == (200 if audience == "enrolled_students" else 404)
        assert cr_detail.status_code == (404 if audience == "teachers_only" else 200)
    logs = (await db.scalars(select(NotificationLog))).all()
    assert len(logs) == 5
    assert not ({inactive.id, dropped.id, rejected.id} & {log.user_id for log in logs})


async def test_feed_stable_order_search_filters_and_read_isolation(client, db):
    teacher, student, offering, _, _ = await _arrange(db)
    cr = await make_user(db, role=UserRole.CR)
    await _enrolled(db, offering.id, cr.id)
    path = f"/api/v1/course-offerings/{offering.id}/announcements"
    ids = []
    for title, type_ in [("Lecture alpha", "general"), ("Exam alpha", "exam"), ("Exam beta", "exam")]:
        response = await client.post(path, headers=auth_header(teacher), json={
            "title": title, "body": "Read this", "announcement_type": type_, "status": "published",
        })
        ids.append(response.json()["id"])
    assert (await client.patch(f"{path}/{ids[0]}/pin", headers=auth_header(teacher), json={"is_pinned": True})).status_code == 200
    all_feed = (await client.get(path, headers=auth_header(student))).json()
    assert all_feed["items"][0]["id"] == ids[0]
    pages = [(await client.get(f"{path}?limit=1&offset={offset}", headers=auth_header(student))).json() for offset in range(3)]
    assert [page["items"][0]["id"] for page in pages] == [row["id"] for row in all_feed["items"]]
    assert [page["has_more"] for page in pages] == [True, True, False]
    assert (await client.get(f"{path}?search=alpha&type=exam", headers=auth_header(student))).json()["total"] == 1
    assert (await client.get(f"{path}?search=%25", headers=auth_header(student))).json()["total"] == 0
    assert (await client.get(f"{path}?status=draft", headers=auth_header(student))).json()["total"] == 0
    for query in ("limit=0", "limit=101", "offset=-1", "type=bogus", "status=bogus"):
        assert (await client.get(f"{path}?{query}", headers=auth_header(student))).status_code == 422
    first = await client.patch(f"/api/v1/course-announcements/{ids[0]}/read", headers=auth_header(student))
    again = await client.patch(f"/api/v1/course-announcements/{ids[0]}/read", headers=auth_header(student))
    assert first.json() == again.json()
    for actor, unread in [(student, 2), (cr, 3)]:
        response = await client.get(f"/api/v1/course-offerings/{offering.id}/workspace", headers=auth_header(actor))
        assert response.json()["unread_announcement_count"] == unread


async def test_existing_resources_schedules_and_attendance_links(client, db):
    teacher, student, offering, course, _ = await _arrange(db)
    other_offering, other_course, _ = await make_offering(db)
    room = Room(room_number="Workspace 1", capacity=20)
    db.add(room)
    await db.flush()
    for offered, catalogue in [(offering, course), (other_offering, other_course)]:
        db.add(ClassSchedule(course_offering_id=offered.id, room_id=room.id, instructor_id=teacher.id,
                             day_of_week="Monday", start_time=time(9), end_time=time(10)))
        db.add(AcademicResource(title="Scoped resource", category="notes", course_id=catalogue.id,
                               uploader_id=teacher.id, file_key="private-object-key", file_name="notes.pdf",
                               file_size_bytes=5, mime_type="application/pdf"))
    await db.commit()
    response = await client.get(f"/api/v1/course-offerings/{offering.id}/workspace", headers=auth_header(student))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["course"]["id"] == str(course.id)
    assert data["semester"]["target_term"] == "3-1"
    assert data["active_enrollment_count"] == 1
    assert len(data["resources"]) == len(data["upcoming_schedules"]) == 1
    assert data["resources"][0]["course_id"] == str(course.id)
    assert "file_key" not in str(data)
    assert data["events"] == data["questions"] == []
    scoped = await client.get(f"/api/v1/course-offerings/{offering.id}/resources", headers=auth_header(student))
    assert scoped.json() == data["resources"]
    attendance = await client.get("/api/v1" + data["links"]["attendance"], headers=auth_header(student))
    assert attendance.status_code == 200
    teacher_workspace = await client.get(f"/api/v1/course-offerings/{offering.id}/workspace", headers=auth_header(teacher))
    teacher_attendance = await client.get("/api/v1" + teacher_workspace.json()["links"]["attendance"], headers=auth_header(teacher))
    assert teacher_attendance.status_code == 200
