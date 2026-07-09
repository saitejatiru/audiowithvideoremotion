/**
 * Root.tsx — Remotion root component.
 *
 * Registers the ExplainerVideo composition with dynamic duration calculated
 * from timeline.audio.durationSec. This ensures VIDEO-03: total video duration
 * matches the actual audio length to within one frame.
 */
import React from "react";
import { Composition } from "remotion";
import { ExplainerVideo } from "./ExplainerVideo";
import type { Timeline } from "./types";

const FPS = 30;
const WIDTH = 1920;
const HEIGHT = 1080;

/**
 * Default timeline for Remotion Studio preview.
 * In production, this is overridden by --props timeline.json.
 */
const defaultTimeline: Timeline = {
  audio: { path: "audio.wav", sampleRate: 24000, durationSec: 5.0 },
  words: [
    { w: "Hello", start: 0.0, end: 0.5, speaker: 1 },
    { w: "world.", start: 0.5, end: 1.2, speaker: 1 },
  ],
  sentences: [
    { idx: 0, text: "Hello world.", start: 0.0, end: 1.2, speaker: 1, wordRange: [0, 2] },
  ],
  scenes: [
    {
      idx: 0,
      sentenceRange: [0, 1],
      start: 0.0,
      end: 1.2,
      onScreenText: "Hello world.",
      visual: { type: "bullet", query: "hello" },
    },
  ],
  meta: { lang: "en", generator: "preview" },
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ExplainerVideo"
        component={ExplainerVideo as any}
        defaultProps={{ timeline: defaultTimeline }}
        calculateMetadata={({ props }) => {
          const timeline = (props as any).timeline as Timeline;
          const isReel = timeline.meta?.format === "9:16";
          const width = isReel ? 1080 : 1920;
          const height = isReel ? 1920 : 1080;
          return {
            width,
            height,
            fps: FPS,
            durationInFrames: Math.max(
              1,
              Math.ceil(timeline.audio.durationSec * FPS)
            ),
          };
        }}
      />
    </>
  );
};
