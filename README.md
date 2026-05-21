# Poiro – AI Creative Battle Room

Poiro is a real-time, minimal multiplayer web platform where a host runs creative prompt challenges and participants compete by submitting AI-generated outputs. The system is stateful, responsive, and uses WebSockets for live updates.

## 1. Local Setup

### Prerequisites
- [Node.js](https://nodejs.org/) (≥ 20) and [Bun](https://bun.sh/)
- [Python](https://www.python.org/) (≥ 3.11)
- [Redis](https://redis.io/) (running locally or via Docker)
- A [Supabase](https://supabase.com) project (free tier)

### Installation

1. **Clone & install dependencies**
   ```bash
   git clone <repo-url>
   cd poiro
   bun install
   ```

2. **Environment variables**
   ```bash
   cp .env.example .env
   cp apps/api/.env.example apps/api/.env
   cp apps/web/.env.local.example apps/web/.env.local
   ```
   Edit each file to match your Supabase project and local Redis setup.

3. **Backend Python environment**
   ```bash
   cd apps/api
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Database setup** — run `supabase/setup.sql` in your Supabase SQL Editor (see §3).

5. **Start everything**
   ```bash
   # From the repo root — Turborepo starts API + Next.js together
   bun run dev
   ```
   > The ARQ job worker runs **embedded inside the FastAPI process** — no separate terminal needed.

Visit `http://localhost:3000`.

---

## 2. Architecture Overview

```text
[ Next.js Client ] <--(REST & WS)--> [ FastAPI Server ] <--(SQL)--> [ Supabase Postgres ]
                                           |
                                      (Enqueue)
                                           |
                                           v
[ AI Provider (OpenAI) ] <----------  [ ARQ Worker ]  <--(Redis)--> [ Redis / Upstash ]
```

- **Frontend**: Next.js 14 App Router · Zustand · TanStack Query · native WebSockets
- **Backend**: FastAPI · async SQLAlchemy · Pydantic v2
- **Auth**: Supabase Auth (JWT, ES256 — no custom secret)
- **Job Queue**: ARQ (Redis) — async AI generation, non-blocking
- **Realtime**: FastAPI WebSocket + Redis Pub/Sub backplane

---

## 3. Database Setup (Supabase SQL Editor)

Run **`supabase/setup.sql`** in **Supabase Dashboard → SQL Editor → New Query**.

The script is **idempotent** — safe to run on a fresh or existing project. It:
1. Creates Postgres enums (`roomstatus`, `roundstatus`, `jobstatus`)
2. Creates all tables (`users`, `rooms`, `participants`, `rounds`, `submissions`, `generation_jobs`, `scores`)
3. Applies the `max_rounds` column patch (safe even if the column already exists)
4. Seeds 4 test user profiles (see §11 — you must create auth accounts first)

### Schema summary

| Table | Key columns |
|---|---|
| `users` | `id` (= auth.users.id), `email`, `display_name` |
| `rooms` | `id`, `code`, `title`, `challenge_prompt`, `host_id`, `status`, `max_rounds` |
| `participants` | `id`, `room_id`, `user_id`, `is_eliminated` |
| `rounds` | `id`, `room_id`, `round_number`, `status` |
| `submissions` | `id`, `round_id`, `participant_id`, `prompt`, `generated_output` |
| `generation_jobs` | `id`, `submission_id`, `status`, `retry_count` |
| `scores` | `id`, `round_id`, `participant_id`, `points`, `is_eliminated`, `scored_by` |

---

## 4. Realtime Event Model

All WebSocket events follow `{ "event": "<name>", "data": { ... } }`.

| Event | Direction | Purpose |
|---|---|---|
| `room:state` | Server → Client | Full state hydration on connect / reconnect |
| `round:started` | Server → Room | New round began |
| `round:ended` | Server → Room | Round over; enters scoring phase |
| `participant:joined` | Server → Room | Roster update |
| `participant:eliminated` | Server → Room | Participant marked eliminated |
| `submission:created` | Server → Room | Prompt locked in |
| `job:queued` | Server → Room | AI job enqueued |
| `job:running` | Server → Room | Worker started |
| `job:completed` | Server → Room | AI output ready |
| `job:failed` / `job:timed_out` | Server → Room | Generation failed |
| `score:submitted` | Server → Room | Host scored a submission |
| `room:completed` | Server → Room | Battle ended. `early: true` → force-close (redirect all); `early: false` → all rounds done (show leaderboard) |

---

## 5. Generation Job Lifecycle

```text
[ Submission Created ]
          |
          v
      (QUEUED) --------->  (TIMED_OUT) --+
          |                              |
          v                              v
      (RUNNING) --------> (FAILED) <-----+
          |                  |
          v                  v
     (COMPLETED)          [ Retry ]
```

---

## 6. Battle Flow

1. Host creates a room with a challenge prompt and number of rounds
2. Participants join via the 6-character room code
3. Host clicks **Start Round** → participants submit prompts → AI generates outputs
4. All participants submit → round ends automatically
5. Host scores each submission (0–100 pts, optional elimination)
6. Repeat for each round
7. After the final round, host clicks **End Battle** → leaderboard shown to all
8. Host can also click **Close Battle** (top-right) at any time to force-close early → participants redirected to dashboard

---

## 7. Persistence

**Persisted (Supabase Postgres)**:  
Users, Rooms, Rounds, Participants, Submissions, Scores, Generation job history.

**Ephemeral (memory / Redis)**:  
- WebSocket connection registry (in-process)
- Active job queue (Redis)
- Client Zustand store — rehydrated from `GET /api/rooms/{code}/state` on reconnect

---

## 8. Failure Handling

| Failure | Behaviour |
|---|---|
| AI generation timeout (30 s) | Job → `timed_out`; frontend shows Retry button |
| AI provider error | Job → `failed`; same retry path |
| WebSocket disconnect | `useWebSocket` reconnects with exponential backoff (500 ms → 30 s cap); server resends `room:state` |
| Redis unavailable at startup | API starts in degraded mode — REST endpoints work, realtime and jobs disabled |
| Invalid prompt | Rejected by Zod (frontend) and Pydantic (backend) before hitting the DB |

---

## 9. Known Limitations

- **In-memory WS registry**: horizontal scaling requires migrating to a fully Redis-backed session store (the Pub/Sub backplane is already in place as a foundation)
- **Host-only scoring**: subjective; a future AI-rubric or peer-vote system would remove the bottleneck
- **Single active round per room**: no concurrent round support
- **Stuck job recovery**: jobs stuck in `running` if a worker crashes mid-task require a periodic sweep cronjob

---

## 10. What I'd Improve With More Time

1. **Spectator mode** — read-only WebSocket for non-participants
2. **AI-automated scoring** — LLM rubric removes host subjectivity
3. **Framer Motion animations** — smoother transitions on job completion / elimination
4. **Rate limiting** — strict limits on `/jobs/{id}/retry` to prevent API abuse
5. **Stuck job sweep** — background task to reset orphaned `running` jobs

---

## 11. Test Accounts

Use these to review the full game flow without registering.

| Role | Email | Password |
|---|---|---|
| 🎮 Host | `host@example.com` | `Poiro@host1` |
| 👤 Participant 1 | `alice@example.com` | `Poiro@alice1` |
| 👤 Participant 2 | `bob@example.com` | `Poiro@bob1` |
| 👤 Participant 3 | `carol@example.com` | `Poiro@carol1` |

**Suggested review flow:**
1. Log in as **Host** → Create a room (2 rounds, any challenge prompt)
2. Open 3 browser tabs → log in as **Alice**, **Bob**, **Carol** → join the room using the code
3. Host clicks **Start Round** → each participant submits a prompt → watch AI generation live
4. Host scores each submission → repeat for round 2
5. After round 2 is scored, host clicks **End Battle** → final leaderboard appears for all users
6. *(Optional)* To test force-close: host clicks **Close Battle** (top-right) mid-round → participants see "Battle Ended" popup and are redirected to dashboard

---

## 12. Deployment (Free Tier)

| Component | Provider | Notes |
|---|---|---|
| Next.js frontend | [Vercel](https://vercel.com) | Set root directory to `apps/web` |
| FastAPI API + embedded worker | [Render](https://render.com) | One free web service |
| Postgres + Auth | [Supabase](https://supabase.com) | Free tier |
| Redis | [Upstash](https://upstash.com) | Free — 10K cmd/day; use `rediss://` URL |

