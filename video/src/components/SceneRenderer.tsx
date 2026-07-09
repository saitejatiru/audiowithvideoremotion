/**
 * SceneRenderer — renders the active scene based on current playback time.
 *
 * Scenes switch at sentence boundaries. The active scene is the one whose
 * [start, end] range contains the current time.
 */
import React from "react";
import { useCurrentFrame, useVideoConfig, AbsoluteFill } from "remotion";
import type { TimelineScene } from "../types";

interface SceneRendererProps {
  scenes: TimelineScene[];
}

const VISUAL_COLORS: Record<string, string> = {
  bullet: "#3B82F6",  // blue
  image: "#10B981",   // green
  code: "#F59E0B",    // amber
};

export const SceneRenderer: React.FC<SceneRendererProps> = ({ scenes }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Find the active scene — the one containing the current time
  const activeScene = scenes.find(
    (s) => currentTime >= s.start && currentTime < s.end
  ) ?? scenes[scenes.length - 1]; // fallback to last scene if past all

  if (!activeScene) return null;

  const accentColor = VISUAL_COLORS[activeScene.visual.type] || "#3B82F6";

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: "60px 80px",
      }}
    >
      {/* Visual type badge */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 60,
          background: accentColor,
          color: "#fff",
          padding: "8px 20px",
          borderRadius: 8,
          fontSize: 18,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: 2,
        }}
      >
        {activeScene.visual.type}
      </div>

      {/* On-screen text — the main content */}
      <div
        style={{
          fontSize: 48,
          fontWeight: 600,
          color: "#F8FAFC",
          textAlign: "center",
          lineHeight: 1.4,
          maxWidth: "80%",
        }}
      >
        {activeScene.onScreenText}
      </div>

      {/* Visual query hint (small, bottom) */}
      <div
        style={{
          position: "absolute",
          bottom: 120,
          fontSize: 16,
          color: "rgba(248, 250, 252, 0.4)",
          fontStyle: "italic",
        }}
      >
        🔍 {activeScene.visual.query}
      </div>
    </AbsoluteFill>
  );
};
