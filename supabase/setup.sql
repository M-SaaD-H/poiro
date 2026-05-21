-- =============================================================================
-- Poiro — Supabase SQL Setup Script
-- Run this in: Supabase Dashboard → SQL Editor → New Query
--
-- Sections:
--   1. Enums
--   2. Tables  (full schema)
--   3. Migration patch  (max_rounds column — safe to run even if already exists)
--   4. Test users seed  (public.users only — auth accounts must be created first)
-- =============================================================================


-- ─────────────────────────────────────────────────────────────────────────────
-- 1. ENUMS
-- ─────────────────────────────────────────────────────────────────────────────

DO $$ BEGIN
  CREATE TYPE roomstatus AS ENUM ('waiting', 'active', 'completed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE roundstatus AS ENUM ('pending', 'active', 'scoring', 'completed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE jobstatus AS ENUM ('queued', 'running', 'completed', 'failed', 'timed_out');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. TABLES
-- ─────────────────────────────────────────────────────────────────────────────

-- users: mirrors auth.users identity; id must match auth.users.id
CREATE TABLE IF NOT EXISTS public.users (
  id           UUID        PRIMARY KEY,  -- must equal auth.users.id
  email        TEXT        NOT NULL UNIQUE,
  display_name TEXT        NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- rooms
CREATE TABLE IF NOT EXISTS public.rooms (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  code             TEXT        NOT NULL UNIQUE,
  title            TEXT        NOT NULL,
  challenge_prompt TEXT        NOT NULL,
  host_id          UUID        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  status           roomstatus  NOT NULL DEFAULT 'waiting',
  max_rounds       INTEGER     NOT NULL DEFAULT 3,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rooms_code ON public.rooms(code);

-- participants
CREATE TABLE IF NOT EXISTS public.participants (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  room_id      UUID        NOT NULL REFERENCES public.rooms(id) ON DELETE CASCADE,
  user_id      UUID        NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  joined_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  is_eliminated BOOLEAN    NOT NULL DEFAULT FALSE,
  CONSTRAINT uq_participant_room_user UNIQUE (room_id, user_id)
);

-- rounds
CREATE TABLE IF NOT EXISTS public.rounds (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  room_id      UUID        NOT NULL REFERENCES public.rooms(id) ON DELETE CASCADE,
  round_number INTEGER     NOT NULL,
  status       roundstatus NOT NULL DEFAULT 'pending',
  started_at   TIMESTAMPTZ,
  ended_at     TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- submissions
CREATE TABLE IF NOT EXISTS public.submissions (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  round_id         UUID        NOT NULL REFERENCES public.rounds(id) ON DELETE CASCADE,
  participant_id   UUID        NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
  prompt           TEXT        NOT NULL,
  generated_output TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_submission_round_participant UNIQUE (round_id, participant_id)
);

-- generation_jobs
CREATE TABLE IF NOT EXISTS public.generation_jobs (
  id             UUID      PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id  UUID      NOT NULL UNIQUE REFERENCES public.submissions(id) ON DELETE CASCADE,
  status         jobstatus NOT NULL DEFAULT 'queued',
  error_message  TEXT,
  enqueued_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at     TIMESTAMPTZ,
  completed_at   TIMESTAMPTZ,
  retry_count    INTEGER   NOT NULL DEFAULT 0
);

-- scores
CREATE TABLE IF NOT EXISTS public.scores (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  round_id       UUID        NOT NULL REFERENCES public.rounds(id) ON DELETE CASCADE,
  participant_id UUID        NOT NULL REFERENCES public.participants(id) ON DELETE CASCADE,
  submission_id  UUID        NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
  points         INTEGER     NOT NULL,
  is_eliminated  BOOLEAN     NOT NULL DEFAULT FALSE,
  scored_by      UUID        REFERENCES public.users(id) ON DELETE SET NULL,
  scored_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. MIGRATION PATCH  (add max_rounds if this is an older schema)
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.rooms
  ADD COLUMN IF NOT EXISTS max_rounds INTEGER NOT NULL DEFAULT 3;


-- ─────────────────────────────────────────────────────────────────────────────
-- 4. TEST USERS SEED
--
-- IMPORTANT: You must create the auth accounts FIRST via:
--   Supabase Dashboard → Authentication → Users → Add user → Create new user
--
--   host@example.com   / Poiro@host1
--   alice@example.com  / Poiro@alice1
--   bob@example.com    / Poiro@bob1
--   carol@example.com  / Poiro@carol1
--
-- Then replace the UUIDs below with the actual UUIDs from Authentication → Users.
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO public.users (id, email, display_name) VALUES
  ('f926a2f5-ce16-4d2c-a7e7-c5afb869d561', 'host@example.com',  'Battle Host'),
  ('4b7fdffb-409d-4c31-a8a7-c38d05459a71', 'alice@example.com', 'Alice'),
  ('5e37660a-a90b-46a2-8f40-87663205a952', 'bob@example.com',   'Bob'),
  ('079ed56c-3e36-49f8-9c08-deb4f25c390d', 'carol@example.com', 'Carol')
ON CONFLICT (id) DO UPDATE
  SET display_name = EXCLUDED.display_name,
      email        = EXCLUDED.email;

-- =============================================================================
-- Done! Verify with:
--   SELECT * FROM public.users;
--   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- =============================================================================
