"use client";

import { useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useRoom } from "@/hooks/useRoom";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useRoomStore } from "@/stores/roomStore";
import { useAuth } from "@/hooks/useAuth";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { RoomHeader } from "@/components/room/RoomHeader";
import { ParticipantList } from "@/components/room/ParticipantList";
import { SubmissionFeed } from "@/components/room/SubmissionFeed";
import { SubmitPromptForm } from "@/components/room/SubmitPromptForm";
import { HostControls } from "@/components/room/HostControls";
import { ScoringPanel } from "@/components/room/ScoringPanel";
import { Wifi, WifiOff, Skull } from "lucide-react";

export default function BattleRoomPage() {
  const { code } = useParams<{ code: string }>();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  
  // 1. Fetch initial state via REST
  const { data: initialSnapshot, isLoading: roomLoading, error: roomError } = useRoom(code);
  
  const setRoomState = useRoomStore((state) => state.setRoomState);
  const resetStore = useRoomStore((state) => state.reset);
  
  // Hydrate store when REST data arrives
  useEffect(() => {
    if (initialSnapshot) {
      setRoomState(initialSnapshot);
    }
  }, [initialSnapshot, setRoomState]);

  // Cleanup on unmount
  useEffect(() => {
    return () => resetStore();
  }, [resetStore]);

  // 2. Open WebSocket
  const roomId = initialSnapshot?.room.id;
  useWebSocket(roomId);

  // 3. Subscribe to live Zustand state
  const { room, activeRound, participants, submissions, jobs, connected } = useRoomStore();

  if (authLoading || roomLoading) return <LoadingSpinner />;
  if (roomError || !room) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950 p-4 text-zinc-200 flex-col gap-4">
        <h2 className="text-xl font-semibold text-red-400">Error loading room</h2>
        <p className="text-zinc-400">The room might not exist or you don't have access.</p>
        <button onClick={() => router.push("/dashboard")} className="text-primary hover:underline">Return to Dashboard</button>
      </div>
    );
  }

  const isHost = user?.id === room.host_id;
  
  // Find current participant if not host
  const currentParticipant = participants.find((p) => p.user_id === user?.id);
  const isEliminated = currentParticipant?.is_eliminated || false;
  
  // Check if current user has already submitted this round
  const hasSubmitted = submissions.some((s) => s.participant_id === currentParticipant?.id && s.round_id === activeRound?.id);
  
  const isRoundActive = activeRound?.status === "active";
  const isScoringPhase = activeRound?.status === "scoring";

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 p-4 md:p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Top Header */}
        <div className="flex justify-end items-center gap-2 mb-2">
          {connected ? (
            <span className="flex items-center text-xs text-emerald-400 bg-emerald-950/30 px-2 py-1 rounded-full border border-emerald-900/50">
              <Wifi className="w-3 h-3 mr-1" /> Live
            </span>
          ) : (
            <span className="flex items-center text-xs text-zinc-500 bg-zinc-900 px-2 py-1 rounded-full border border-zinc-800">
              <WifiOff className="w-3 h-3 mr-1" /> Reconnecting...
            </span>
          )}
        </div>

        <RoomHeader room={room} activeRound={activeRound} participantCount={participants.length} />

        {isEliminated && !isHost && (
          <div className="bg-red-950/40 border border-red-900/50 text-red-200 p-4 rounded-xl flex items-center gap-3">
            <Skull className="w-6 h-6 text-red-400 flex-shrink-0" />
            <div>
              <p className="font-semibold">You have been eliminated.</p>
              <p className="text-sm text-red-300/80">You can still watch the battle unfold, but you cannot submit prompts.</p>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column: Feed & Input */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Host Only: Controls */}
            {isHost && (
              <HostControls roomId={room.id} roomStatus={room.status} activeRound={activeRound} />
            )}

            {/* Host Only: Scoring Panel (Shown during scoring phase) */}
            {isHost && isScoringPhase && (
              <ScoringPanel activeRound={activeRound!} submissions={submissions} participants={participants} />
            )}

            {/* Participant Only: Submit Form */}
            {!isHost && !isEliminated && isRoundActive && (
              <SubmitPromptForm roundId={activeRound!.id} hasSubmitted={hasSubmitted} disabled={!isRoundActive} />
            )}

            {/* Participant Only: Waiting state when round is not active */}
            {!isHost && !isEliminated && !isRoundActive && (
              <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl text-center text-zinc-400">
                Waiting for the host to start the {activeRound ? 'next ' : ''}round...
              </div>
            )}

            {/* Submission Feed */}
            {(isRoundActive || isScoringPhase || submissions.length > 0) && (
              <SubmissionFeed 
                submissions={submissions} 
                jobs={jobs} 
                participants={participants} 
                currentUserId={user?.id || ""} 
              />
            )}
          </div>

          {/* Right Column: Sidebar */}
          <div className="space-y-6">
            <ParticipantList participants={participants} hostId={room.host_id} />
          </div>
        </div>

      </div>
    </div>
  );
}
