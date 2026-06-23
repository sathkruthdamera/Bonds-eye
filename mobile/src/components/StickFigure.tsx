import React from 'react';
import { View, Text } from 'react-native';
import Svg, { Circle, Line } from 'react-native-svg';

export type StickFigureData = {
  mode: string;
  zone: string;
  x: number;
  y: number;
  motion: number;
  confidence: number;
};

const deg = (d: number) => (d * Math.PI) / 180;
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

// Draws an abstract RF-driven stick avatar. This is not a real skeleton; it is a
// visual approximation of pose_state + zone_state + motion coming from the API.
export default function StickFigure({ data }: { data?: StickFigureData }) {
  const mode = data?.mode ?? 'NO_PERSON';
  const motion = clamp(data?.motion ?? 0, 0, 1);
  const xNorm = clamp(data?.x ?? 0.5, 0, 1);

  const dim = mode === 'NO_PERSON' || mode === 'UNKNOWN';
  const crouch = mode === 'CROUCH_LIKE';
  const moving = mode === 'MOVING';

  const color = dim ? '#5b6472' : moving ? '#22c55e' : '#38bdf8';
  const opacity = dim ? 0.4 : 1;

  // Horizontal placement from zone (kept clear of the edges).
  const cx = clamp(xNorm * 100, 18, 82);

  const headR = 9;
  const headCy = crouch ? 36 : 26;
  const neckY = headCy + headR;
  const torsoLen = crouch ? 26 : 40;
  const hipY = neckY + torsoLen;
  const shoulderY = neckY + 6;

  const armLen = 26;
  const legLen = crouch ? 26 : 34;

  const armSpread = (crouch ? 30 : 16) + (moving ? motion * 26 : 0);
  const legSpread = (crouch ? 26 : 12) + (moving ? motion * 18 : 0);

  const leftHandX = cx - Math.sin(deg(armSpread)) * armLen;
  const rightHandX = cx + Math.sin(deg(armSpread)) * armLen;
  const handY = shoulderY + Math.cos(deg(armSpread)) * armLen;

  const leftFootX = cx - Math.sin(deg(legSpread)) * legLen;
  const rightFootX = cx + Math.sin(deg(legSpread)) * legLen;
  const footY = hipY + Math.cos(deg(legSpread)) * legLen;

  return (
    <View style={{ backgroundColor: '#0f172a', borderRadius: 12, paddingVertical: 8 }}>
      <Svg width="100%" height={240} viewBox="0 0 100 120">
        {/* ground / zone baseline */}
        <Line x1={6} y1={112} x2={94} y2={112} stroke="#1e293b" strokeWidth={2} />
        <Line x1={cx} y1={108} x2={cx} y2={116} stroke="#334155" strokeWidth={2} />

        {/* head */}
        <Circle cx={cx} cy={headCy} r={headR} stroke={color} strokeWidth={3} fill="none" opacity={opacity} />
        {/* spine */}
        <Line x1={cx} y1={neckY} x2={cx} y2={hipY} stroke={color} strokeWidth={3} strokeLinecap="round" opacity={opacity} />
        {/* arms */}
        <Line x1={cx} y1={shoulderY} x2={leftHandX} y2={handY} stroke={color} strokeWidth={3} strokeLinecap="round" opacity={opacity} />
        <Line x1={cx} y1={shoulderY} x2={rightHandX} y2={handY} stroke={color} strokeWidth={3} strokeLinecap="round" opacity={opacity} />
        {/* legs */}
        <Line x1={cx} y1={hipY} x2={leftFootX} y2={footY} stroke={color} strokeWidth={3} strokeLinecap="round" opacity={opacity} />
        <Line x1={cx} y1={hipY} x2={rightFootX} y2={footY} stroke={color} strokeWidth={3} strokeLinecap="round" opacity={opacity} />
      </Svg>
      <Text style={{ color: '#94a3b8', textAlign: 'center', marginTop: 4 }}>
        {mode} · {data?.zone ?? 'UNKNOWN'} · motion {Math.round(motion * 100)}%
      </Text>
    </View>
  );
}
