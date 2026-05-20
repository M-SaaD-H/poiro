import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Play, SquareSquare, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { RoomStatus, Round } from "@/types";

export function HostControls({ 
  roomId, 
  roomStatus,
  activeRound 
}: { 
  roomId: string, 
  roomStatus: string,
  activeRound: Round | null 
}) {
  const [isStarting, setIsStarting] = useState(false);
  const [isEnding, setIsEnding] = useState(false);

  async function handleStartRound() {
    setIsStarting(true);
    try {
      await api.post(`/rooms/${roomId}/rounds/start`);
      toast.success("Round started!");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to start round");
    } finally {
      setIsStarting(false);
    }
  }

  async function handleEndRound() {
    if (!activeRound) return;
    setIsEnding(true);
    try {
      await api.post(`/rounds/${activeRound.id}/end`);
      toast.success("Round ended. Proceed to scoring.");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to end round");
    } finally {
      setIsEnding(false);
    }
  }

  const isRoomActive = roomStatus === "active";
  const hasActiveRound = activeRound?.status === "active";
  const hasScoringRound = activeRound?.status === "scoring";

  return (
    <Card className="bg-zinc-900 border-indigo-500/30 ring-1 ring-indigo-500/20 shadow-lg shadow-indigo-900/10">
      <CardContent className="p-4 flex items-center justify-between">
        <div className="text-zinc-300 font-medium">
          Host Controls
        </div>
        <div className="flex gap-3">
          <Button 
            onClick={handleStartRound}
            disabled={!isRoomActive || hasActiveRound || hasScoringRound || isStarting}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            {isStarting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
            Start Round
          </Button>
          
          <Button 
            onClick={handleEndRound}
            disabled={!hasActiveRound || isEnding}
            variant="destructive"
            className="bg-red-900 hover:bg-red-800 text-white border-red-800"
          >
            {isEnding ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <SquareSquare className="w-4 h-4 mr-2" />}
            End Round
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
