CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Enums
CREATE TYPE user_role AS ENUM ('super_admin', 'teacher', 'cr', 'student', 'lab_assistant', 'alumni');
CREATE TYPE course_type AS ENUM ('theory', 'lab', 'thesis', 'project');
CREATE TYPE reservation_status AS ENUM ('pending', 'approved', 'rejected', 'cancelled');
CREATE TYPE attendance_status AS ENUM ('present', 'absent', 'late', 'excused');
CREATE TYPE exchange_listing_type AS ENUM ('sell', 'lend', 'giveaway');
CREATE TYPE exchange_status AS ENUM ('available', 'reserved', 'completed');
CREATE TYPE lab_condition AS ENUM ('operational', 'minor_defect', 'under_repair', 'decommissioned');
CREATE TYPE borrow_status AS ENUM ('pending_approval', 'approved', 'issued', 'returned', 'overdue', 'rejected');

-- 1. Identity & Auth
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier VARCHAR(32) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role user_role NOT NULL DEFAULT 'student',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE users ADD COLUMN avatar_key VARCHAR(512);

CREATE TABLE profiles_student (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    session_year VARCHAR(9) NOT NULL,
    current_term VARCHAR(4) NOT NULL,
    blood_group VARCHAR(3),
    contact_number VARCHAR(20),
    github_profile TEXT,
    linkedin_profile TEXT
);

CREATE TABLE profiles_faculty (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    designation VARCHAR(100) NOT NULL,
    room_number VARCHAR(50),
    office_hours TEXT,
    research_areas TEXT[] DEFAULT '{}'
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_family UUID NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Academics & Schedule
CREATE TABLE semesters (
    id SERIAL PRIMARY KEY,
    title VARCHAR(50) NOT NULL UNIQUE,
    target_term VARCHAR(4),
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    CONSTRAINT ck_semesters_target_term CHECK (
        target_term IS NULL OR target_term IN
        ('1-1', '1-2', '2-1', '2-2', '3-1', '3-2', '4-1', '4-2')
    )
);
CREATE INDEX ix_semesters_active ON semesters (id) WHERE is_active = TRUE;

CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_code VARCHAR(12) NOT NULL UNIQUE,
    title VARCHAR(150) NOT NULL,
    credit_hours NUMERIC(3, 1) NOT NULL,
    type course_type NOT NULL,
    description TEXT
);

CREATE TABLE course_offerings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
    semester_id INT NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
    coordinator_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    publication_status VARCHAR(20) NOT NULL DEFAULT 'draft',
    published_by UUID REFERENCES users(id) ON DELETE SET NULL,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_course_offerings_publication_status CHECK (publication_status IN ('draft', 'published')),
    UNIQUE(course_id, semester_id)
);
CREATE INDEX ix_course_offerings_semester_publication
    ON course_offerings (semester_id, publication_status);

CREATE TABLE teacher_assignment_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    decided_by UUID REFERENCES users(id) ON DELETE SET NULL,
    decided_at TIMESTAMPTZ,
    rejection_reason VARCHAR(1000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_teacher_assignment_requests_offering_teacher UNIQUE (course_offering_id, teacher_id),
    CONSTRAINT ck_teacher_assignment_requests_status CHECK (status IN ('pending', 'approved', 'rejected'))
);
CREATE INDEX ix_teacher_assignment_requests_status_created
    ON teacher_assignment_requests (status, created_at);
CREATE INDEX ix_teacher_assignment_requests_teacher
    ON teacher_assignment_requests (teacher_id);

CREATE TABLE course_enrollments (
    id BIGSERIAL PRIMARY KEY,
    course_offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'enrolled',
    advisor_approved BOOLEAN NOT NULL DEFAULT FALSE,
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dropped_at TIMESTAMPTZ,
    CONSTRAINT ck_course_enrollments_status CHECK (status IN ('enrolled', 'main', 'improvement', 'drop')),
    UNIQUE(course_offering_id, student_id)
);
CREATE INDEX ix_course_enrollments_student_status ON course_enrollments (student_id, status);
CREATE INDEX ix_course_enrollments_notification_recipients
    ON course_enrollments (course_offering_id, student_id)
    WHERE status IN ('enrolled', 'main', 'improvement');

CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    room_number VARCHAR(50) NOT NULL UNIQUE,
    building VARCHAR(100) NOT NULL DEFAULT 'Department of EEE, IICT Building',
    capacity INT NOT NULL,
    is_lab BOOLEAN NOT NULL DEFAULT FALSE,
    amenities JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE class_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
    room_id INT NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    instructor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    day_of_week VARCHAR(15) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL
);
CREATE INDEX ix_class_schedules_day_start ON class_schedules (day_of_week, start_time);

