import { Room, Round } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Users, Hash } from "lucide-react";

export function RoomHeader({ room, activeRound, participantCount }: { room: Room, activeRound: Round | null, participantCount: number }) {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between bg-zinc-900 border border-zinc-800 p-6 rounded-xl shadow-sm gap-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-zinc-50">{room.title}</h1>
        <p className="text-zinc-400 text-sm">Host Context: <span className="text-zinc-300 font-medium">{room.challenge_prompt}</span></p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Badge variant="outline" className="border-zinc-700 bg-zinc-800/50 text-zinc-300 px-3 py-1 text-sm font-medium">
          <Hash className="w-3 h-3 mr-1 inline" /> {room.code}
        </Badge>
        <Badge variant="outline" className="border-zinc-700 bg-zinc-800/50 text-zinc-300 px-3 py-1 text-sm font-medium">
          <Users className="w-3 h-3 mr-1 inline" /> {participantCount}
        </Badge>
        {activeRound ? (
          <Badge className="bg-indigo-500 hover:bg-indigo-600 text-white px-3 py-1 text-sm font-medium border-0">
            Round {activeRound.round_number}
          </Badge>
        ) : (
          <Badge variant="secondary" className="bg-zinc-800 text-zinc-400 px-3 py-1 text-sm font-medium border-0">
            Waiting
          </Badge>
        )}
      </div>
    </div>
  );
}
