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

/**
 * Default timeline for Remotion Studio preview.
 * In production, this is overridden by --props timeline.json.
 * Uses style "whiteboard" + a sample diagram so the scribe look is visible.
 */
const defaultTimeline: Timeline = {
  audio: { path: "audio.wav", sampleRate: 24000, durationSec: 15.0 },
  words: [
    { w: "The", start: 0.2, end: 0.4, speaker: 1 },
    { w: "cell", start: 0.4, end: 0.9, speaker: 1 },
    { w: "is", start: 0.9, end: 1.1, speaker: 1 },
    { w: "the", start: 1.1, end: 1.3, speaker: 1 },
    { w: "basic", start: 1.3, end: 1.8, speaker: 1 },
    { w: "unit", start: 1.8, end: 2.2, speaker: 1 },
    { w: "of", start: 2.2, end: 2.4, speaker: 1 },
    { w: "life.", start: 2.4, end: 3.0, speaker: 1 },
    { w: "It", start: 5.2, end: 5.4, speaker: 1 },
    { w: "has", start: 5.4, end: 5.7, speaker: 1 },
    { w: "three", start: 5.7, end: 6.1, speaker: 1 },
    { w: "main", start: 6.1, end: 6.5, speaker: 1 },
    { w: "parts.", start: 6.5, end: 7.1, speaker: 1 },
  ],
  sentences: [
    { idx: 0, text: "The cell is the basic unit of life.", start: 0.0, end: 5.0, speaker: 1, wordRange: [0, 8] },
    { idx: 1, text: "It has three main parts.", start: 5.0, end: 15.0, speaker: 1, wordRange: [8, 13] },
  ],
  scenes: [
    {
      idx: 0,
      sentenceRange: [0, 1],
      start: 0.0,
      end: 5.0,
      onScreenText: "The smallest living unit",
      title: "The Cell",
      emoji: "🔬",
      visual: { type: "diagram", query: "cell", image: "sample-diagram.svg", credit: "Sample diagram" },
    },
    {
      idx: 1,
      sentenceRange: [1, 2],
      start: 5.0,
      end: 15.0,
      onScreenText: "Every cell shares these",
      title: "Three Main Parts",
      bullets: ["Cell membrane", "Cytoplasm", "Nucleus"],
      visual: { type: "bullet", query: "cell parts" },
    },
  ],
  meta: { lang: "en", generator: "preview", style: "whiteboard" },
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
