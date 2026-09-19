--
-- PostgreSQL database dump
--

\restrict BDgdYOdWXsvUlRb4JadPtCgG7OfKondaNqh3x4ipynbHZa8S9BODvBb4whIJ9aG

-- Dumped from database version 16.15 (Debian 16.15-1.pgdg12+2)
-- Dumped by pg_dump version 16.15 (Debian 16.15-1.pgdg12+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: courses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.courses (id, course_code, title, credit_hours, type, description) FROM stdin;
\.


--
-- Data for Name: semesters; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.semesters (id, title, is_active, start_date, end_date) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, identifier, email, password_hash, full_name, role, is_active, created_at, updated_at, avatar_key) FROM stdin;
\.


--
-- Data for Name: course_offerings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.course_offerings (id, course_id, semester_id, coordinator_id) FROM stdin;
\.


--
-- Data for Name: rooms; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.rooms (id, room_number, building, capacity, is_lab, amenities) FROM stdin;
\.


--
-- Data for Name: class_schedules; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.class_schedules (id, course_offering_id, room_id, instructor_id, day_of_week, start_time, end_time) FROM stdin;
\.


--
-- Data for Name: course_enrollments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.course_enrollments (id, course_offering_id, student_id, status, advisor_approved, enrolled_at) FROM stdin;
\.


--
-- Data for Name: password_reset_tokens; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.password_reset_tokens (id, user_id, token_hash, is_used, expires_at, created_at) FROM stdin;
\.


--
-- Data for Name: profiles_faculty; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.profiles_faculty (user_id, designation, room_number, office_hours, research_areas) FROM stdin;
\.


--
-- Data for Name: profiles_student; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.profiles_student (user_id, session_year, current_term, blood_group, contact_number, github_profile, linkedin_profile) FROM stdin;
\.


--
-- Name: course_enrollments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.course_enrollments_id_seq', 1, false);


--
-- Name: rooms_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.rooms_id_seq', 1, false);


--
-- Name: semesters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.semesters_id_seq', 1, false);


--
-- PostgreSQL database dump complete
--

\unrestrict BDgdYOdWXsvUlRb4JadPtCgG7OfKondaNqh3x4ipynbHZa8S9BODvBb4whIJ9aG

