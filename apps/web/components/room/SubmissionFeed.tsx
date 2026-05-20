import { Submission, GenerationJob, Participant } from "@/types";
import { SubmissionCard } from "./SubmissionCard";

export function SubmissionFeed({
  submissions,
  jobs,
  participants,
  currentUserId
}: {
  submissions: Submission[];
  jobs: Record<string, GenerationJob>;
  participants: Participant[];
  currentUserId: string;
}) {
  if (submissions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-zinc-500 border border-dashed border-zinc-800 rounded-xl bg-zinc-900/30">
        <p>No submissions yet for this round.</p>
        <p className="text-sm mt-1">Be the first to submit!</p>
      </div>
    );
  }

  // Find the job for a submission if it isn't nested inside (from WS)
  const getJobForSubmission = (sub: Submission) => {
    // If from REST API, it might be nested
    if (sub.generation_job) return sub.generation_job;
    // Otherwise look in jobs record by submission id (inefficient but fine for small n)
    return Object.values(jobs).find(j => j.submission_id === sub.id);
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-zinc-100 mb-4">Live Submissions</h3>
      {submissions.map((sub) => {
        const participant = participants.find((p) => p.id === sub.participant_id);
        const job = getJobForSubmission(sub);
        const isCurrentUser = participant?.user_id === currentUserId;
        
        return (
          <SubmissionCard 
            key={sub.id} 
            submission={sub} 
            job={job} 
            participant={participant}
            isCurrentUser={isCurrentUser}
          />
        );
      })}
    </div>
  );
}
