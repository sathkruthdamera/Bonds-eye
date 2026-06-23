export type StickFigure = {
  mode: string;
  zone: string;
  x: number;
  y: number;
  motion: number;
  confidence: number;
};

export type LiveSnapshot = {
  presence: boolean;
  confidence: number;
  motion_intensity: number;
  signal_disturbance: number;
  pose_state: string;
  zone_state: string;
  node_count: number;
  nodes: Record<string, any>;
  stick_figure: StickFigure | null;
};

type LiveFeedHandle = {
  close: () => void;
};

export function connectLiveFeed(
  url: string,
  onSnapshot: (snapshot: LiveSnapshot) => void,
  onStatus?: (status: string) => void,
): LiveFeedHandle {
  let socket: WebSocket | null = null;
  let closedByUser = false;
  let retryMs = 1000;

  const connect = () => {
    onStatus?.('connecting');
    socket = new WebSocket(url);

    socket.onopen = () => {
      retryMs = 1000;
      onStatus?.('connected');
    };

    socket.onmessage = (message) => {
      try {
        const payload = JSON.parse(message.data);
        if (payload.snapshot) onSnapshot(payload.snapshot);
      } catch (error) {
        console.warn('Invalid live feed payload', error);
      }
    };

    socket.onerror = () => {
      onStatus?.('error');
    };

    socket.onclose = () => {
      if (closedByUser) return;
      onStatus?.('reconnecting');
      const wait = retryMs;
      retryMs = Math.min(retryMs * 2, 15000);
      setTimeout(connect, wait);
    };
  };

  connect();

  return {
    close: () => {
      closedByUser = true;
      socket?.close();
    },
  };
}
