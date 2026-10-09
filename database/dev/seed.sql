-- Development seed data.
-- Run only via the opt-in seed-dev Compose service after Alembic upgrades.
--
-- This file is development-only. The seed-dev service refuses to run unless
-- ENVIRONMENT=development, and the accounts below use intentionally fixed
-- local passwords for manual testing. Never use these identities or passwords
-- outside a disposable development database.
--
-- Login identities:
--   dev-admin     / DevAdmin123!
--   dev-teacher-1 / DevTeacher123!
--   dev-teacher-2 / DevTeacher123!
--   dev-student-1 / DevStudent123!
--   dev-student-2 / DevStudent123!
--   tasfik-rahman / password123
--   2023338049 (Kakon Chandro Roy) / password123
--   2023338050 (Tanij Roy, CR) / password123

-- One active semester. Natural-key upsert makes a safe rerun keep one row.
INSERT INTO semesters (title, target_term, is_active, start_date, end_date) VALUES
('Term 3-1, 2026', '3-1', true, '2026-07-01', '2026-12-31')
ON CONFLICT (title) DO UPDATE SET
    target_term = EXCLUDED.target_term,
    is_active = EXCLUDED.is_active,
    start_date = EXCLUDED.start_date,
    end_date = EXCLUDED.end_date;

-- Development identities. Password hashes are bcrypt hashes for the passwords
-- documented above; they are not production credentials.
INSERT INTO users (identifier, email, password_hash, full_name, role, is_active) VALUES
('dev-admin', 'dev-admin@example.com', '$2b$12$toHpMeM9kLlmD.Q1vzHwL..p7fhpXbWKF459SCG6gr.jXDYjW6biO', 'Development Administrator', 'super_admin', true),
('dev-teacher-1', 'dev-teacher-1@example.com', '$2b$12$RcfxHMvT.jr4xgfJoNvE1u6ww.gD0WkIjr47uuTzkJvpgKZe0M.nK', 'Dr. Samira Rahman', 'teacher', true),
('dev-teacher-2', 'dev-teacher-2@example.com', '$2b$12$RcfxHMvT.jr4xgfJoNvE1u6ww.gD0WkIjr47uuTzkJvpgKZe0M.nK', 'Dr. Farhan Karim', 'teacher', true),
('dev-student-1', 'dev-student-1@example.com', '$2b$12$XDDP1oLSMvX4bGuzkT.QFus3lGjyOuyTGCKJ.H5XrFqJNw7LviPwy', 'Nabila Ahmed', 'student', true),
('dev-student-2', 'dev-student-2@example.com', '$2b$12$XDDP1oLSMvX4bGuzkT.QFus3lGjyOuyTGCKJ.H5XrFqJNw7LviPwy', 'Tanvir Hossain', 'student', true),
('tasfik-rahman', 'tasfik.rahman@example.com', '$2b$12$Hq4uAadGIUPP9Z.sCAE40.dyzWoIMqQC.RppU1OwPB8r4dwULBxAq', 'Tasfik Rahman', 'teacher', true),
('2023338049', 'kakon.chandro.roy@example.com', '$2b$12$Hq4uAadGIUPP9Z.sCAE40.dyzWoIMqQC.RppU1OwPB8r4dwULBxAq', 'Kakon Chandro Roy', 'student', true),
('2023338050', 'tanij.roy@example.com', '$2b$12$Hq4uAadGIUPP9Z.sCAE40.dyzWoIMqQC.RppU1OwPB8r4dwULBxAq', 'Tanij Roy', 'cr', true)
ON CONFLICT (identifier) DO UPDATE SET
    email = EXCLUDED.email,
    password_hash = EXCLUDED.password_hash,
    full_name = EXCLUDED.full_name,
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active;

INSERT INTO profiles_faculty (user_id, designation, room_number, office_hours)
SELECT id, 'Assistant Professor', 'EEE-201', 'Sunday and Tuesday, 10:00–12:00'
FROM users WHERE identifier = 'dev-teacher-1'
ON CONFLICT (user_id) DO UPDATE SET
    designation = EXCLUDED.designation,
    room_number = EXCLUDED.room_number,
    office_hours = EXCLUDED.office_hours;

INSERT INTO profiles_faculty (user_id, designation, room_number, office_hours)
SELECT id, 'Lecturer', 'EEE-202', 'Monday and Wednesday, 14:00–16:00'
FROM users WHERE identifier = 'dev-teacher-2'
ON CONFLICT (user_id) DO UPDATE SET
    designation = EXCLUDED.designation,
    room_number = EXCLUDED.room_number,
    office_hours = EXCLUDED.office_hours;

