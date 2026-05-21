import { create } from "zustand";
import { RoomSnapshot, WSEvent, Room, Participant, Round, Submission, GenerationJob, Score } from "@/types";

interface RoomState {
  room: Room | null;
  activeRound: Round | null;
  participants: Participant[];
  submissions: Submission[];
  jobs: Record<string, GenerationJob>;
  scores: Score[];
  connected: boolean;
  earlyClose: boolean;

  setRoomState: (snapshot: RoomSnapshot) => void;
  applyEvent: (event: WSEvent) => void;
  setConnected: (connected: boolean) => void;
  reset: () => void;
}

export const useRoomStore = create<RoomState>((set) => ({
  room: null,
  activeRound: null,
  participants: [],
  submissions: [],
  jobs: {},
  scores: [],
  connected: false,
  earlyClose: false,

  setConnected: (connected) => set({ connected }),

  setRoomState: (snapshot) => {
    const jobsRecord: Record<string, GenerationJob> = {};
    snapshot.jobs.forEach(job => {
      jobsRecord[job.id] = job;
    });

    set({
      room: snapshot.room,
      activeRound: snapshot.active_round,
      participants: snapshot.participants,
      submissions: snapshot.submissions,
      jobs: jobsRecord,
      scores: [],
    });
  },

  applyEvent: (event) => set((state) => {
    switch (event.event) {
      case "room:state": {
        const jobsRecord: Record<string, GenerationJob> = {};
        event.data.jobs.forEach(job => {
          jobsRecord[job.id] = job;
        });
        return {
          room: event.data.room,
          activeRound: event.data.active_round,
          participants: event.data.participants,
          submissions: event.data.submissions,
          jobs: jobsRecord,
          scores: [],
        };
      }

      case "round:started": {
        if (!state.room) return state;
        const newRound: Round = {
          id: event.data.round_id,
          room_id: state.room.id,
          round_number: event.data.round_number,
          status: "active",
          started_at: new Date().toISOString(),
          ended_at: null,
          created_at: new Date().toISOString(),
        };
        // Clear per-round data when a new round starts
        return { activeRound: newRound, submissions: [], jobs: {}, scores: [] };
      }

      case "round:ended": {
        if (!state.activeRound || state.activeRound.id !== event.data.round_id) return state;
        const updatedRound: Round = { ...state.activeRound, status: "scoring", ended_at: new Date().toISOString() };
        return { activeRound: updatedRound };
      }

      case "participant:joined": {
        // Destructure room_status (sent by backend) out before storing the participant
        const { room_status, ...participant } = event.data;
        const newStatus = room_status ?? state.room?.status;
        return {
          participants: [...state.participants, participant],
          room: state.room ? { ...state.room, status: newStatus ?? state.room.status } : state.room,
        };
      }

      case "participant:left": {
        return {
          participants: state.participants.filter(p => p.id !== event.data.participant_id),
        };
      }

      case "participant:eliminated": {
        return {
          participants: state.participants.map(p =>
            p.id === event.data.participant_id ? { ...p, is_eliminated: true } : p
          )
        };
      }

      case "submission:created": {
        // Guard against duplicate events (e.g. WS reconnect replay)
        if (state.submissions.some(s => s.id === event.data.submission_id)) return state;
        const newSubmission: Submission = {
          id: event.data.submission_id,
          round_id: state.activeRound?.id || "",
          participant_id: event.data.participant_id,
          prompt: event.data.prompt,
          generated_output: null,
          created_at: new Date().toISOString(),
        };
        return {
          submissions: [...state.submissions, newSubmission]
        };
      }

      case "job:queued": {
        const newJob: GenerationJob = {
          id: event.data.job_id,
          submission_id: event.data.submission_id,
          status: "queued",
          error_message: null,
          enqueued_at: new Date().toISOString(),
          started_at: null,
          completed_at: null,
          retry_count: 0,
        };
        return {
          jobs: { ...state.jobs, [event.data.job_id]: newJob }
        };
      }

      case "job:running": {
        const existing = state.jobs[event.data.job_id];
        if (!existing) return state;
        return {
          jobs: {
            ...state.jobs,
            [event.data.job_id]: { ...existing, status: "running", started_at: new Date().toISOString() },
          }
        };
      }

      case "job:completed": {
        const existing = state.jobs[event.data.job_id];
        if (!existing) return state;
        return {
          jobs: {
            ...state.jobs,
            [event.data.job_id]: { ...existing, status: "completed", completed_at: new Date().toISOString() },
          },
          submissions: state.submissions.map(sub =>
            sub.id === event.data.submission_id ? { ...sub, generated_output: event.data.output } : sub
          )
        };
      }

      case "job:failed": {
        const existing = state.jobs[event.data.job_id];
        if (!existing) return state;
        return {
          jobs: {
            ...state.jobs,
            [event.data.job_id]: {
              ...existing,
              status: "failed",
              error_message: event.data.error_message,
              completed_at: new Date().toISOString(),
            },
          }
        };
      }

      case "job:timed_out": {
        const existing = state.jobs[event.data.job_id];
        if (!existing) return state;
        return {
          jobs: {
            ...state.jobs,
            [event.data.job_id]: { ...existing, status: "timed_out", completed_at: new Date().toISOString() },
          }
        };
      }

      case "score:submitted": {
        const { participant_id, points, is_eliminated } = event.data;

        // Accumulate score in the scores slice
        const newScore: Score = {
          id: `${participant_id}-${Date.now()}`, // client-side ephemeral id
          round_id: state.activeRound?.id ?? "",
          participant_id,
          submission_id: "",
          points,
          is_eliminated,
          scored_by: "",
          scored_at: new Date().toISOString(),
        };

        return {
          scores: [...state.scores, newScore],
          // Mark participant as eliminated if the flag is set
          participants: state.participants.map(p =>
            p.id === participant_id && is_eliminated ? { ...p, is_eliminated: true } : p
          ),
        };
      }

      case "room:completed": {
        return {
          room: state.room ? { ...state.room, status: "completed" } : state.room,
          earlyClose: Boolean(event.data.early),
        };
      }

      default: return state;
    }
  }),

  reset: () => set({
    room: null,
    activeRound: null,
    participants: [],
    submissions: [],
    jobs: {},
    scores: [],
    connected: false,
    earlyClose: false,
  })
}));