CREATE TABLE room_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id INT NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    reserved_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    purpose TEXT NOT NULL,
    slot_range TSTZRANGE NOT NULL,
    status reservation_status NOT NULL DEFAULT 'pending',
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMPTZ,
    rejection_reason VARCHAR(255),
    cancelled_by UUID REFERENCES users(id) ON DELETE SET NULL,
    cancellation_reason VARCHAR(255),
    cancellation_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT no_overlapping_room_bookings EXCLUDE USING gist (
        room_id WITH =,
        slot_range WITH &&
    ) WHERE (status IN ('approved', 'pending'))
);

-- 3. Attendance
CREATE TABLE attendance_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
    session_date DATE NOT NULL DEFAULT CURRENT_DATE,
    taken_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    topic_discussed TEXT,
    editable_until TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP + INTERVAL '48 hours'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE attendance_records (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status attendance_status NOT NULL DEFAULT 'present',
    marked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, student_id)
);

-- 4. Notifications
CREATE TABLE user_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fcm_token TEXT NOT NULL UNIQUE,
    platform VARCHAR(20) NOT NULL DEFAULT 'web',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notification_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    enable_push BOOLEAN NOT NULL DEFAULT TRUE,
    enable_10m_class_alert BOOLEAN NOT NULL DEFAULT TRUE,
    enable_lab_reminders BOOLEAN NOT NULL DEFAULT TRUE,
    enable_exam_alerts BOOLEAN NOT NULL DEFAULT TRUE,
    per_type JSONB NOT NULL DEFAULT '{}'::jsonb,
    quiet_start TIME,
    quiet_end TIME
);

CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    recipient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    data_payload JSONB DEFAULT '{}'::jsonb,
    -- Legacy schedule reference. New occurrence-level deduplication lives
    -- in notification_log; the new scanner leaves this column NULL.
    class_session_id UUID REFERENCES class_schedules(id) ON DELETE CASCADE,
    notified_at TIMESTAMPTZ,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_notification_class_session UNIQUE (recipient_id, class_session_id)
);
CREATE INDEX ix_notifications_recipient_read ON notifications (recipient_id, is_read);

CREATE TABLE device_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    platform VARCHAR(20) NOT NULL DEFAULT 'web',
    last_seen TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_device_tokens_user_id ON device_tokens (user_id);

CREATE TABLE notification_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(40) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    due_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_notification_batches_pending_due ON notification_batches (due_at)
    WHERE status = 'pending';

CREATE TABLE notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id UUID NOT NULL,
    type VARCHAR(40) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    notification_id BIGINT REFERENCES notifications(id) ON DELETE SET NULL,
    batch_id UUID REFERENCES notification_batches(id) ON DELETE SET NULL,
    due_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_notification_log_event UNIQUE (user_id, event_id, type),
    CONSTRAINT ck_notification_log_priority CHECK (priority IN ('high', 'medium', 'low'))
);
CREATE INDEX ix_notification_log_pending ON notification_log (user_id, type, due_at)
    WHERE status = 'pending';

CREATE TABLE notification_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL REFERENCES notification_batches(id) ON DELETE CASCADE,
    device_id UUID REFERENCES device_tokens(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INT NOT NULL DEFAULT 0,
    attempted_at TIMESTAMPTZ,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_error VARCHAR(40),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_notification_delivery_device UNIQUE (batch_id, device_id)
);
CREATE INDEX ix_notification_deliveries_retry
    ON notification_deliveries (batch_id, status, next_attempt_at);

-- 5. Resources & Books
CREATE TABLE academic_resources (
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

CREATE TABLE book_exchanges (
    resource_id UUID PRIMARY KEY REFERENCES academic_resources(id) ON DELETE CASCADE,
    author VARCHAR(200) NOT NULL,
    edition VARCHAR(50),
    transaction_type exchange_listing_type NOT NULL DEFAULT 'lend',
    price_bdt NUMERIC(10, 2) DEFAULT 0.00,
    status exchange_status NOT NULL DEFAULT 'available',
    is_available BOOLEAN NOT NULL DEFAULT TRUE
);

-- 6. Labs
CREATE TABLE equipment_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL,
    total_quantity INT NOT NULL DEFAULT 1,
    available_quantity INT NOT NULL DEFAULT 1
);

