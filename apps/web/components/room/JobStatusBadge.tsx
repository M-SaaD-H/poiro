import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";

export function JobStatusBadge({ status }: { status: "queued" | "running" | "completed" | "failed" | "timed_out" }) {
  switch (status) {
    case "queued":
      return (
        <div className="flex items-center text-xs text-zinc-400 bg-zinc-800 px-2 py-1 rounded-md">
          <Clock className="w-3 h-3 mr-1" /> Queued
        </div>
      );
    case "running":
      return (
        <div className="flex items-center text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-1 rounded-md">
          <Loader2 className="w-3 h-3 mr-1 animate-spin" /> Generating...
        </div>
      );
    case "completed":
      return (
        <div className="flex items-center text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-1 rounded-md">
          <CheckCircle2 className="w-3 h-3 mr-1" /> Completed
        </div>
      );
    case "failed":
    case "timed_out":
      return (
        <div className="flex items-center text-xs text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-1 rounded-md">
          <XCircle className="w-3 h-3 mr-1" /> Failed
        </div>
      );
    default:
      return null;
  }
}
