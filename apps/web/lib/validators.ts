import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
export type LoginFormData = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  display_name: z.string().min(2, "Display name must be at least 2 characters").max(50),
});
export type RegisterFormData = z.infer<typeof registerSchema>;

export const createRoomSchema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters").max(100),
  challenge_prompt: z.string().min(10, "Challenge prompt must be at least 10 characters").max(500),
  max_rounds: z.coerce.number().int().min(1, "Must have at least 1 round").max(10, "Max 10 rounds").default(3),
});
export type CreateRoomFormData = z.infer<typeof createRoomSchema>;

export const joinRoomSchema = z.object({
  code: z.string().length(6, "Join code must be exactly 6 characters").toUpperCase(),
});
export type JoinRoomFormData = z.infer<typeof joinRoomSchema>;

export const submitPromptSchema = z.object({
  prompt: z.string().min(5, "Prompt must be at least 5 characters").max(300),
});
export type SubmitPromptFormData = z.infer<typeof submitPromptSchema>;

export const scoreSubmissionSchema = z.object({
  points: z.number().min(0).max(100),
  is_eliminated: z.boolean().default(false),
});
export type ScoreSubmissionFormData = z.infer<typeof scoreSubmissionSchema>;
