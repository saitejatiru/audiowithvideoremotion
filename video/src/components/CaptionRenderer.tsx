/**
 * CaptionRenderer — TikTok-style paged captions built from timeline words[].
 *
 * Words are grouped into short pages (max 4 words / ~1.2s). Only the current
 * page shows: big, bold, high-contrast, active word highlighted with a pop.
 * Speaker color per word satisfies VIDEO-04; word timing per token is VIDEO-02.
 */
import React, { useMemo } from "react";
import {
  AbsoluteFill,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { TimelineWord } from "../types";

const SPEAKER_COLORS: Record<number, string> = {
  1: "#FDE047", // yellow highlight — classic caption accent
  2: "#22D3EE",
  3: "#A78BFA",
  4: "#FB923C",
};

const MAX_WORDS_PER_PAGE = 4;
const MAX_PAGE_SPAN_SEC = 1.2;

interface Page {
  words: TimelineWord[];
  start: number;
  end: number;
}

const paginate = (words: TimelineWord[]): Page[] => {
  const pages: Page[] = [];
  let current: TimelineWord[] = [];
  for (const w of words) {
    const spanTooLong =
      current.length > 0 && w.end - current[0].start > MAX_PAGE_SPAN_SEC;
    if (current.length >= MAX_WORDS_PER_PAGE || spanTooLong) {
      pages.push({ words: current, start: current[0].start, end: current[current.length - 1].end });
      current = [];
    }
    current.push(w);
  }
  if (current.length > 0) {
    pages.push({ words: current, start: current[0].start, end: current[current.length - 1].end });
  }
  return pages;
};

const CaptionPage: React.FC<{
  page: Page;
  nextStart: number | null;
  style?: "dark" | "whiteboard";
}> = ({ page, style = "dark" }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const currentTime = page.start + frame / fps; // frame is sequence-relative
  const pop = spring({ frame, fps, config: { damping: 20, stiffness: 300 } });
  const fontSize = width < 1200 ? 64 : 76; // 9:16 vs 16:9
  const wb = style === "whiteboard";

  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center" }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "0 22px",
          maxWidth: "88%",
          marginBottom: 90,
          transform: `scale(${0.9 + 0.1 * pop})`,
        }}
      >
        {page.words.map((word, i) => {
          const isActive = currentTime >= word.start && currentTime < word.end;
          const highlight = SPEAKER_COLORS[word.speaker] || SPEAKER_COLORS[1];
          if (wb) {
            // whiteboard: dark ink; the active word gets a marker-highlighter
            // sweep behind it (yellow), like a teacher highlighting the board
            return (
              <span
                key={i}
                style={{
                  fontSize: fontSize - 8,
                  fontWeight: 800,
                  color: isActive ? "#111827" : "#334155",
                  background: isActive ? highlight : "transparent",
                  borderRadius: 10,
                  padding: "0 10px",
                  transform: isActive ? "scale(1.08)" : "scale(1)",
                  lineHeight: 1.35,
                }}
              >
                {word.w}
              </span>
            );
          }
          return (
            <span
              key={i}
              style={{
                fontSize,
                fontWeight: 900,
                textTransform: "uppercase",
                color: isActive ? highlight : "#FFFFFF",
                transform: isActive ? "scale(1.12)" : "scale(1)",
                WebkitTextStroke: "10px black",
                paintOrder: "stroke fill",
                textShadow: "0 6px 24px rgba(0,0,0,0.8)",
                lineHeight: 1.25,
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

export const CaptionRenderer: React.FC<{
  words: TimelineWord[];
  style?: "dark" | "whiteboard";
}> = ({ words, style = "dark" }) => {
  const { fps, durationInFrames } = useVideoConfig();
  const pages = useMemo(() => paginate(words), [words]);

  return (
    <AbsoluteFill>
      {pages.map((page, i) => {
        const next = pages[i + 1] ?? null;
        const from = Math.round(page.start * fps);
        // hold the page until the next one starts (no caption flicker in gaps)
        const until = next ? Math.round(next.start * fps) : durationInFrames;
        const dur = Math.max(1, until - from);
        return (
          <Sequence key={i} from={from} durationInFrames={dur}>
            <CaptionPage page={page} nextStart={next ? next.start : null} style={style} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
