# Phase 4: Remotion Render - Research

**Researched:** 2026-07-09
**Domain:** Remotion / React Video Rendering / Audio-Video Sync
**Confidence:** HIGH

## Summary

Phase 4 adds a Remotion-based video project that reads `timeline.json` and renders an MP4. Remotion is a React-based video generation framework. We will pass the `timeline.json` as `inputProps` to the Remotion build CLI.

The core challenge is audio-video sync. `durationInFrames` for the Remotion composition must precisely match the audio duration in frames (`Math.ceil(timeline.audio.durationSec * FPS)`).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIDEO-01 | Remotion composition produces MP4 synced to audio | Remotion CLI `npx remotion render`, `Audio` component for narration |
| VIDEO-02 | Word-level captions appear frame-accurately | `useCurrentFrame()` and `timeline.words` to map words to frames |
| VIDEO-03 | Total duration matches audio | Calculate `durationInFrames` dynamically from `inputProps` |
| VIDEO-04 | Multiple speakers have distinct captions | Map `speaker_id` to color/style in caption renderer |

---

## Standard Stack

| Library | Version | Purpose |
|---------|---------|---------|
| remotion | >= 4.0 | Video rendering framework in React |
| react | >= 18 | UI for video frames |

## Architecture Patterns

### Pattern 1: Dynamic Duration
The composition duration must be dynamic based on the audio length.
```tsx
import { calculateMetadata } from "@remotion/cli";

export const VideoComp = ({ timeline }) => {
  // Render scenes and captions based on timeline
};

// In Root.tsx
<Composition
  id="ExplainerVideo"
  component={VideoComp}
  calculateMetadata={async ({ props }) => {
    return {
      durationInFrames: Math.ceil(props.timeline.audio.durationSec * 30),
    };
  }}
/>
```

### Pattern 2: Captions and Scenes Filtering
Filter words and scenes based on `useCurrentFrame()`.
```tsx
const frame = useCurrentFrame();
const { fps } = useVideoConfig();
const currentTime = frame / fps;

const activeScene = timeline.scenes.find(s => currentTime >= s.start && currentTime <= s.end);
const activeWord = timeline.words.find(w => currentTime >= w.start && currentTime <= w.end);
```

## Anti-Patterns to Avoid
- **Hardcoding framerates:** Always use `useVideoConfig().fps` instead of hardcoding `30`.
- **Loading audio externally:** Load the audio via Remotion's `<Audio>` tag so it is embedded in the final MP4.

## Open Questions
- Default FPS: 30 is recommended for explainers.
- Resolution: 1920x1080 (16:9) or 1080x1920 (9:16 vertical)? We should default to 16:9 for explainer videos.