INSERT INTO profiles_faculty (user_id, designation, room_number, office_hours)
SELECT id, 'Lecturer', 'EEE-203', 'Sunday and Tuesday, 13:00–15:00'
FROM users WHERE identifier = 'tasfik-rahman'
ON CONFLICT (user_id) DO UPDATE SET
    designation = EXCLUDED.designation,
    room_number = EXCLUDED.room_number,
    office_hours = EXCLUDED.office_hours;

INSERT INTO profiles_student (user_id, session_year, current_term)
SELECT id, '2023-2024', '3-1'
FROM users WHERE identifier = 'dev-student-1'
ON CONFLICT (user_id) DO UPDATE SET
    session_year = EXCLUDED.session_year,
    current_term = EXCLUDED.current_term;

INSERT INTO profiles_student (user_id, session_year, current_term)
SELECT id, '2023-2024', '3-1'
FROM users WHERE identifier = 'dev-student-2'
ON CONFLICT (user_id) DO UPDATE SET
    session_year = EXCLUDED.session_year,
    current_term = EXCLUDED.current_term;

INSERT INTO profiles_student (user_id, session_year, current_term)
SELECT id, '2023-2024', '3-1'
FROM users WHERE identifier = '2023338049'
ON CONFLICT (user_id) DO UPDATE SET
    session_year = EXCLUDED.session_year,
    current_term = EXCLUDED.current_term;

INSERT INTO profiles_student (user_id, session_year, current_term)
SELECT id, '2023-2024', '3-1'
FROM users WHERE identifier = '2023338050'
ON CONFLICT (user_id) DO UPDATE SET
    session_year = EXCLUDED.session_year,
    current_term = EXCLUDED.current_term;

INSERT INTO courses (id, course_code, title, credit_hours, type, description) VALUES
('10000000-0000-0000-0000-000000000001', 'EEE 311', 'Electrical Machines II', 3.0, 'theory', 'Synchronous machines and induction motors.'),
('10000000-0000-0000-0000-000000000002', 'EEE 312', 'Electrical Machines II Lab', 1.5, 'lab', 'Bench testing of transformers and AC machines.'),
('10000000-0000-0000-0000-000000000003', 'EEE 315', 'Microprocessors & Microcontrollers', 3.0, 'theory', '8086 architecture and STM32 embedded design.'),
('10000000-0000-0000-0000-000000000004', 'EEE 321', 'Digital Signal Processing', 3.0, 'theory', 'Discrete-time signals, transforms, and digital filter design.')
ON CONFLICT (course_code) DO UPDATE SET
    title = EXCLUDED.title,
    credit_hours = EXCLUDED.credit_hours,
    type = EXCLUDED.type,
    description = EXCLUDED.description;

-- Three published offerings and one draft offering for the admin workflow.
INSERT INTO course_offerings (
    course_id, semester_id, created_by, publication_status, published_by, published_at
)
SELECT c.id, s.id, a.id, 'published', a.id, CURRENT_TIMESTAMP
FROM courses c
JOIN semesters s ON s.title = 'Term 3-1, 2026'
JOIN users a ON a.identifier = 'dev-admin'
WHERE c.course_code = 'EEE 311'
ON CONFLICT (course_id, semester_id) DO UPDATE SET
    created_by = EXCLUDED.created_by,
    publication_status = EXCLUDED.publication_status,
    published_by = EXCLUDED.published_by,
    published_at = EXCLUDED.published_at,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO course_offerings (
    course_id, semester_id, created_by, publication_status, published_by, published_at
)
SELECT c.id, s.id, a.id, 'published', a.id, CURRENT_TIMESTAMP
FROM courses c
JOIN semesters s ON s.title = 'Term 3-1, 2026'
JOIN users a ON a.identifier = 'dev-admin'
WHERE c.course_code = 'EEE 312'
ON CONFLICT (course_id, semester_id) DO UPDATE SET
    created_by = EXCLUDED.created_by,
    publication_status = EXCLUDED.publication_status,
    published_by = EXCLUDED.published_by,
    published_at = EXCLUDED.published_at,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO course_offerings (
    course_id, semester_id, created_by, publication_status, published_by, published_at
)
SELECT c.id, s.id, a.id, 'published', a.id, CURRENT_TIMESTAMP
FROM courses c
JOIN semesters s ON s.title = 'Term 3-1, 2026'
JOIN users a ON a.identifier = 'dev-admin'
WHERE c.course_code = 'EEE 315'
ON CONFLICT (course_id, semester_id) DO UPDATE SET
    created_by = EXCLUDED.created_by,
    publication_status = EXCLUDED.publication_status,
    published_by = EXCLUDED.published_by,
    published_at = CURRENT_TIMESTAMP,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO course_offerings (course_id, semester_id, created_by, publication_status)
