import React, { useEffect, useState } from 'react';
import { SafeAreaView, ScrollView, Text, View } from 'react-native';
import NodeCard from './src/components/NodeCard';
import { connectLiveFeed } from './src/services/liveFeed';

export default function App() {
  const [snapshot, setSnapshot] = useState<any>(null);

  useEffect(() => {
    const socket = connectLiveFeed('ws://YOUR_SERVER_IP:8080/ws/live', setSnapshot);
    return () => socket.close();
  }, []);

  return (
    <SafeAreaView style={{ flex: 1, padding: 16 }}>
      <ScrollView>
        <Text style={{ fontSize: 24 }}>Bonds-eye Dashboard</Text>
        <Text>Presence: {snapshot?.presence ? 'YES' : 'NO'}</Text>
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
