import { useEffect, useRef } from "react";
import { useRoomStore } from "@/stores/roomStore";
import { WSEvent } from "@/types";

export function useWebSocket(roomId: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null);
  const { applyEvent, setConnected } = useRoomStore();

  useEffect(() => {
    if (!roomId) return;

    const token = localStorage.getItem("auth_token");
    if (!token) return;

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
    const ws = new WebSocket(`${wsUrl}/ws/rooms/${roomId}?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log(`WebSocket connected to room ${roomId}`);
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as WSEvent;
        console.log("WS Received:", parsed);
        applyEvent(parsed);
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    ws.onclose = (event) => {
      console.log(`WebSocket disconnected: ${event.code} ${event.reason}`);
      setConnected(false);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error", error);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [roomId, applyEvent, setConnected]);

  return wsRef.current;
}
