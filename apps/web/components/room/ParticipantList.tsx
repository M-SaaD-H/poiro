import { Participant } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, UserX, UserCheck } from "lucide-react";

export function ParticipantList({ participants, hostId }: { participants: Participant[], hostId: string }) {
  return (
    <Card className="bg-zinc-900 border-zinc-800 h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2 text-zinc-100">
          <Users className="w-5 h-5 text-indigo-400" />
          Participants
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {participants.length === 0 ? (
            <li className="text-sm text-zinc-500 italic">No one has joined yet.</li>
          ) : (
            participants.map((p) => (
              <li key={p.id} className="flex items-center justify-between py-2 border-b border-zinc-800/50 last:border-0">
                <span className={`text-sm font-medium ${p.is_eliminated ? 'text-zinc-500 line-through' : 'text-zinc-200'}`}>
                  {p.display_name}
                </span>
                {p.is_eliminated ? (
                  <UserX className="w-4 h-4 text-red-400" />
                ) : (
                  <UserCheck className="w-4 h-4 text-emerald-400" />
                )}
              </li>
            ))
          )}
        </ul>
      </CardContent>
    </Card>
  );
}
