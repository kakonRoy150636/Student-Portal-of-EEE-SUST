-- Demo/reference data only. NO user accounts are seeded here.
--
-- Earlier revisions of this file shipped four accounts (including a
-- super_admin) that all shared one committed bcrypt hash, which meant the
-- administrative password was whatever string produced that hash and could
-- be checked offline by anyone with the repository. Credentials do not
-- belong in version control:
--
--   * an administrator is created from BOOTSTRAP_ADMIN_* environment
--     variables on first start, with a forced password change; or
--   * people register through /auth/register/* and are approved by an admin.
--
-- Everything below is reference data (semesters, courses, rooms, offerings)
-- that contains no secrets.

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
