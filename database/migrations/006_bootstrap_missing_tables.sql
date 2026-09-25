-- Bootstrap the 25 tables that schema.sql declares but the running Postgres
-- volume never received.
--
-- The live database was initialised from an *older* schema.sql when its
-- volume was first created, and /docker-entrypoint-initdb.d only runs on an
-- empty volume -- so later edits to schema.sql never reach an existing
-- database. The consequence was severe: every endpoint backed by one of
-- these tables 500'd (GET /notifications -> "relation notifications does
-- not exist"), and the student dashboard could never show a real number
-- because attendance_sessions / course_enrollments did not exist either.
--
-- Revision 0001 is a deliberate no-op stamp, so no Alembic revision ever
-- created these tables. This migration is the missing link: it brings an
-- existing database up to what schema.sql already promised.
--
-- Purely additive -- no DROP, no data loss, no column rewrite. Every CREATE
-- is guarded with IF NOT EXISTS, so it is a no-op on a fresh database that
-- already received these tables from schema.sql at init time, and safe to
-- re-run. Tables are emitted in schema.sql declaration order so that every
-- foreign key target is created before the table referencing it.

-- 006 creates only the tables absent from older volumes. The enums those
-- tables reference are normally present, but CREATE TYPE has no IF NOT
-- EXISTS, so they are created defensively inside a duplicate_object guard:
-- on a database that already has them this is a silent no-op.
DO $$ BEGIN
    CREATE TYPE attendance_status AS ENUM ('present', 'absent', 'late', 'excused');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TYPE exchange_listing_type AS ENUM ('sell', 'lend', 'giveaway');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TYPE exchange_status AS ENUM ('available', 'reserved', 'completed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TYPE lab_condition AS ENUM ('operational', 'minor_defect', 'under_repair', 'decommissioned');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TYPE borrow_status AS ENUM ('pending_approval', 'approved', 'issued', 'returned', 'overdue', 'rejected');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS attendance_sessions (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
course_offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
session_date DATE NOT NULL DEFAULT CURRENT_DATE,
taken_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
topic_discussed TEXT,
editable_until TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '48 hours'),
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance_records (

id BIGSERIAL PRIMARY KEY,
session_id UUID NOT NULL REFERENCES attendance_sessions(id) ON DELETE CASCADE,
student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
status attendance_status NOT NULL DEFAULT 'present',
marked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
UNIQUE(session_id, student_id)
);

