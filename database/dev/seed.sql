-- Development seed data.
-- Run only via the opt-in seed-dev Compose service after Alembic upgrades.
--
-- NOTE: there is deliberately NO user account in this file. The previous
-- revision seeded a super_admin with a bcrypt hash committed to the
-- repository, which meant every fresh deployment -- including any public
-- demo -- shipped an administrator whose credential material was published.
-- A committed hash is crackable offline at leisure and cannot be rotated
-- without a new commit, so the account is now created at runtime from
-- BOOTSTRAP_ADMIN_* environment variables (see backend/app/core/bootstrap.py).
--
-- The course/room/semester rows below are reference data: they are not
-- secrets, and the application is unusable without a term and some rooms.

INSERT INTO semesters (id, title, is_active, start_date, end_date) VALUES
(1, 'Term 3-1, 2026', true, '2026-07-01', '2026-12-31')
ON CONFLICT DO NOTHING;

INSERT INTO courses (id, course_code, title, credit_hours, type, description) VALUES
('10000000-0000-0000-0000-000000000001', 'EEE 311', 'Electrical Machines II', 3.0, 'theory', 'Synchronous machines and induction motors.'),
('10000000-0000-0000-0000-000000000002', 'EEE 312', 'Electrical Machines II Lab', 1.5, 'lab', 'Bench testing of transformers and AC machines.'),
('10000000-0000-0000-0000-000000000003', 'EEE 315', 'Microprocessors & Microcontrollers', 3.0, 'theory', '8086 architecture and STM32 embedded design.')
ON CONFLICT DO NOTHING;

INSERT INTO rooms (id, room_number, building, capacity, is_lab) VALUES
(1, 'Room 301', 'IICT Building', 60, false),
(2, 'Room 304', 'IICT Building', 80, false),
(3, 'Electronics Lab', 'IICT Building', 40, true),
(4, 'Machines Lab', 'Old EEE Building', 35, true)
ON CONFLICT DO NOTHING;
