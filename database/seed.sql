INSERT INTO users (id, identifier, email, password_hash, full_name, role) VALUES
('00000000-0000-0000-0000-000000000001', 'admin', 'admin@sust.edu', '$2b$12$e8x5a34uK29oYx1e.Vz3A.w3yvVpWwX3fX/GzQ5.xZpQy8Z3A.w3y', 'System Administrator', 'super_admin'),
('00000000-0000-0000-0000-000000000002', 'faculty01', 'tasfiq@sust.edu', '$2b$12$e8x5a34uK29oYx1e.Vz3A.w3yvVpWwX3fX/GzQ5.xZpQy8Z3A.w3y', 'Dr. Md. Tasfiq Rahman', 'teacher'),
('00000000-0000-0000-0000-000000000003', '2021338001', 'kakon@student.sust.edu', '$2b$12$e8x5a34uK29oYx1e.Vz3A.w3yvVpWwX3fX/GzQ5.xZpQy8Z3A.w3y', 'Kakon Chandro Roy', 'student'),
('00000000-0000-0000-0000-000000000004', '2021338037', 'tanij@student.sust.edu', '$2b$12$e8x5a34uK29oYx1e.Vz3A.w3yvVpWwX3fX/GzQ5.xZpQy8Z3A.w3y', 'Tanij Roy', 'cr')
ON CONFLICT DO NOTHING;

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
