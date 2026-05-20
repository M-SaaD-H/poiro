# Poiro – AI Creative Battle Room

Poiro is a real-time, minimal multiplayer web platform where a host runs creative prompt challenges and participants compete by submitting AI-generated outputs. The system is stateful, responsive, and uses WebSockets for live updates.

## 1. Local Setup

### Prerequisites
- [Node.js](https://nodejs.org/) (≥ 20) and [Bun](https://bun.sh/)
- [Python](https://www.python.org/) (≥ 3.11)
- [Redis](https://redis.io/) (Running locally or via Docker)
- PostgreSQL (or Supabase local instance)

### Installation

1. **Clone & Install Dependencies**
   ```bash
   git clone <repo-url>
   cd poiro
   bun install
   ```

2. **Environment Variables**
   ```bash
   cp .env.example .env
   cp apps/api/.env.example apps/api/.env
   cp apps/web/.env.local.example apps/web/.env.local
   ```
   *Edit `.env` files to match your local database and Redis setup.*

3. **Backend Setup (FastAPI)**
   ```bash
   cd apps/api
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   ```

4. **Start the Services**
   Open three terminal tabs:
   - **FastAPI API Server**: `cd apps/api && uvicorn app.main:app --reload --port 8000`
   - **ARQ Worker (Redis job queue)**: `cd apps/api && arq app.jobs.worker.WorkerSettings`
   - **Next.js Frontend**: `cd apps/web && bun run dev`

Visit `http://localhost:3000` to start playing.

---

## 2. Architecture Overview

Poiro uses a robust decoupled architecture:
- **Frontend**: Next.js 14 App Router, Zustand for state, TanStack Query for REST data, and native WebSockets.
- **Backend**: FastAPI with async SQLAlchemy, communicating with a PostgreSQL database.
- **Job Queue**: ARQ (Redis) handles long-running AI generation jobs asynchronously to prevent blocking the API.
- **Realtime**: FastAPI WebSockets broadcast state changes to clients in real-time.

```text
[ Next.js Client ] <--(REST & WS)--> [ FastAPI Server ] <--(SQL)--> [ PostgreSQL ]
                                           |
                                      (Enqueue)
                                           |
                                           v
[ AI Providers ] <--(Async API)-->   [ ARQ Worker ] <--(Redis)--> [ Redis DB ]
```

---

## 3. Database Schema

- **Users**: `id`, `email`, `hashed_password`, `display_name`
- **Rooms**: `id`, `code`, `title`, `challenge_prompt`, `host_id`, `status`
- **Participants**: `id`, `room_id`, `user_id`, `is_eliminated`, `joined_at`
- **Rounds**: `id`, `room_id`, `round_number`, `status`
- **Submissions**: `id`, `round_id`, `participant_id`, `prompt`, `generated_output`
- **GenerationJobs**: `id`, `submission_id`, `status`, `error_message`, `enqueued_at`, `completed_at`
- **Scores**: `id`, `round_id`, `participant_id`, `submission_id`, `points`, `is_eliminated`, `scored_by`

---

## 4. Realtime Event Model

All WebSocket events follow the `{ "event": "<name>", "data": { ... } }` structure.

| Event | Direction | Purpose |
|---|---|---|
| `room:state` | Server → Client | Full state hydration upon initial connection. |
| `round:started` | Server → Room | Notifies participants a new round has begun. |
| `round:ended` | Server → Room | Notifies participants the round is over; moves to scoring. |
| `participant:joined`| Server → Room | Real-time participant roster updates. |
| `participant:eliminated`| Server → Room| Marks a participant as eliminated across all clients. |
| `submission:created`| Server → Room | Signals a user has locked in their prompt. |
| `job:queued` | Server → Room | AI generation job entered Redis queue. |
| `job:running` | Server → Room | Worker started generating AI response. |
| `job:completed` | Server → Room | Worker finished; delivers final output. |
| `job:failed` / `timed_out`| Server → Room | Generation failed; allows UI to show retry button. |
| `score:submitted` | Server → Room | Host has scored a participant's submission. |

---

## 5. Generation Job Lifecycle

Generation tasks are handled by a finite state machine managed by ARQ:

```text
[ Submission Created ]
          |
          v
      (QUEUED) ---------> (TIMED_OUT) --+
          |                             |
          v                             v
      (RUNNING) --------> (FAILED) <----+
          |                 |
          v                 v
     (COMPLETED)         [ Retry ]
```

---

## 6. Battle Mechanism

**Current Implementation**: Host-assigned points with an elimination flag.
- After a round ends, the host reviews all generated outputs.
- The host awards points (0-100) per participant and can optionally eliminate them.
- Eliminated participants can observe but cannot submit in future rounds.

**Weaknesses**: 
- Highly subjective; reliant entirely on host judgment.
- Susceptible to host bias or favoritism.
- Does not scale well for large rooms (host bottleneck).

**Production Improvements**:
- **Peer Voting**: Participants rank each other's outputs anonymously.
- **AI-Automated Scoring**: Use an LLM with a strict rubric to score outputs objectively based on the original challenge context.
- **Weighted Crowd Score**: Combine host score, peer votes, and AI evaluation.

---

## 7. Persistence

**Persisted (Database)**:
- Users, Rooms, Rounds, Participants, Submissions, Scores, Job histories.
- JWT tokens are strictly validated against user records.

**Ephemeral (Memory/Redis)**:
- WebSocket connection registry (FastAPI memory).
- Active job queue (Redis).
- Client-side live state (Zustand store). If a client refreshes, Zustand is rehydrated via a single REST snapshot call (`/api/rooms/{id}/state`).

---

## 8. Failure Handling

- **Job Failures**: If the AI provider fails or times out (30s limit), the job transitions to `failed` or `timed_out`. The frontend displays a "Retry" button allowing the participant to re-enqueue the job.
- **WS Disconnects**: If the WebSocket drops, the `useWebSocket` hook (or a future auto-reconnect wrapper) handles it. Next.js gracefully falls back to the last known state. Upon manual refresh, the full state is re-fetched.
- **Invalid Prompts**: Validated deeply by Zod on the frontend, and Pydantic on the backend.

---

## 9. Known Limitations

- **Scalability of WebSockets**: The current `ConnectionManager` is in-memory. If deploying multiple FastAPI pods, a Redis Pub/Sub backplane is required to sync WS events across instances.
- **Simple JWT Auth**: Custom JWT implementation is used. Supabase Auth (as initially requested) was swapped for a native FastAPI+SQLite/Postgres JWT flow for simplicity in rapid prototyping, requiring custom Next.js middleware handling via cookies.
- **Single Active Round**: The system assumes strict linear progression. You cannot run multiple rounds concurrently in the same room.

---

## 10. What I'd Improve With More Time

1. **Redis Pub/Sub for WebSockets**: To support multi-pod horizontal scaling.
2. **Robust Reconnection Logic**: Add exponential backoff for WebSocket drops and automatic REST re-sync on reconnect.
3. **Spectator Mode**: Allow non-logged-in users to view rooms via a read-only WebSocket connection.
4. **Enhanced UI Animations**: Add Framer Motion for smoother transitions when jobs complete or participants are eliminated.
5. **Rate Limiting**: Implement strict rate limits on the `/submissions` endpoint to prevent OpenAI API abuse.
