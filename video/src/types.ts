/**
 * timeline.json TypeScript interfaces.
 *
 * Matches the canonical schema defined in tts/schema.py (Phase 1).
 * All downstream components consume these types.
 */

export interface TimelineAudio {
  path: string;
  sampleRate: number;
  durationSec: number;
}

export interface TimelineWord {
  w: string;
  start: number;
  end: number;
  speaker: number;
  confidence?: number;
}

export interface TimelineSentence {
  idx: number;
  text: string;
  start: number;
  end: number;
  speaker: number;
  wordRange: [number, number]; // half-open [first, last+1]
}

export interface SceneVisual {
  type:
    | "bullet"
    | "image"
    | "code"
    | "big-number"
    | "comparison"
    | "chart"
    | "steps"
    | "formula"
    | "diagram";
  query: string;
  image?: string; // public/-relative diagram file (diagram scenes only)
  asset?: string; // public/-relative background illustration/video file
  assetKind?: "image" | "video"; // how to render `asset`
  credit?: string; // license attribution
}

export interface SceneChart {
  labels: string[];
  values: number[];
}

export interface TimelineScene {
  idx: number;
  sentenceRange: [number, number]; // half-open [first, last+1]
  start: number;
  end: number;
  onScreenText: string;
  visual: SceneVisual;
  title?: string;
  bullets?: string[];
  emoji?: string;
  chart?: SceneChart;
  formula?: string;
}

export interface TimelineMeta {
  lang: string;
  wer?: number;
  generator: string;
  format?: string; // e.g. "16:9" or "9:16"
  alignMethod?: string;
  alignedAt?: string;
}

export interface Timeline {
  audio: TimelineAudio;
  words: TimelineWord[];
  sentences: TimelineSentence[];
  scenes: TimelineScene[];
  meta: TimelineMeta;
}
