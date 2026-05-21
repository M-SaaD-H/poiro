"use client";

import { useEffect, useRef, useState } from "react";
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
import { Wifi, WifiOff, Skull, Flag, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

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

  // Track previous status to distinguish "room loaded as completed" (redirect
  // immediately, no popup) from "status changed while on page" (show popup).
  const prevRoomStatus = useRef<string | undefined>(undefined);
  const [battleEnded, setBattleEnded] = useState(false);

  useEffect(() => {
    if (!room?.status) return;

    const wasCompleted = prevRoomStatus.current === "completed";
    const isNowCompleted = room.status === "completed";
    const hadPreviousStatus = prevRoomStatus.current !== undefined;

    if (isNowCompleted) {
      if (!hadPreviousStatus || wasCompleted) {
        // Room was already completed on first load — redirect immediately
        router.push("/dashboard");
      } else {
        // Status just changed to completed while user was on the page
        const isHostNow = user?.id === room.host_id;
        if (isHostNow) {
          router.push("/dashboard");
        } else {
          // Show popup to participants, then redirect after 3s
          setBattleEnded(true);
          setTimeout(() => router.push("/dashboard"), 3000);
        }
      }
    }

    prevRoomStatus.current = room.status;
  }, [room?.status, room?.host_id, user?.id]);

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

  // Host sees all submissions; participants only see their own (fair play)
  const visibleSubmissions = isHost
    ? submissions
    : submissions.filter((s) => s.participant_id === currentParticipant?.id);

  // ── Active room view ──────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 p-4 md:p-8 font-sans">

      {/* Battle-ended popup — shown to participants when host closes the battle */}
      {battleEnded && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="bg-zinc-900 border border-red-800/60 ring-1 ring-red-700/30 rounded-2xl p-8 max-w-sm w-full mx-4 text-center shadow-2xl shadow-red-950/40">
            <div className="flex justify-center mb-5">
              <div className="w-16 h-16 rounded-full bg-red-950/60 border border-red-800/50 flex items-center justify-center">
                <Flag className="w-8 h-8 text-red-400" />
              </div>
            </div>
            <h2 className="text-2xl font-bold text-zinc-100 mb-2">Battle Ended</h2>
            <p className="text-zinc-400 mb-6">The host has closed this battle.</p>
            <div className="flex items-center justify-center gap-2 text-zinc-500 text-sm">
              <span className="inline-block w-2 h-2 rounded-full bg-zinc-600 animate-pulse" />
              Returning to dashboard…
            </div>
          </div>
        </div>
      )}

      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Top Header */}
        <div className="flex justify-between items-center mb-2">
          <div /> {/* spacer */}
          <div className="flex items-center gap-3">
            {connected ? (
              <span className="flex items-center text-xs text-emerald-400 bg-emerald-950/30 px-2 py-1 rounded-full border border-emerald-900/50">
                <Wifi className="w-3 h-3 mr-1" /> Live
              </span>
            ) : (
              <span className="flex items-center text-xs text-zinc-500 bg-zinc-900 px-2 py-1 rounded-full border border-zinc-800">
                <WifiOff className="w-3 h-3 mr-1" /> Reconnecting...
              </span>
            )}

            {isHost ? (
              <Button
                size="sm"
                variant="destructive"
                className="bg-red-900/70 hover:bg-red-800 border border-red-800/60 text-red-200 text-xs h-7 px-3"
                onClick={async () => {
                  if (!confirm("Close this battle? All participants will be redirected.")) return;
                  try {
                    await api.post(`/rooms/${room.id}/complete`);
                  } catch {
                    // room may already be completed — still navigate
                  }
                  router.push("/dashboard");
                }}
              >
                <Flag className="w-3 h-3 mr-1" /> Close Battle
              </Button>
            ) : (
              <Button
                size="sm"
                variant="ghost"
                className="text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 border border-zinc-800 text-xs h-7 px-3"
                onClick={async () => {
                  try {
                    await api.delete(`/rooms/${room.id}/leave`);
                  } catch {
                    // already left or not a participant — still navigate
                  }
                  router.push("/dashboard");
                }}
              >
                <LogOut className="w-3 h-3 mr-1" /> Leave Room
              </Button>
            )}
          </div>
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
            
            {/* Host Only: Controls — hidden during scoring so ScoringPanel owns the flow */}
            {isHost && !isScoringPhase && (
              <HostControls roomId={room.id} roomStatus={room.status} activeRound={activeRound} participantCount={participants.length} />
            )}

            {/* Host Only: Scoring Panel (Shown during scoring phase) */}
            {isHost && isScoringPhase && (
              <ScoringPanel activeRound={activeRound!} submissions={submissions} participants={participants} room={room} />
            )}

            {/* Participant Only: Submit Form */}
            {!isHost && !isEliminated && isRoundActive && (
              <SubmitPromptForm roundId={activeRound!.id} hasSubmitted={hasSubmitted} disabled={!isRoundActive} />
            )}

            {/* Participant Only: Waiting state when round is not active */}
            {!isHost && !isEliminated && !isRoundActive && (
              <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl text-center text-zinc-400">
                {isScoringPhase
                  ? "Waiting for the host to finish scoring…"
                  : `Waiting for the host to start the ${activeRound ? "next " : ""}round…`}
              </div>
            )}

            {/* Submission Feed — host sees all, participants see only their own */}
            {(isRoundActive || isScoringPhase || visibleSubmissions.length > 0) && (
              <SubmissionFeed
                submissions={visibleSubmissions}
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
