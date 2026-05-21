import { useEffect, useRef } from "react";
import { useRoomStore } from "@/stores/roomStore";
import { WSEvent } from "@/types";

// Exponential backoff config
const BACKOFF_BASE_MS = 500;
const BACKOFF_MAX_MS = 30_000;

/**
 * Manages a WebSocket connection to a room with automatic exponential-backoff
 * reconnection.
 *
 * On every connect (initial or reconnect) the server sends a `room:state`
 * snapshot, so no manual re-hydration is needed on the client side.
 *
 * The reconnect loop stops only when the component unmounts (`shouldReconnect`
 * is set to false before the WebSocket is closed intentionally).
 */
export function useWebSocket(roomId: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const shouldReconnectRef = useRef(true);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!roomId) return;

    shouldReconnectRef.current = true;

    function getBackoffDelay(): number {
      const delay = Math.min(
        BACKOFF_BASE_MS * 2 ** reconnectAttemptRef.current,
        BACKOFF_MAX_MS
      );
      reconnectAttemptRef.current += 1;
      return delay;
    }

    function connect() {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        // No auth token — don't attempt WS connection
        return;
      }

      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
      const ws = new WebSocket(`${wsUrl}/ws/rooms/${roomId}?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`[WS] Connected to room ${roomId}`);
        reconnectAttemptRef.current = 0; // reset backoff on successful connect
        useRoomStore.getState().setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as WSEvent;
          console.log("[WS] Received:", parsed.event);
          useRoomStore.getState().applyEvent(parsed);
        } catch (err) {
          console.error("[WS] Failed to parse message", err);
        }
      };

      ws.onclose = (event) => {
        console.log(`[WS] Disconnected: ${event.code} ${event.reason}`);
        useRoomStore.getState().setConnected(false);

        if (!shouldReconnectRef.current) return;

        // Policy violation (1008) = bad token — don't reconnect
        if (event.code === 1008) {
          console.warn("[WS] Auth rejected — will not reconnect.");
          return;
        }

        // Room completed — page is redirecting, no point reconnecting
        const currentRoom = useRoomStore.getState().room;
        if (currentRoom?.status === "completed") {
          console.log("[WS] Room completed — stopping reconnect loop.");
          return;
        }

        const delay = getBackoffDelay();
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current})`);
        reconnectTimerRef.current = setTimeout(() => {
          if (shouldReconnectRef.current) connect();
        }, delay);
      };

      ws.onerror = (error) => {
        // onclose fires immediately after onerror — reconnect is handled there
        console.error("[WS] Error:", error);
      };
    }

    connect();

    return () => {
      // Mark as intentional close so onclose doesn't trigger reconnect
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      const ws = wsRef.current;
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
    };
  }, [roomId]);

  return wsRef.current;
}