CREATE TABLE IF NOT EXISTS user_devices (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
fcm_token TEXT NOT NULL UNIQUE,
platform VARCHAR(20) NOT NULL DEFAULT 'web',
is_active BOOLEAN NOT NULL DEFAULT TRUE,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notification_preferences (

user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
enable_push BOOLEAN NOT NULL DEFAULT TRUE,
enable_10m_class_alert BOOLEAN NOT NULL DEFAULT TRUE,
enable_lab_reminders BOOLEAN NOT NULL DEFAULT TRUE,
enable_exam_alerts BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS notifications (

id BIGSERIAL PRIMARY KEY,
recipient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
title VARCHAR(200) NOT NULL,
body TEXT NOT NULL,
data_payload JSONB DEFAULT '{}'::jsonb,
is_read BOOLEAN NOT NULL DEFAULT FALSE,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS academic_resources (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
title VARCHAR(255) NOT NULL,
description TEXT,
category VARCHAR(50) NOT NULL,
course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
uploader_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
file_key VARCHAR(512) NOT NULL,
file_name VARCHAR(255) NOT NULL,
file_size_bytes BIGINT NOT NULL,
mime_type VARCHAR(100) NOT NULL,
download_count INT NOT NULL DEFAULT 0,
is_faculty_verified BOOLEAN NOT NULL DEFAULT FALSE,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
tsv_search TSVECTOR GENERATED ALWAYS AS (
to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))
) STORED
);

CREATE TABLE IF NOT EXISTS book_exchanges (

resource_id UUID PRIMARY KEY REFERENCES academic_resources(id) ON DELETE CASCADE,
author VARCHAR(200) NOT NULL,
edition VARCHAR(50),
transaction_type exchange_listing_type NOT NULL DEFAULT 'lend',
price_bdt NUMERIC(10, 2) DEFAULT 0.00,
status exchange_status NOT NULL DEFAULT 'available',
is_available BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS equipment_models (

id SERIAL PRIMARY KEY,
model_name VARCHAR(150) NOT NULL,
category VARCHAR(50) NOT NULL,
total_quantity INT NOT NULL DEFAULT 1,
available_quantity INT NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS equipment_assets (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
model_id INT NOT NULL REFERENCES equipment_models(id) ON DELETE RESTRICT,
asset_tag VARCHAR(50) NOT NULL UNIQUE,
lab_name VARCHAR(100) NOT NULL,
condition lab_condition NOT NULL DEFAULT 'operational',
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS equipment_borrow_requests (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
asset_id UUID NOT NULL REFERENCES equipment_assets(id) ON DELETE RESTRICT,
borrower_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
supervising_teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
purpose TEXT NOT NULL,
borrow_start TIMESTAMPTZ NOT NULL,
expected_return TIMESTAMPTZ NOT NULL,
status borrow_status NOT NULL DEFAULT 'pending_approval',
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS damage_reports (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
asset_id UUID NOT NULL REFERENCES equipment_assets(id) ON DELETE RESTRICT,
reported_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
description TEXT NOT NULL,
repair_cost_bdt NUMERIC(10, 2) DEFAULT 0.00,
resolved BOOLEAN NOT NULL DEFAULT FALSE,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lab_bench_reservations (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
lab_name VARCHAR(100) NOT NULL,
bench_number INT NOT NULL,
reserved_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
slot_range TSTZRANGE NOT NULL,
status VARCHAR(20) NOT NULL DEFAULT 'approved'
);

CREATE TABLE IF NOT EXISTS projects (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
title VARCHAR(255) NOT NULL,
abstract TEXT NOT NULL,
tier VARCHAR(50) NOT NULL DEFAULT 'capstone_thesis',
semester_id INT NOT NULL REFERENCES semesters(id) ON DELETE RESTRICT,
supervisor_id UUID REFERENCES users(id) ON DELETE SET NULL,
github_repo_url TEXT,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_members (

project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
role VARCHAR(30) NOT NULL DEFAULT 'member',
PRIMARY KEY (project_id, student_id)
);

CREATE TABLE IF NOT EXISTS supervisor_proposals (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
faculty_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
proposal_text TEXT NOT NULL,
status VARCHAR(20) NOT NULL DEFAULT 'pending',
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_publications (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
title VARCHAR(255) NOT NULL,
conference_name VARCHAR(200),
doi_url VARCHAR(255),
paper_file_key VARCHAR(512) NOT NULL,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS career_opportunities (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
posted_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
title VARCHAR(200) NOT NULL,
organization_name VARCHAR(150) NOT NULL,
type VARCHAR(50) NOT NULL,
location VARCHAR(120),
application_deadline DATE NOT NULL,
application_target TEXT NOT NULL,
description TEXT NOT NULL,
tags TEXT[] NOT NULL DEFAULT '{}',
is_verified BOOLEAN NOT NULL DEFAULT TRUE,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS student_cv_profiles (

user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
headline VARCHAR(200),
summary TEXT,
education JSONB DEFAULT '[]'::jsonb,
skills JSONB DEFAULT '{}'::jsonb,
experience JSONB DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS student_portfolios (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
slug VARCHAR(60) NOT NULL UNIQUE,
is_public BOOLEAN NOT NULL DEFAULT TRUE,
view_count INT NOT NULL DEFAULT 0,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_documents (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
title VARCHAR(255) NOT NULL,
file_path TEXT NOT NULL,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
document_id UUID REFERENCES knowledge_documents(id) ON DELETE CASCADE,
content TEXT NOT NULL,
embedding vector(768) NOT NULL,
tsv_content TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_chat_sessions (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
session_title VARCHAR(150) NOT NULL DEFAULT 'Course Q&A',
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_chat_messages (

id BIGSERIAL PRIMARY KEY,
session_id UUID NOT NULL REFERENCES ai_chat_sessions(id) ON DELETE CASCADE,
sender VARCHAR(10) NOT NULL,
content TEXT NOT NULL,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_generated_study_plans (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
plan_payload JSONB NOT NULL,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS course_offering_teachers (

id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
course_offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
role VARCHAR(50) NOT NULL DEFAULT 'course_teacher',
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
UNIQUE(course_offering_id, teacher_id)
);
