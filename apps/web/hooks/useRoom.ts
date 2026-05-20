import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { RoomSnapshot } from "@/types";

export function useRoom(code: string) {
  return useQuery({
    queryKey: ["room", code],
    queryFn: async () => {
      // First, get the room id using the code
      const { data: roomData } = await api.get(`/rooms/${code}`);
      // Then fetch the full state snapshot using the room id
      const { data: stateData } = await api.get<RoomSnapshot>(`/rooms/${roomData.id}/state`);
      return stateData;
    },
    enabled: !!code,
    retry: false,
  });
}
