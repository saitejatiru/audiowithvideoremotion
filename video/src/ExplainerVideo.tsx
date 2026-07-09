/**
 * ExplainerVideo — main Remotion composition.
 *
 * Consumes timeline.json as props. Embeds narration audio via <Audio>,
 * renders scenes and word-level captions synced to the audio.
 *
 * Duration is dynamic — calculated from timeline.audio.durationSec in Root.tsx.
 */
import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import type { Timeline } from "./types";
import { SceneRenderer } from "./components/SceneRenderer";
import { CaptionRenderer } from "./components/CaptionRenderer";

interface ExplainerVideoProps {
  timeline: Timeline;
}

export const ExplainerVideo: React.FC<ExplainerVideoProps> = ({ timeline }) => {
  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%)",
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      }}
    >
      {/* Narration audio — embedded in final MP4 */}
      <Audio src={staticFile(timeline.audio.path)} />

      {/* Scene content — switches at sentence boundaries */}
      <SceneRenderer scenes={timeline.scenes} />

      {/* Word-level captions — frame-accurate, speaker-colored */}
      <CaptionRenderer words={timeline.words} />
    </AbsoluteFill>
  );
};
