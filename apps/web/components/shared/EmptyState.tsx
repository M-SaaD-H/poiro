import { FolderOpen } from "lucide-react";

export function EmptyState({ message = "No data available." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-zinc-900/50 border border-dashed border-zinc-800 rounded-xl">
      <FolderOpen className="w-10 h-10 text-zinc-600 mb-3" />
      <p className="text-zinc-400">{message}</p>
    </div>
  );
}
