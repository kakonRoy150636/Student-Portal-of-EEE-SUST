import pytest

from app.services.attendance_service import AttendanceService

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize('statuses,percentage,below', [
    ([], 0.0, False),
    (['absent'], 0.0, True),
    (['present'], 100.0, False),
    (['present','late','present','absent'], 75.0, False),
    (['present','late','absent'], 66.67, True),
    (['present','excused'], 50.0, True),
])
async def test_student_percentage_edges(database, statuses, percentage, below):
    teacher, student = await database.user('teacher'), await database.user()
    offering = await database.offering(teacher=teacher)
    await database.enroll(student, offering)
    for status in statuses:
        await database.attendance(offering, teacher, [(student, status)])
    async with database.sessions() as db:
        summary = await AttendanceService(db).get_student_summary(student.id)
    assert summary['total_classes'] == len(statuses)
    assert summary['percentage'] == percentage
    assert summary['below_threshold'] is below


async def test_student_summary_excludes_classmates(database):
    teacher = await database.user('teacher')
    student, other = await database.user(), await database.user()
    offering = await database.offering(teacher=teacher)
    await database.enroll(student, offering)
    await database.enroll(other, offering)
    await database.attendance(offering, teacher, [(student,'absent'), (other,'present')])
    async with database.sessions() as db:
        summary = await AttendanceService(db).get_student_summary(student.id)
    assert summary['total_classes'] == 1 and summary['percentage'] == 0.0


async def test_unmarked_session_counts_in_denominator(database):
    teacher, student = await database.user('teacher'), await database.user()
    offering = await database.offering(teacher=teacher)
    await database.enroll(student, offering)
    await database.attendance(offering, teacher, [(student, 'present')])
    await database.attendance(offering, teacher, [])
    async with database.sessions() as db:
        summary = await AttendanceService(db).get_student_summary(student.id)
    assert summary['total_classes'] == 2 and summary['percentage'] == 50.0


async def test_zero_sessions_not_ineligible_in_teacher_summary(database):
    student = await database.user()
    offering = await database.offering()
    await database.enroll(student, offering)
    async with database.sessions() as db:
        rows = await AttendanceService(db).get_course_summary(offering)
    assert rows[0]['total_sessions'] == 0
    assert rows[0]['below_threshold'] is False


async def test_teacher_summary_threshold_and_student_isolation(database):
    teacher = await database.user('teacher')
    student, other = await database.user(), await database.user()
    offering = await database.offering(teacher=teacher)
    await database.enroll(student, offering)
    await database.enroll(other, offering)
    for index in range(4):
        await database.attendance(offering, teacher, [(student, 'present' if index<3 else 'absent'), (other, 'absent')])
    async with database.sessions() as db:
        rows = await AttendanceService(db).get_course_summary(offering)
    indexed = {r['student_id']: r for r in rows}
    assert indexed[student.id]['percentage'] == 75.0
    assert indexed[student.id]['below_threshold'] is False
    assert indexed[other.id]['percentage'] == 0.0


async def test_attendance_correction_ownership_and_deadline(api, database):
    teacher, stranger, student = await database.user('teacher'), await database.user('teacher'), await database.user()
    offering = await database.offering(teacher=teacher)
    await database.enroll(student, offering)
    session = await database.attendance(offering, teacher, [(student,'absent')])
    payload = {'records':[{'student_id':str(student.id),'status':'present'}]}
    path = f'/api/v1/attendance/sessions/{session}'
    for actor in [student, stranger]:
        assert (await api.put(path, json=payload, headers=database.headers(actor))).status_code == 403
    changed = await api.put(path, json=payload, headers=database.headers(teacher))
    assert changed.status_code == 200, changed.text
    assert await database.conn.fetchval('SELECT status FROM attendance_records WHERE session_id=$1', session) == 'present'
    await database.conn.execute("UPDATE attendance_sessions SET editable_until=now()-interval '1 second' WHERE id=$1", session)
    assert (await api.put(path, json=payload, headers=database.headers(teacher))).status_code == 400


async def test_teacher_can_record_real_enum_statuses(api, database):
    teacher, student = await database.user('teacher'), await database.user()
    offering = await database.offering(teacher=teacher)
    await database.enroll(student, offering)
    payload = {'course_offering_id':str(offering),'session_date':'2030-01-07',
               'records':[{'student_id':str(student.id),'status':'late'}]}
    result = await api.post('/api/v1/attendance/sessions', json=payload, headers=database.headers(teacher))
    assert result.status_code == 200, result.text
    assert await database.conn.fetchval('SELECT status FROM attendance_records') == 'late'
