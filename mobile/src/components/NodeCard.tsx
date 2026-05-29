import React from 'react';
import { View, Text } from 'react-native';

export default function NodeCard({ nodeId, rssi, online }: { nodeId: string; rssi: number; online: boolean }) {
  return (
    <View style={{ padding: 12, marginBottom: 8 }}>
      <Text>{nodeId}</Text>
      <Text>RSSI: {rssi}</Text>
      <Text>Status: {online ? 'ONLINE' : 'OFFLINE'}</Text>
    </View>
  );
}
