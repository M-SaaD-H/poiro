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
      case "room:state":
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

      case "round:started":
        if (!state.room) return state;
        return {
          activeRound: {
            id: event.data.round_id,
            room_id: state.room.id,
            round_number: event.data.round_number,
            status: "active",
            started_at: new Date().toISOString(),
            ended_at: null,
            created_at: new Date().toISOString(),
          }
        };

      case "round:ended":
        if (!state.activeRound || state.activeRound.id !== event.data.round_id) return state;
        return {
          activeRound: { ...state.activeRound, status: "scoring", ended_at: new Date().toISOString() }
        };

      case "participant:joined":
        return {
          participants: [...state.participants, event.data]
        };

      case "participant:eliminated":
        return {
          participants: state.participants.map(p => 
            p.id === event.data.participant_id ? { ...p, is_eliminated: true } : p
          )
        };

      case "submission:created":
        // We only get the IDs here, full submission is fetched via REST or we wait for job
        // Typically, we might optimistic update, but let's just add a shell
        const newSubmission: Submission = {
          id: event.data.submission_id,
          round_id: state.activeRound?.id || "",
          participant_id: event.data.participant_id,
          prompt: "...", // Loading state prompt
          generated_output: null,
          created_at: new Date().toISOString(),
        };
        return {
          submissions: [...state.submissions, newSubmission]
        };

      case "job:queued":
        return {
          jobs: {
            ...state.jobs,
            [event.data.job_id]: {
              id: event.data.job_id,
              submission_id: event.data.submission_id,
              status: "queued",
              error_message: null,
              enqueued_at: new Date().toISOString(),
              started_at: null,
              completed_at: null,
              retry_count: 0,
            }
          }
        };

      case "job:running":
        return {
          jobs: {
            ...state.jobs,
            [event.data.job_id]: {
              ...state.jobs[event.data.job_id],
              status: "running",
              started_at: new Date().toISOString(),
            }
          }
        };

      case "job:completed":
        // Also update the submission output
        return {
          jobs: {
            ...state.jobs,
            [event.data.job_id]: {
              ...state.jobs[event.data.job_id],
              status: "completed",
              completed_at: new Date().toISOString(),
            }
          },
          submissions: state.submissions.map(sub => 
            sub.id === event.data.submission_id ? { ...sub, generated_output: event.data.output } : sub
          )
        };

      case "job:failed":
        return {
          jobs: {
            ...state.jobs,
            [event.data.job_id]: {
              ...state.jobs[event.data.job_id],
              status: "failed",
              error_message: event.data.error_message,
              completed_at: new Date().toISOString(),
            }
          }
        };

      case "job:timed_out":
        return {
          jobs: {
            ...state.jobs,
            [event.data.job_id]: {
              ...state.jobs[event.data.job_id],
              status: "timed_out",
              completed_at: new Date().toISOString(),
            }
          }
        };
        
      case "score:submitted":
        if (event.data.is_eliminated) {
           return {
             participants: state.participants.map(p => 
               p.id === event.data.participant_id ? { ...p, is_eliminated: true } : p
             )
           };
        }
        return state;

      default:
        return state;
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