CREATE TABLE equipment_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id INT NOT NULL REFERENCES equipment_models(id) ON DELETE RESTRICT,
    asset_tag VARCHAR(50) NOT NULL UNIQUE,
    lab_name VARCHAR(100) NOT NULL,
    condition lab_condition NOT NULL DEFAULT 'operational',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE equipment_borrow_requests (
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

CREATE TABLE damage_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES equipment_assets(id) ON DELETE RESTRICT,
    reported_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    description TEXT NOT NULL,
    repair_cost_bdt NUMERIC(10, 2) DEFAULT 0.00,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lab_bench_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lab_name VARCHAR(100) NOT NULL,
    bench_number INT NOT NULL,
    reserved_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    slot_range TSTZRANGE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'approved'
);

-- 7. Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    abstract TEXT NOT NULL,
    tier VARCHAR(50) NOT NULL DEFAULT 'capstone_thesis',
    semester_id INT NOT NULL REFERENCES semesters(id) ON DELETE RESTRICT,
    supervisor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    github_repo_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE project_members (
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(30) NOT NULL DEFAULT 'member',
    PRIMARY KEY (project_id, student_id)
);

CREATE TABLE supervisor_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    faculty_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    proposal_text TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE project_publications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    conference_name VARCHAR(200),
    doi_url VARCHAR(255),
    paper_file_key VARCHAR(512) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. Career
CREATE TABLE career_opportunities (
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

CREATE TABLE student_cv_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    headline VARCHAR(200),
    summary TEXT,
    education JSONB DEFAULT '[]'::jsonb,
    skills JSONB DEFAULT '{}'::jsonb,
    experience JSONB DEFAULT '[]'::jsonb
);

CREATE TABLE student_portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    slug VARCHAR(60) NOT NULL UNIQUE,
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    view_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 9. AI Knowledge
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(768),
    embedding_model VARCHAR(100),
    page_number INTEGER,
    section VARCHAR(255),
    tsv_content TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_document_chunk_page CHECK (page_number IS NULL OR page_number > 0)
);
CREATE INDEX ix_document_chunks_tsv ON document_chunks USING GIN (tsv_content);
CREATE INDEX ix_document_chunks_document ON document_chunks (document_id);
CREATE INDEX ix_knowledge_documents_course ON knowledge_documents (course_id);

CREATE TABLE ai_chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_title VARCHAR(150) NOT NULL DEFAULT 'Course Q&A',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES ai_chat_sessions(id) ON DELETE CASCADE,
    sender VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_generated_study_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE course_offering_teachers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_offering_id UUID NOT NULL REFERENCES course_offerings(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'course_teacher',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(course_offering_id, teacher_id)
);

-- 10. Alumni Portal (public landing + authenticated members' area)
CREATE TABLE alumni_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    batch_year INT NOT NULL,
    department VARCHAR(100) NOT NULL,
    graduation_date DATE NOT NULL,
    current_company VARCHAR(150),
    designation VARCHAR(150),
    industry VARCHAR(100),
    linkedin_url VARCHAR(255),
    verified_by_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    membership_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    is_visible BOOLEAN NOT NULL DEFAULT FALSE,
    current_city VARCHAR(120),
    current_country VARCHAR(120),
    bio VARCHAR(2000),
    phone VARCHAR(30),
    email_visible BOOLEAN NOT NULL DEFAULT FALSE,
    phone_visible BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    search_tsv TSVECTOR GENERATED ALWAYS AS (
        to_tsvector(
            'english',
            coalesce(department, '') || ' ' ||
            coalesce(current_company, '') || ' ' ||
            coalesce(industry, '') || ' ' ||
            coalesce(designation, '') || ' ' ||
            coalesce(batch_year::text, '')
        )
    ) STORED,
    CONSTRAINT uq_alumni_profiles_user UNIQUE (user_id),
    CONSTRAINT ck_alumni_profiles_batch_year CHECK (batch_year >= 2010),
    CONSTRAINT ck_alumni_profiles_membership
        CHECK (membership_status IN ('pending', 'active', 'expired', 'rejected'))
);
CREATE INDEX ix_alumni_profiles_user_id ON alumni_profiles (user_id);
CREATE INDEX ix_alumni_profiles_batch_year ON alumni_profiles (batch_year);
CREATE INDEX ix_alumni_profiles_industry ON alumni_profiles (industry);
CREATE INDEX ix_alumni_profiles_membership_status ON alumni_profiles (membership_status);
CREATE INDEX ix_alumni_profiles_is_visible ON alumni_profiles (is_visible);
CREATE INDEX ix_alumni_profiles_batch_industry ON alumni_profiles (batch_year, industry);
CREATE INDEX ix_alumni_profiles_search ON alumni_profiles USING GIN (search_tsv);
CREATE INDEX ix_alumni_profiles_current_country ON alumni_profiles (current_country);
CREATE INDEX ix_alumni_profiles_is_verified ON alumni_profiles (is_verified);
CREATE INDEX ix_users_full_name_trgm ON users USING GIN (full_name gin_trgm_ops);

