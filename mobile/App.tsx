import React, { useEffect, useState } from 'react';
import { SafeAreaView, ScrollView, Text } from 'react-native';
import NodeCard from './src/components/NodeCard';
import StickFigure from './src/components/StickFigure';
import { connectLiveFeed, LiveSnapshot } from './src/services/liveFeed';

export default function App() {
  const [snapshot, setSnapshot] = useState<LiveSnapshot | null>(null);
  const [status, setStatus] = useState('connecting');

  useEffect(() => {
    const socket = connectLiveFeed('ws://YOUR_SERVER_IP:8080/ws/live', setSnapshot, setStatus);
    return () => socket.close();
  }, []);

  return (
    <SafeAreaView style={{ flex: 1, padding: 16 }}>
      <ScrollView>
        <Text style={{ fontSize: 24, fontWeight: '600' }}>Bonds-eye Dashboard</Text>
        <Text style={{ color: '#64748b', marginBottom: 8 }}>Link: {status}</Text>

        <StickFigure data={snapshot?.stick_figure ?? undefined} />

        <Text style={{ marginTop: 12 }}>Presence: {snapshot?.presence ? 'YES' : 'NO'}</Text>
        <Text>Pose: {snapshot?.pose_state ?? 'UNKNOWN'}</Text>
        <Text>Zone: {snapshot?.zone_state ?? 'UNKNOWN'}</Text>
        <Text>Confidence: {snapshot?.confidence ?? 0}</Text>
        <Text>Motion: {snapshot?.motion_intensity ?? 0}</Text>
        <Text>Disturbance: {snapshot?.signal_disturbance ?? 0}</Text>

        {snapshot?.nodes && Object.entries(snapshot.nodes).map(([id, node]: any) => (
          <NodeCard
            key={id}
            nodeId={id}
            rssi={node.rssi}
            online={node.online}
          />
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}
