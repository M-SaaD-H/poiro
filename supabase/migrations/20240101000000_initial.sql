-- =============================================================================
-- Poiro — initial schema migration
-- Apply via: supabase db push  (or supabase migration up)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- Enum types
-- ---------------------------------------------------------------------------
CREATE TYPE public.roomstatus AS ENUM ('waiting', 'active', 'completed');
CREATE TYPE public.roundstatus AS ENUM ('pending', 'active', 'scoring', 'completed');
CREATE TYPE public.jobstatus   AS ENUM ('queued', 'running', 'completed', 'failed', 'timed_out');

-- ---------------------------------------------------------------------------
-- public.users  (profile mirror of auth.users)
-- The id FK into auth.users ensures the row is automatically removed when the
-- Supabase Auth user is deleted.
-- ---------------------------------------------------------------------------
CREATE TABLE public.users (
    id           UUID        PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    email        TEXT        NOT NULL UNIQUE,
    display_name TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- public.rooms
-- ---------------------------------------------------------------------------
CREATE TABLE public.rooms (
    id               UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    code             CHAR(6)      NOT NULL UNIQUE,
    title            VARCHAR(200) NOT NULL,
    challenge_prompt TEXT         NOT NULL,
    host_id          UUID         NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    status           public.roomstatus NOT NULL DEFAULT 'waiting',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rooms_code   ON public.rooms (code);
CREATE INDEX idx_rooms_host   ON public.rooms (host_id);
CREATE INDEX idx_rooms_status ON public.rooms (status);

-- ---------------------------------------------------------------------------
-- public.participants
-- ---------------------------------------------------------------------------
CREATE TABLE public.participants (
    id             UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    room_id        UUID        NOT NULL REFERENCES public.rooms (id) ON DELETE CASCADE,
    user_id        UUID        NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    joined_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_eliminated  BOOLEAN     NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_participant_room_user UNIQUE (room_id, user_id)
);

CREATE INDEX idx_participants_room ON public.participants (room_id);
CREATE INDEX idx_participants_user ON public.participants (user_id);

-- ---------------------------------------------------------------------------
-- public.rounds
-- ---------------------------------------------------------------------------
CREATE TABLE public.rounds (
    id           UUID              PRIMARY KEY DEFAULT uuid_generate_v4(),
    room_id      UUID              NOT NULL REFERENCES public.rooms (id) ON DELETE CASCADE,
    round_number INTEGER           NOT NULL,
    status       public.roundstatus NOT NULL DEFAULT 'pending',
    started_at   TIMESTAMPTZ,
    ended_at     TIMESTAMPTZ,
    created_at   TIMESTAMPTZ       NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rounds_room   ON public.rounds (room_id);
CREATE INDEX idx_rounds_status ON public.rounds (status);

-- ---------------------------------------------------------------------------
-- public.submissions
-- ---------------------------------------------------------------------------
CREATE TABLE public.submissions (
    id               UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    round_id         UUID        NOT NULL REFERENCES public.rounds (id) ON DELETE CASCADE,
    participant_id   UUID        NOT NULL REFERENCES public.participants (id) ON DELETE CASCADE,
    prompt           TEXT        NOT NULL,
    generated_output TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_submission_round_participant UNIQUE (round_id, participant_id)
);

CREATE INDEX idx_submissions_round       ON public.submissions (round_id);
CREATE INDEX idx_submissions_participant ON public.submissions (participant_id);

-- ---------------------------------------------------------------------------
-- public.generation_jobs
-- ---------------------------------------------------------------------------
CREATE TABLE public.generation_jobs (
    id            UUID              PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID              NOT NULL UNIQUE REFERENCES public.submissions (id) ON DELETE CASCADE,
    status        public.jobstatus  NOT NULL DEFAULT 'queued',
    error_message VARCHAR(2000),
    enqueued_at   TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    retry_count   INTEGER           NOT NULL DEFAULT 0
);

CREATE INDEX idx_generation_jobs_status ON public.generation_jobs (status);

-- ---------------------------------------------------------------------------
-- public.scores
-- ---------------------------------------------------------------------------
CREATE TABLE public.scores (
    id             UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    round_id       UUID        NOT NULL REFERENCES public.rounds (id) ON DELETE CASCADE,
    participant_id UUID        NOT NULL REFERENCES public.participants (id) ON DELETE CASCADE,
    submission_id  UUID        NOT NULL REFERENCES public.submissions (id) ON DELETE CASCADE,
    points         INTEGER     NOT NULL,
    is_eliminated  BOOLEAN     NOT NULL DEFAULT FALSE,
    scored_by      UUID        REFERENCES public.users (id) ON DELETE SET NULL,
    scored_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scores_round       ON public.scores (round_id);
CREATE INDEX idx_scores_participant ON public.scores (participant_id);

-- ---------------------------------------------------------------------------
-- Row Level Security (RLS)
-- Enable RLS on all tables. Policies can be refined per business rules.
-- ---------------------------------------------------------------------------
ALTER TABLE public.users           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rooms           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.participants    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rounds          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scores          ENABLE ROW LEVEL SECURITY;

-- Allow the service role (used by the API server) full access to all tables.
-- The API enforces its own business-logic access control via FastAPI dependencies.
CREATE POLICY "service_role_all" ON public.users           FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON public.rooms           FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON public.participants    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON public.rounds          FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON public.submissions     FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON public.generation_jobs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON public.scores          FOR ALL TO service_role USING (true) WITH CHECK (true);
