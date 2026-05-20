"use client";

import { Room, Round } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Users, Hash, Copy } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { toast } from "sonner";
export function RoomHeader({ room, activeRound, participantCount }: { room: Room, activeRound: Round | null, participantCount: number }) {

  const handleCopy = () => {
    navigator.clipboard.writeText(room.code);
    toast.success("Room code copied!");
  };

  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between bg-zinc-900 border border-zinc-800 p-6 rounded-xl shadow-sm gap-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-zinc-50">{room.title}</h1>
        <p className="text-zinc-400 text-sm">Host Context: <span className="text-zinc-300 font-medium">{room.challenge_prompt}</span></p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge 
                variant="outline" 
                className="border-zinc-700 bg-zinc-800/50 text-zinc-300 px-3 py-1 text-sm font-medium cursor-pointer hover:bg-zinc-700/50 transition-colors"
                onClick={handleCopy}
              >
                <Hash className="w-3 h-3 mr-1 inline" /> {room.code}
              </Badge>
            </TooltipTrigger>
            <TooltipContent className="bg-zinc-800 border-zinc-700 text-zinc-200">
              <div className="flex items-center gap-1.5">
                <Copy className="w-3 h-3 text-zinc-400" /> <span className="font-medium">Click to copy</span>
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
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