SELECT c.id, s.id, a.id, 'draft'
FROM courses c
JOIN semesters s ON s.title = 'Term 3-1, 2026'
JOIN users a ON a.identifier = 'dev-admin'
WHERE c.course_code = 'EEE 321'
ON CONFLICT (course_id, semester_id) DO UPDATE SET
    created_by = EXCLUDED.created_by,
    publication_status = EXCLUDED.publication_status,
    published_by = NULL,
    published_at = NULL,
    updated_at = CURRENT_TIMESTAMP;

-- One approved assignment, a second approved assignment, and one pending request.
INSERT INTO teacher_assignment_requests (
    course_offering_id, teacher_id, status, decided_by, decided_at, rejection_reason
)
SELECT o.id, t.id, 'approved', a.id, CURRENT_TIMESTAMP, NULL
FROM course_offerings o
JOIN courses c ON c.id = o.course_id
JOIN users t ON t.identifier = 'dev-teacher-1'
JOIN users a ON a.identifier = 'dev-admin'
WHERE c.course_code = 'EEE 311'
ON CONFLICT (course_offering_id, teacher_id) DO UPDATE SET
    status = EXCLUDED.status,
    decided_by = EXCLUDED.decided_by,
    decided_at = EXCLUDED.decided_at,
    rejection_reason = NULL,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO teacher_assignment_requests (
    course_offering_id, teacher_id, status, decided_by, decided_at, rejection_reason
)
SELECT o.id, t.id, 'pending', NULL, NULL, NULL
FROM course_offerings o
JOIN courses c ON c.id = o.course_id
JOIN users t ON t.identifier = 'dev-teacher-2'
WHERE c.course_code = 'EEE 312'
ON CONFLICT (course_offering_id, teacher_id) DO UPDATE SET
    status = EXCLUDED.status,
    decided_by = NULL,
    decided_at = NULL,
    rejection_reason = NULL,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO teacher_assignment_requests (
    course_offering_id, teacher_id, status, decided_by, decided_at, rejection_reason
)
SELECT o.id, t.id, 'approved', a.id, CURRENT_TIMESTAMP, NULL
FROM course_offerings o
JOIN courses c ON c.id = o.course_id
JOIN users t ON t.identifier = 'dev-teacher-2'
JOIN users a ON a.identifier = 'dev-admin'
WHERE c.course_code = 'EEE 315'
ON CONFLICT (course_offering_id, teacher_id) DO UPDATE SET
    status = EXCLUDED.status,
    decided_by = EXCLUDED.decided_by,
    decided_at = EXCLUDED.decided_at,
    rejection_reason = NULL,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO course_offering_teachers (course_offering_id, teacher_id, role)
SELECT o.id, t.id, 'course_teacher'
FROM course_offerings o
JOIN courses c ON c.id = o.course_id
JOIN users t ON t.identifier = 'dev-teacher-1'
WHERE c.course_code = 'EEE 311'
ON CONFLICT (course_offering_id, teacher_id) DO UPDATE SET role = EXCLUDED.role;

INSERT INTO course_offering_teachers (course_offering_id, teacher_id, role)
SELECT o.id, t.id, 'course_teacher'
FROM course_offerings o
JOIN courses c ON c.id = o.course_id
JOIN users t ON t.identifier = 'dev-teacher-2'
WHERE c.course_code = 'EEE 315'
ON CONFLICT (course_offering_id, teacher_id) DO UPDATE SET role = EXCLUDED.role;

-- One active enrollment for each sample student.
INSERT INTO course_enrollments (course_offering_id, student_id, status, advisor_approved)
SELECT o.id, u.id, 'enrolled', true
FROM course_offerings o
JOIN courses c ON c.id = o.course_id
JOIN users u ON u.identifier = 'dev-student-1'
WHERE c.course_code = 'EEE 311'
ON CONFLICT (course_offering_id, student_id) DO UPDATE SET
    status = EXCLUDED.status,
    advisor_approved = EXCLUDED.advisor_approved,
    dropped_at = NULL,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO course_enrollments (course_offering_id, student_id, status, advisor_approved)
SELECT o.id, u.id, 'enrolled', true
FROM course_offerings o
JOIN courses c ON c.id = o.course_id
JOIN users u ON u.identifier = 'dev-student-2'
WHERE c.course_code = 'EEE 315'
ON CONFLICT (course_offering_id, student_id) DO UPDATE SET
    status = EXCLUDED.status,
    advisor_approved = EXCLUDED.advisor_approved,
    dropped_at = NULL,
    updated_at = CURRENT_TIMESTAMP;

INSERT INTO rooms (id, room_number, building, capacity, is_lab) VALUES
(1, 'Room 301', 'IICT Building', 60, false),
(2, 'Room 304', 'IICT Building', 80, false),
(3, 'Electronics Lab', 'IICT Building', 40, true),
(4, 'Machines Lab', 'Old EEE Building', 35, true)
ON CONFLICT DO NOTHING;
