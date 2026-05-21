"use client";

import { useEffect, useState } from "react";
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
import { api } from "@/lib/api";
import { Wifi, WifiOff, Skull, Crown, Medal, Trophy, Flag, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";

interface LeaderboardEntry {
  participant_id: string;
  display_name: string;
  total_points: number;
  is_eliminated: boolean;
}

export default function BattleRoomPage() {
  const { code } = useParams<{ code: string }>();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[] | null>(null);
  const [loadingLeaderboard, setLoadingLeaderboard] = useState(false);

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

  // Fetch leaderboard when room becomes completed
  useEffect(() => {
    if (room?.status === "completed" && room.id && !leaderboard) {
      setLoadingLeaderboard(true);
      api.get(`/rooms/${room.id}/leaderboard`)
        .then(({ data }) => setLeaderboard(data))
        .catch(console.error)
        .finally(() => setLoadingLeaderboard(false));
    }
  }, [room?.status, room?.id]);

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
  const isCompleted = room.status === "completed";
  
  // Find current participant if not host
  const currentParticipant = participants.find((p) => p.user_id === user?.id);
  const isEliminated = currentParticipant?.is_eliminated || false;
  
  // Check if current user has already submitted this round
  const hasSubmitted = submissions.some((s) => s.participant_id === currentParticipant?.id && s.round_id === activeRound?.id);
  
  const isRoundActive = activeRound?.status === "active";
  const isScoringPhase = activeRound?.status === "scoring";

  // ── Completed / Leaderboard view ──────────────────────────────────────────
  if (isCompleted) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-50 p-4 md:p-8 font-sans">
        <div className="max-w-2xl mx-auto space-y-8 pt-12">
          <div className="text-center space-y-2">
            <div className="flex justify-center mb-4">
              <Trophy className="w-14 h-14 text-yellow-400" />
            </div>
            <h1 className="text-4xl font-bold text-yellow-400">Battle Complete!</h1>
            <p className="text-zinc-400">{room.title} — Final Standings</p>
          </div>

          {loadingLeaderboard && <p className="text-center text-zinc-500 animate-pulse">Loading leaderboard…</p>}

          {leaderboard && (
            <div className="space-y-3">
              {leaderboard.map((entry, idx) => (
                <div
                  key={entry.participant_id}
                  className={`flex items-center justify-between p-4 rounded-xl border ${
                    idx === 0
                      ? "bg-yellow-950/40 border-yellow-600/50 ring-1 ring-yellow-500/30"
                      : idx === 1
                      ? "bg-zinc-800/60 border-zinc-600/50"
                      : idx === 2
                      ? "bg-amber-950/20 border-amber-800/40"
                      : "bg-zinc-900/40 border-zinc-800"
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-8 flex justify-center">
                      {idx === 0 ? (
                        <Crown className="w-6 h-6 text-yellow-400" />
                      ) : idx === 1 ? (
                        <Medal className="w-6 h-6 text-zinc-300" />
                      ) : idx === 2 ? (
                        <Medal className="w-6 h-6 text-amber-600" />
                      ) : (
                        <span className="text-zinc-500 font-bold">#{idx + 1}</span>
                      )}
                    </div>
                    <div>
                      <p className={`font-semibold text-lg ${entry.is_eliminated ? "line-through text-zinc-500" : "text-zinc-100"}`}>
                        {entry.display_name}
                      </p>
                      {entry.is_eliminated && (
                        <span className="text-xs text-red-400">Eliminated</span>
                      )}
                    </div>
                  </div>
                  <span className={`text-2xl font-bold ${idx === 0 ? "text-yellow-400" : "text-zinc-300"}`}>
                    {entry.total_points} <span className="text-sm font-normal text-zinc-500">pts</span>
                  </span>
                </div>
              ))}
              {leaderboard.length === 0 && (
                <p className="text-center text-zinc-500 italic">No scores were recorded.</p>
              )}
            </div>
          )}

          <div className="flex justify-center pt-4">
            <Button variant="outline" onClick={() => router.push("/dashboard")} className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
              Back to Dashboard
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // ── Active room view ──────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 p-4 md:p-8 font-sans">
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
                Waiting for the host to start the {activeRound ? 'next ' : ''}round...
              </div>
            )}

            {/* Submission Feed — visible to host only */}
            {isHost && (isRoundActive || isScoringPhase || submissions.length > 0) && (
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
