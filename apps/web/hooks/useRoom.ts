import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { RoomSnapshot } from "@/types";

/**
 * Fetches the full room state snapshot by join code in a **single HTTP call**.
 *
 * Previously this made two serial requests (GET /rooms/{code} then
 * GET /rooms/{id}/state), adding a full RTT before the WebSocket could open.
 * The backend now exposes GET /rooms/{code}/state which does both in one
 * database query.
 */
export function useRoom(code: string) {
  return useQuery({
    queryKey: ["room", code],
    queryFn: async () => {
      const { data } = await api.get<RoomSnapshot>(`/rooms/${code}/state`);
      return data;
    },
    enabled: !!code,
    retry: false,
  });
}
