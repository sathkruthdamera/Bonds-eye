export type LiveSnapshot = {
  presence: boolean;
  confidence: number;
  motion_intensity: number;
  signal_disturbance: number;
  node_count: number;
  nodes: Record<string, any>;
};

export function connectLiveFeed(url: string, onSnapshot: (snapshot: LiveSnapshot) => void, onError?: (event: Event) => void): WebSocket {
  const socket = new WebSocket(url);

  socket.onmessage = (message) => {
    try {
      const payload = JSON.parse(message.data);
      if (payload.snapshot) {
        onSnapshot(payload.snapshot);
      }
    } catch (error) {
      console.warn('Invalid live feed payload', error);
    }
  };

  socket.onerror = (event) => {
    if (onError) onError(event);
  };

  return socket;
}
