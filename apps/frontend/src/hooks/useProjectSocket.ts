import { useEffect, useRef } from "react";

import { useJobsStore } from "../stores/jobsStore";
import type { JobProgressMessage } from "../types/api";

/** Se conecta a /api/ws/projects/{projectId} y vuelca cada mensaje de
 * progreso en el store global de jobs. Reconecta automaticamente si el
 * socket se cierra (por ejemplo tras reiniciar el backend). */
export function useProjectSocket(projectId: string | undefined) {
  const setJob = useJobsStore((s) => s.setJob);
  const retryRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (!projectId) return;
    let closedByUser = false;
    let socket: WebSocket;

    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(`${protocol}//${window.location.host}/api/ws/projects/${projectId}`);
      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as JobProgressMessage;
          setJob(msg);
        } catch {
          /* ignorar mensajes no-JSON */
        }
      };
      socket.onclose = () => {
        if (!closedByUser) {
          retryRef.current = setTimeout(connect, 2000);
        }
      };
    }

    connect();
    return () => {
      closedByUser = true;
      if (retryRef.current) clearTimeout(retryRef.current);
      socket?.close();
    };
  }, [projectId, setJob]);
}
