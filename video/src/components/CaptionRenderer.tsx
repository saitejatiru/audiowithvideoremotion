/**
 * CaptionRenderer — word-level captions with speaker-specific colors.
 *
 * Each word appears and disappears frame-accurately based on its start/end
 * timestamps from timeline.json. The currently-spoken word is highlighted
 * (TikTok-style active word). VIDEO-02 + VIDEO-04.
 */
import React from "react";
import { useCurrentFrame, useVideoConfig, AbsoluteFill } from "remotion";
import type { TimelineWord } from "../types";

interface CaptionRendererProps {
  words: TimelineWord[];
}

/**
 * Speaker color palette. Speaker 1 = white, Speaker 2 = cyan, etc.
 * Maps to the VIDEO-04 requirement (multi-speaker distinct captions).
 */
const SPEAKER_COLORS: Record<number, string> = {
  1: "#FFFFFF",
  2: "#22D3EE",
  3: "#A78BFA",
  4: "#FB923C",
};

/**
 * How many surrounding words to show for context.
 * Shows a sliding window of words around the active one.
 */
const CONTEXT_WINDOW = 6;

export const CaptionRenderer: React.FC<CaptionRendererProps> = ({ words }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Find the index of the currently-active word
  const activeIdx = words.findIndex(
    (w) => currentTime >= w.start && currentTime < w.end
  );

  // If no word is active (silence/gap), find the most recent one
  const displayIdx =
    activeIdx >= 0
      ? activeIdx
      : words.findLastIndex((w) => currentTime >= w.end);

  if (displayIdx < 0) return null;

  // Sliding window: show surrounding words for context
  const windowStart = Math.max(0, displayIdx - CONTEXT_WINDOW);
  const windowEnd = Math.min(words.length, displayIdx + CONTEXT_WINDOW + 1);
  const visibleWords = words.slice(windowStart, windowEnd);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 60,
      }}
    >
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "6px 10px",
          maxWidth: "80%",
          padding: "16px 24px",
          background: "rgba(0, 0, 0, 0.6)",
          borderRadius: 12,
          backdropFilter: "blur(8px)",
        }}
      >
        {visibleWords.map((word, i) => {
          const globalIdx = windowStart + i;
          const isActive = globalIdx === activeIdx;
          const isPast = currentTime > word.end;
          const speakerColor =
            SPEAKER_COLORS[word.speaker] || SPEAKER_COLORS[1];

          return (
            <span
              key={`${globalIdx}-${word.w}`}
              style={{
                fontSize: isActive ? 36 : 30,
                fontWeight: isActive ? 800 : 500,
                color: isActive
                  ? speakerColor
                  : isPast
                    ? "rgba(255, 255, 255, 0.4)"
                    : "rgba(255, 255, 255, 0.6)",
                transform: isActive ? "scale(1.1)" : "scale(1)",
                transition: "all 0.1s ease",
                textShadow: isActive
                  ? `0 0 20px ${speakerColor}80`
                  : "none",
              }}
            >
              {word.w}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
