export interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export interface Room {
  id: string;
  code: string;
  title: string;
  challenge_prompt: string;
  host_id: string;
  status: "waiting" | "active" | "completed";
  created_at: string;
}

export interface Participant {
  id: string;
  room_id: string;
  user_id: string;
  display_name: string;
  joined_at: string;
  is_eliminated: boolean;
}

export interface Round {
  id: string;
  room_id: string;
  round_number: number;
  status: "pending" | "active" | "scoring" | "completed";
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface GenerationJob {
  id: string;
  submission_id: string;
  status: "queued" | "running" | "completed" | "failed" | "timed_out";
  error_message: string | null;
  enqueued_at: string;
  started_at: string | null;
  completed_at: string | null;
  retry_count: number;
}

export interface Submission {
  id: string;
  round_id: string;
  participant_id: string;
  prompt: string;
  generated_output: string | null;
  created_at: string;
  generation_job?: GenerationJob | null;
}

export interface Score {
  id: string;
  round_id: string;
  participant_id: string;
  submission_id: string;
  points: number;
  is_eliminated: boolean;
  scored_by: string;
  scored_at: string;
}

export interface RoomSnapshot {
  room: Room;
  participants: Participant[];
  active_round: Round | null;
  submissions: Submission[];
  jobs: GenerationJob[];
}

// WebSocket Events
export type WSEvent =
  | { event: "room:state"; data: RoomSnapshot }
  | { event: "round:started"; data: { round_id: string; round_number: number } }
  | { event: "round:ended"; data: { round_id: string } }
  | { event: "participant:joined"; data: Participant }
  | { event: "participant:eliminated"; data: { participant_id: string } }
  | { event: "submission:created"; data: { submission_id: string; participant_id: string } }
  | { event: "job:queued"; data: { job_id: string; submission_id: string } }
  | { event: "job:running"; data: { job_id: string } }
  | { event: "job:completed"; data: { job_id: string; submission_id: string; output: string } }
  | { event: "job:failed"; data: { job_id: string; error_message: string } }
  | { event: "job:timed_out"; data: { job_id: string } }
  | { event: "score:submitted"; data: { participant_id: string; points: number; is_eliminated: boolean } };
