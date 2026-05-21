import { useState, useEffect } from "react";
import { Round, Submission, Participant, Score, Room } from "@/types";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { CheckCircle2, Trophy, Loader2, Play, Flag } from "lucide-react";

export function ScoringPanel({
  activeRound,
  submissions,
  participants,
  room,
}: {
  activeRound: Round;
  submissions: Submission[];
  participants: Participant[];
  room: Room;
}) {
  const [existingScores, setExistingScores] = useState<Score[]>([]);
  const [loadingScores, setLoadingScores] = useState(true);
  const [submittingIds, setSubmittingIds] = useState<Set<string>>(new Set());
  const [isStartingNext, setIsStartingNext] = useState(false);
  const [isEndingBattle, setIsEndingBattle] = useState(false);

  // Local state for the forms
  const [points, setPoints] = useState<Record<string, string>>({});
  const [eliminated, setEliminated] = useState<Record<string, boolean>>({});

  useEffect(() => {
    async function fetchScores() {
      try {
        const { data } = await api.get(`/rounds/${activeRound.id}/scores`);
        setExistingScores(data);
      } catch (err) {
        console.error("Failed to load scores", err);
      } finally {
        setLoadingScores(false);
      }
    }
    fetchScores();
  }, [activeRound.id]);

  async function submitScore(participantId: string) {
    const pts = parseInt(points[participantId] || "0", 10);
    const isEliminated = eliminated[participantId] || false;

    if (isNaN(pts) || pts < 0 || pts > 100) {
      toast.error("Points must be between 0 and 100");
      return;
    }

    setSubmittingIds((prev) => new Set(prev).add(participantId));
    try {
      const { data } = await api.post(`/rounds/${activeRound.id}/scores`, {
        participant_id: participantId,
        points: pts,
        is_eliminated: isEliminated,
      });
      setExistingScores((prev) => [...prev, data]);
      toast.success("Score saved");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to save score");
    } finally {
      setSubmittingIds((prev) => {
        const next = new Set(prev);
        next.delete(participantId);
        return next;
      });
    }
  }

  async function handleStartNextRound() {
    setIsStartingNext(true);
    try {
      await api.post(`/rooms/${room.id}/rounds/start`);
      toast.success(`Round ${activeRound.round_number + 1} started!`);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to start next round");
    } finally {
      setIsStartingNext(false);
    }
  }

  async function handleEndBattle() {
    setIsEndingBattle(true);
    try {
      await api.post(`/rooms/${room.id}/complete`);
      // room:completed WS event will fire and page.tsx's useEffect
      // redirects everyone (host + all participants) to /dashboard
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to end battle");
      setIsEndingBattle(false);
    }
  }

  // Non-eliminated participants that have submitted this round
  const scorableSubmissions = submissions.filter((sub) => {
    const p = participants.find((p) => p.id === sub.participant_id);
    return p && !p.is_eliminated;
  });

  const allScored =
    scorableSubmissions.length > 0 &&
    scorableSubmissions.every((sub) =>
      existingScores.some((s) => s.participant_id === sub.participant_id)
    );

  const isLastRound = activeRound.round_number >= room.max_rounds;

  if (loadingScores) return <div className="text-zinc-500 py-4">Loading scores...</div>;

  return (
    <Card className="bg-zinc-900 border-yellow-500/30 ring-1 ring-yellow-500/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-yellow-500">
          <Trophy className="w-5 h-5" />
          Scoring Phase — Round {activeRound.round_number}/{room.max_rounds}
        </CardTitle>
        <CardDescription className="text-zinc-400">
          Award points to each participant. You may also eliminate participants.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {scorableSubmissions.map((sub) => {
          const participant = participants.find((p) => p.id === sub.participant_id);
          if (!participant) return null;

          const existingScore = existingScores.find((s) => s.participant_id === participant.id);
          const isSubmitting = submittingIds.has(participant.id);

          return (
            <div key={sub.id} className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between p-4 bg-zinc-950 rounded-lg border border-zinc-800">
              <div className="flex-1">
                <div className="font-medium text-zinc-200">{participant.display_name}</div>
                <div className="text-xs text-zinc-500 truncate max-w-xs">{sub.prompt}</div>
              </div>

              {existingScore ? (
                <div className="flex items-center gap-4 text-sm bg-emerald-950/30 text-emerald-400 px-4 py-2 rounded-md border border-emerald-900/50">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{existingScore.points} pts</span>
                  {existingScore.is_eliminated && <span className="text-red-400 font-medium">Eliminated</span>}
                </div>
              ) : (
                <div className="flex items-center gap-4 flex-wrap sm:flex-nowrap">
                  <div className="flex items-center gap-2">
                    <Label htmlFor={`pts-${participant.id}`} className="text-zinc-400">Pts (0-100)</Label>
                    <Input
                      id={`pts-${participant.id}`}
                      type="number"
                      min="0" max="100"
                      className="w-20 bg-zinc-900 border-zinc-700 h-9 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                      value={points[participant.id] || ""}
                      onChange={(e) => setPoints({ ...points, [participant.id]: e.target.value })}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <Label htmlFor={`elim-${participant.id}`} className="text-zinc-400 cursor-pointer">Eliminate?</Label>
                    <Switch
                      id={`elim-${participant.id}`}
                      checked={eliminated[participant.id] || false}
                      onCheckedChange={(val) => setEliminated({ ...eliminated, [participant.id]: val })}
                    />
                  </div>
                  <Button
                    size="sm"
                    className="bg-yellow-600 hover:bg-yellow-700 text-yellow-50"
                    disabled={isSubmitting}
                    onClick={() => submitScore(participant.id)}
                  >
                    {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save"}
                  </Button>
                </div>
              )}
            </div>
          );
        })}

        {submissions.length === 0 && (
          <div className="text-sm text-zinc-500 italic">No submissions to score.</div>
        )}

        {/* Action footer: shown once all submissions are scored */}
        {allScored && (
          <div className="pt-4 border-t border-zinc-800 flex items-center justify-between">
            <p className="text-sm text-zinc-400">
              {isLastRound
                ? "All rounds complete. End the battle to reveal the leaderboard."
                : `Round ${activeRound.round_number} complete. Start the next round when ready.`}
            </p>
            {isLastRound ? (
              <Button
                onClick={handleEndBattle}
                disabled={isEndingBattle}
                className="bg-red-700 hover:bg-red-600 text-white"
              >
                {isEndingBattle ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Flag className="w-4 h-4 mr-2" />}
                End Battle
              </Button>
            ) : (
              <Button
                onClick={handleStartNextRound}
                disabled={isStartingNext}
                className="bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                {isStartingNext ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
                Start Round {activeRound.round_number + 1}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
