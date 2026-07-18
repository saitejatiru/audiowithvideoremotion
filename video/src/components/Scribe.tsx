/**
 * Scribe.tsx — whiteboard draw-on primitives for the scribe explanation style.
 *
 * ScribeReveal: an image is progressively "drawn" onto the board — revealed in
 * horizontal strips, boustrophedon (left→right, then right→left, like a real
 * hand sketching), with a ✍️ hand tracking the reveal front. Same trick
 * commercial scribe tools (VideoScribe) use for raster images.
 *
 * WriteOn: text (or any block) revealed left→right via clip-path, like being
 * written with a marker. Works for multiline blocks.
 *
 * MarkerLine: an underline stroke that draws itself (SVG dashoffset).
 */
import React from "react";
import {
  Img,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const STRIPS = 6;

/** 0→1 draw progress over the first ~55% of the scene (clamped 0.7s–3s). */
const useDrawProgress = (durFrames: number, delayFrames = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const revealFrames = Math.min(Math.max(0.7 * fps, durFrames * 0.55), 3 * fps);
  return interpolate(frame - delayFrames, [0, revealFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};

export const ScribeReveal: React.FC<{
  src: string;
  durFrames: number;
  width: number;
  height: number;
  paper?: string; // board color the cover strips must match
}> = ({ src, durFrames, width, height, paper = "#FDFDF8" }) => {
  const p = useDrawProgress(durFrames, 4);
  const stripH = height / STRIPS;

  // hand position: which strip is being drawn, and how far along it
  const stripF = Math.min(p * STRIPS, STRIPS - 0.0001);
  const strip = Math.floor(stripF);
  const local = stripF - strip; // 0..1 within current strip
  const leftToRight = strip % 2 === 0;
  const handX = (leftToRight ? local : 1 - local) * width;
  const handY = (strip + 0.6) * stripH;

  return (
    <div style={{ position: "relative", width, height }}>
      <Img
        src={src}
        style={{ width: "100%", height: "100%", objectFit: "contain" }}
      />
      {/* cover strips: hide the not-yet-drawn part of each row */}
      {Array.from({ length: STRIPS }, (_, i) => {
        const li = Math.min(Math.max(p * STRIPS - i, 0), 1); // strip i local progress
        const l2r = i % 2 === 0;
        const w = (1 - li) * 100;
        if (w <= 0) return null;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              top: i * stripH - 1,
              height: stripH + 2,
              width: `${w}%`,
              ...(l2r ? { right: 0 } : { left: 0 }),
              background: paper,
            }}
          />
        );
      })}
      {/* the drawing hand — vanishes when the sketch completes */}
      {p < 1 && (
        <div
          style={{
            position: "absolute",
            left: handX - 20,
            top: handY - 30,
            fontSize: 84,
            transform: "rotate(-15deg)",
            filter: "drop-shadow(2px 4px 4px rgba(0,0,0,0.25))",
          }}
        >
          ✍️
        </div>
      )}
    </div>
  );
};

export const WriteOn: React.FC<{
  children: React.ReactNode;
  delayFrames?: number;
  durationFrames?: number;
  style?: React.CSSProperties;
}> = ({ children, delayFrames = 0, durationFrames = 18, style }) => {
  const frame = useCurrentFrame();
  const p = interpolate(
    frame - delayFrames,
    [0, durationFrames],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  return (
    <div
      style={{
        ...style,
        clipPath: `inset(0 ${(1 - p) * 100}% 0 0)`,
        opacity: p > 0 ? 1 : 0,
      }}
    >
      {children}
    </div>
  );
};

export const MarkerLine: React.FC<{
  width: number;
  color: string;
  delayFrames?: number;
}> = ({ width, color, delayFrames = 8 }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame - delayFrames, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <svg width={width} height={14} style={{ display: "block" }}>
      <path
        d={`M 4 8 Q ${width * 0.3} 3, ${width * 0.55} 8 T ${width - 6} 7`}
        stroke={color}
        strokeWidth={6}
        strokeLinecap="round"
        fill="none"
        strokeDasharray={width * 1.2}
        strokeDashoffset={(1 - p) * width * 1.2}
      />
    </svg>
  );
};