CREATE TABLE alumni_employments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alumni_id UUID NOT NULL REFERENCES alumni_profiles(id) ON DELETE CASCADE,
    organization VARCHAR(255) NOT NULL,
    position VARCHAR(255) NOT NULL,
    sector VARCHAR(30) NOT NULL DEFAULT 'other',
    city VARCHAR(120),
    country VARCHAR(120),
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_alumni_employments_sector CHECK (sector IN ('industry', 'academia', 'government', 'startup', 'higher_study', 'other')),
    CONSTRAINT ck_alumni_employments_dates CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);
CREATE INDEX ix_alumni_employments_alumni ON alumni_employments (alumni_id);
CREATE INDEX ix_alumni_employments_country_sector ON alumni_employments (country, sector);
CREATE INDEX ix_alumni_employments_organization_trgm ON alumni_employments USING GIN (organization gin_trgm_ops);
CREATE UNIQUE INDEX uq_alumni_employments_one_current ON alumni_employments (alumni_id) WHERE is_current;

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by UUID NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    description VARCHAR(2000) NOT NULL,
    venue VARCHAR(200) NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    cover_photo_key VARCHAR(512),
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    members_only BOOLEAN NOT NULL DEFAULT FALSE,
    event_type VARCHAR(20) NOT NULL DEFAULT 'meetup',
    -- NULL capacity == unlimited; otherwise attending RSVPs claim a seat.
    capacity INT,
    -- Set by the Celery Beat announcer when a published event's FCM
    -- broadcast goes out; keeps the minute-scanner idempotent.
    announced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_events_starts_at ON events (starts_at);
CREATE INDEX ix_events_is_published ON events (is_published);
CREATE INDEX ix_events_event_type ON events (event_type);

CREATE TABLE event_rsvps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rsvp_status VARCHAR(20) NOT NULL DEFAULT 'attending',
    note VARCHAR(500),
    -- Each attending RSVP claims a disjoint [seat, seat] point range so the
    -- DB rejects overbooking even under concurrent requests. Non-attending
    -- rows keep a NULL slot and never consume capacity.
    slot_range INT4RANGE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_event_rsvps_event_user UNIQUE (event_id, user_id),
    CONSTRAINT ck_event_rsvps_status
        CHECK (rsvp_status IN ('attending', 'interested', 'not_attending')),
    CONSTRAINT no_double_booked_event_seats EXCLUDE USING gist (
        event_id WITH =,
        slot_range WITH &&
    ) WHERE (rsvp_status = 'attending')
);

CREATE TABLE scholarships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by UUID NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    description VARCHAR(2000) NOT NULL,
    eligibility VARCHAR(1000) NOT NULL,
    amount_bdt INT,
    deadline DATE NOT NULL,
    application_target VARCHAR(255) NOT NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_scholarships_deadline ON scholarships (deadline);
CREATE INDEX ix_scholarships_is_published ON scholarships (is_published);

CREATE TABLE scholarship_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_id UUID NOT NULL REFERENCES scholarships(id) ON DELETE CASCADE,
    applicant_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    motivation VARCHAR(2000) NOT NULL,
    document_key VARCHAR(512),
    document_name VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'submitted',
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_scholarship_applications UNIQUE (scholarship_id, applicant_id),
    CONSTRAINT ck_scholarship_applications_status
        CHECK (status IN ('submitted', 'under_review', 'approved', 'rejected'))
);

CREATE TABLE mentorship_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mentor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mentee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'requested',
    requested_by UUID NOT NULL REFERENCES users(id),
    mentee_note VARCHAR(1000),
    mentor_note VARCHAR(1000),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_mentorship_pairs UNIQUE (mentor_id, mentee_id),
    CONSTRAINT ck_mentorship_pairs_status
        CHECK (status IN ('requested', 'active', 'ended', 'declined')),
    CONSTRAINT ck_mentorship_pairs_not_self
        CHECK (mentor_id <> mentee_id)
);
CREATE INDEX ix_mentorship_pairs_mentee ON mentorship_pairs (mentee_id, status);

CREATE TABLE news_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(220) NOT NULL UNIQUE,
    body VARCHAR(20000) NOT NULL,
    cover_photo_key VARCHAR(512),
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_news_posts_slug ON news_posts (slug);
CREATE INDEX ix_news_posts_is_published ON news_posts (is_published);

CREATE TABLE gallery_albums (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description VARCHAR(1000),
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,
    cover_photo_key VARCHAR(512),
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE gallery_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    album_id UUID NOT NULL REFERENCES gallery_albums(id) ON DELETE CASCADE,
    photo_key VARCHAR(512) NOT NULL,
    caption VARCHAR(500),
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
