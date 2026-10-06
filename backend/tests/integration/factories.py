"""Minimal valid rows against the production migrations, not ORM-created tables."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
import uuid

from app.core.security import get_password_hash, create_access_token

PASSWORD = 'Integration-test-pass-23'
START = datetime(2030, 1, 7, 10, tzinfo=timezone.utc)


class Factory:
    def __init__(self, conn, dsn, sessions):
        self.conn, self.dsn, self.sessions = conn, dsn, sessions

    async def user(self, role='student', active=True):
        ident = 'test-' + uuid.uuid4().hex[:16]
        row = await self.conn.fetchrow('''INSERT INTO users
            (identifier,email,password_hash,full_name,role,is_active)
            VALUES ($1,$2,$3,'Integration User',$4,$5) RETURNING *''',
            ident, ident+'@example.com', await get_password_hash(PASSWORD), role, active)
        return SimpleNamespace(**dict(row))

    @staticmethod
    def headers(user):
        return {'Authorization': 'Bearer '+create_access_token({'sub': str(user.id), 'role': user.role})}

    async def room(self, is_lab=False):
        return await self.conn.fetchval('''INSERT INTO rooms(room_number,capacity,is_lab)
            VALUES ($1,30,$2) RETURNING id''', 'R-'+uuid.uuid4().hex[:10], is_lab)

    async def semester(self):
        return await self.conn.fetchval('''INSERT INTO semesters(title,start_date,end_date,is_active)
            VALUES ($1,'2030-01-01','2030-06-30',true) RETURNING id''', uuid.uuid4().hex)

    async def offering(self, credits=3, semester=None, teacher=None, published=False):
        semester = semester or await self.semester()
        course = await self.conn.fetchval('''INSERT INTO courses(course_code,title,credit_hours,type)
            VALUES ($1,'Integration course',$2,'theory') RETURNING id''',
            'T'+uuid.uuid4().hex[:10], Decimal(str(credits)))
        offering = await self.conn.fetchval('''INSERT INTO course_offerings(course_id,semester_id,coordinator_id)
            VALUES ($1,$2,$3) RETURNING id''', course, semester, teacher.id if teacher else None)
        if published:
            await self.conn.execute(
                "UPDATE course_offerings SET publication_status='published' WHERE id=$1", offering
            )
        if teacher:
            await self.conn.execute('''INSERT INTO course_offering_teachers(course_offering_id,teacher_id)
                VALUES ($1,$2)''', offering, teacher.id)
        return offering

    async def enroll(self, user, offering):
        await self.conn.execute('''INSERT INTO course_enrollments(student_id,course_offering_id)
            VALUES ($1,$2)''', user.id, offering)

    async def attendance(self, offering, teacher, records, when=date(2030, 1, 7)):
        session = await self.conn.fetchval('''INSERT INTO attendance_sessions(course_offering_id,taken_by,session_date)
            VALUES ($1,$2,$3) RETURNING id''', offering, teacher.id, when)
        for user, status in records:
            await self.conn.execute('''INSERT INTO attendance_records(session_id,student_id,status)
                VALUES ($1,$2,$3)''', session, user.id, status)
        return session

    async def schedule(self, offering, teacher, room):
        return await self.conn.fetchval('''INSERT INTO class_schedules
            (course_offering_id,instructor_id,room_id,day_of_week,start_time,end_time)
            VALUES ($1,$2,$3,'monday','16:00','17:00') RETURNING id''', offering, teacher.id, room)

    @staticmethod
    def booking(room, start=START, end=None):
        return {'room_id': room, 'purpose': 'Integration booking',
                'start_time': start.isoformat(), 'end_time': (end or start+timedelta(hours=1)).isoformat()}

    @staticmethod
    def registration(offerings):
        ident = 'enroll-'+uuid.uuid4().hex[:16]
        return {'identifier': ident, 'email': ident+'@example.com', 'full_name': 'Enrollment Test',
                'password': PASSWORD, 'session_year': '26-30', 'current_term': '3-1',
                'course_selections': [{'course_offering_id': str(o)} for o in offerings]}
