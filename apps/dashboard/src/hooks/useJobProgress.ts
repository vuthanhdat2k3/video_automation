import { useEffect, useRef, useState, useCallback } from 'react';

interface JobEvent {
  type: 'init' | 'job.completed' | 'job.failed' | 'job.created' | 'job.progress';
  job?: Record<string, unknown>;
  jobs?: Record<string, unknown>[];
}

export function useJobProgress(projectId: string | undefined) {
  const [jobs, setJobs] = useState<Record<string, unknown>[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!projectId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}://${host}/api/v1/ws/projects/${projectId}`);

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data: JobEvent = JSON.parse(event.data);
        if (data.type === 'init' && data.jobs) {
          setJobs(data.jobs);
        } else if (data.job) {
          setJobs((prev) => {
            const idx = prev.findIndex((j) => j.id === data.job!.id);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = data.job!;
              return next;
            }
            return [...prev, data.job!];
          });
        }
      } catch {
        // ignore bad payload
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [projectId]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { jobs, connected };
}
