import { create } from "zustand";
import { RoomSnapshot, WSEvent, Room, Participant, Round, Submission, GenerationJob } from "@/types";

interface RoomState {
  room: Room | null;
  activeRound: Round | null;
  participants: Participant[];
  submissions: Submission[];
  jobs: Record<string, GenerationJob>;
  connected: boolean;

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
  connected: false,

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
        return { activeRound: newRound, submissions: [], jobs: {} };
      }

      case "round:ended": {
        if (!state.activeRound || state.activeRound.id !== event.data.round_id) return state;
        const updatedRound: Round = { ...state.activeRound, status: "scoring", ended_at: new Date().toISOString() };
        return { activeRound: updatedRound };
      }

      case "participant:joined": {
        return {
          participants: [...state.participants, event.data],
          room: state.room ? { ...state.room, status: "active" } : state.room,
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
        const updatedJob: GenerationJob = {
          ...existing,
          status: "running",
          started_at: new Date().toISOString(),
        };
        return {
          jobs: { ...state.jobs, [event.data.job_id]: updatedJob }
        };
      }

      case "job:completed": {
        const existing = state.jobs[event.data.job_id];
        if (!existing) return state;
        const updatedJob: GenerationJob = {
          ...existing,
          status: "completed",
          completed_at: new Date().toISOString(),
        };
        return {
          jobs: { ...state.jobs, [event.data.job_id]: updatedJob },
          submissions: state.submissions.map(sub =>
            sub.id === event.data.submission_id ? { ...sub, generated_output: event.data.output } : sub
          )
        };
      }

      case "job:failed": {
        const existing = state.jobs[event.data.job_id];
        if (!existing) return state;
        const updatedJob: GenerationJob = {
          ...existing,
          status: "failed",
          error_message: event.data.error_message,
          completed_at: new Date().toISOString(),
        };
        return {
          jobs: { ...state.jobs, [event.data.job_id]: updatedJob }
        };
      }

      case "job:timed_out": {
        const existing = state.jobs[event.data.job_id];
        if (!existing) return state;
        const updatedJob: GenerationJob = {
          ...existing,
          status: "timed_out",
          completed_at: new Date().toISOString(),
        };
        return {
          jobs: { ...state.jobs, [event.data.job_id]: updatedJob }
        };
      }

      case "score:submitted": {
        if (event.data.is_eliminated) {
          return {
            participants: state.participants.map(p =>
              p.id === event.data.participant_id ? { ...p, is_eliminated: true } : p
            )
          };
        }
        return state;
      }

      case "room:completed": {
        return {
          room: state.room ? { ...state.room, status: "completed" } : state.room,
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
    connected: false,
  })
}));
