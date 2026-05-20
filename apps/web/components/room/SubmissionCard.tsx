import { Submission, GenerationJob, Participant } from "@/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { JobStatusBadge } from "./JobStatusBadge";
import { Button } from "@/components/ui/button";
import { RotateCcw, Quote } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useState } from "react";

export function SubmissionCard({
  submission,
  job,
  participant,
  isCurrentUser
}: {
  submission: Submission;
  job?: GenerationJob;
  participant?: Participant;
  isCurrentUser: boolean;
}) {
  const [retrying, setRetrying] = useState(false);

  async function handleRetry() {
    if (!job) return;
    setRetrying(true);
    try {
      await api.post(`/jobs/${job.id}/retry`);
      toast.success("Job re-queued successfully");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to retry job");
    } finally {
      setRetrying(false);
    }
  }

  const isFailed = job?.status === "failed" || job?.status === "timed_out";

  return (
    <Card className="bg-zinc-900/50 border-zinc-800 overflow-hidden">
      <CardHeader className="bg-zinc-900 px-4 py-3 border-b border-zinc-800 flex flex-row items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-medium text-sm text-zinc-200">
            {participant?.display_name || "Unknown Participant"}
          </span>
          {job && <JobStatusBadge status={job.status} />}
        </div>
        {isFailed && isCurrentUser && (
          <Button variant="ghost" size="sm" onClick={handleRetry} disabled={retrying} className="h-8 text-zinc-400 hover:text-zinc-100">
            <RotateCcw className={`w-4 h-4 mr-1 ${retrying ? 'animate-spin' : ''}`} />
            Retry
          </Button>
        )}
      </CardHeader>
      <CardContent className="p-4 space-y-4">
        <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800/50">
          <div className="flex items-start gap-2 text-zinc-400 text-sm italic">
            <Quote className="w-4 h-4 flex-shrink-0 mt-0.5 text-zinc-600" />
            <p>{submission.prompt}</p>
          </div>
        </div>
        
        {submission.generated_output && (
          <div className="prose prose-invert prose-sm max-w-none">
            <p className="text-zinc-300 leading-relaxed whitespace-pre-wrap">{submission.generated_output}</p>
          </div>
        )}
        
        {job?.error_message && isFailed && (
          <div className="text-xs text-red-400 bg-red-950/30 p-2 rounded border border-red-900/50">
            Error: {job.error_message}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
