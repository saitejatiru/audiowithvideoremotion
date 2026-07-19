/**
 * SceneRenderer — animated educational scene templates, in two styles:
 *
 *  "dark" (default): dark gradient, fetched illustration/video as a full-bleed
 *   background behind animated text.
 *
 *  "whiteboard" (scribe): paper board, handwriting fonts, and every element
 *   DRAWS ON — images sketch in strip-by-strip with a ✍️ hand (ScribeReveal),
 *   titles write on with a marker underline, bullets write in one by one.
 *   This is the "teacher at a whiteboard" explanation style.
 *
 * Each scene renders inside its own <Sequence> so entrance animations restart
 * per scene. Scenes hold until the next scene starts (no blank frames), and
 * switch at sentence boundaries (STORY-03).
 */
import React from "react";
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import katex from "katex";
import "katex/dist/katex.min.css";
import { loadFont as loadCaveat } from "@remotion/google-fonts/Caveat";
import { loadFont as loadPatrickHand } from "@remotion/google-fonts/PatrickHand";
import type { TimelineScene } from "../types";
import { MarkerLine, ScribeReveal, WriteOn } from "./Scribe";

const caveat = loadCaveat();
const patrick = loadPatrickHand();

export type SceneStyle = "dark" | "whiteboard";

const ACCENTS: Record<string, string> = {
  bullet: "#3B82F6",
  image: "#10B981",
  code: "#F59E0B",
  "big-number": "#F43F5E",
  comparison: "#A78BFA",
  chart: "#38BDF8",
  steps: "#34D399",
  formula: "#FBBF24",
  diagram: "#F472B6",
};

// Marker-pen palette for the whiteboard: same keys, board-legible colors.
const WB_ACCENTS: Record<string, string> = {
  bullet: "#2563EB",
  image: "#059669",
  code: "#D97706",
  "big-number": "#DC2626",
  comparison: "#7C3AED",
  chart: "#0284C7",
  steps: "#059669",
  formula: "#B45309",
  diagram: "#DB2777",
};

interface Theme {
  ink: string;      // strongest text
  text: string;     // body text
  sub: string;      // secondary text
  card: string;     // card background
  border: string;   // neutral border
  codeBg: string;
  codeText: string;
  paper: string;    // board background (whiteboard only)
  titleFont: string;
  bodyFont: string;
}

const THEMES: Record<SceneStyle, Theme> = {
  dark: {
    ink: "#F8FAFC",
    text: "#E2E8F0",
    sub: "#94A3B8",
    card: "#1E293B",
    border: "#334155",
    codeBg: "#0B1220",
    codeText: "#A5F3FC",
    paper: "#0F172A",
    titleFont: "'Inter', 'Segoe UI', system-ui, sans-serif",
    bodyFont: "'Inter', 'Segoe UI', system-ui, sans-serif",
  },
  whiteboard: {
    ink: "#1E293B",
    text: "#334155",
    sub: "#64748B",
    card: "#F1F5F9",
    border: "#CBD5E1",
    codeBg: "#F8FAFC",
    codeText: "#0F766E",
    paper: "#FDFDF8",
    titleFont: `'${caveat.fontFamily}', cursive`,
    bodyFont: `'${patrick.fontFamily}', cursive`,
  },
};

/** Spring entrance: slide up + fade (dark style). */
const useEntrance = (delayFrames = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - delayFrames, fps, config: { damping: 200 } });
  return {
    opacity: p,
    transform: `translateY(${interpolate(p, [0, 1], [40, 0])}px)`,
  };
};

const Title: React.FC<{
  text: string;
  accent: string;
  style: SceneStyle;
  small?: boolean;
}> = ({ text, accent, style, small }) => {
  const entrance = useEntrance(0);
  if (!text) return null;
  const T = THEMES[style];
  if (style === "whiteboard") {
    return (
      <div style={{ marginBottom: 36, textAlign: "center" }}>
        <WriteOn durationFrames={16}>
          <div
            style={{
              fontFamily: T.titleFont,
              fontSize: small ? 68 : 88,
              fontWeight: 700,
              color: T.ink,
              lineHeight: 1.1,
            }}
          >
            {text}
          </div>
        </WriteOn>
        <MarkerLine width={Math.min(90 + text.length * 22, 700)} color={accent} />
      </div>
    );
  }
  return (
    <div
      style={{
        ...entrance,
        fontSize: small ? 44 : 64,
        fontWeight: 800,
        color: T.ink,
        textAlign: "center",
        borderBottom: `6px solid ${accent}`,
        paddingBottom: 12,
        marginBottom: 40,
        maxWidth: "85%",
      }}
    >
      {text}
    </div>
  );
};

const Bullets: React.FC<{ items: string[]; accent: string; style: SceneStyle }> = ({
  items,
  accent,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const T = THEMES[style];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28, maxWidth: "80%" }}>
      {items.map((b, i) => {
        const delay = 12 + i * 16;
        if (style === "whiteboard") {
          return (
            <WriteOn key={i} delayFrames={delay} durationFrames={14}>
              <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
                <div style={{ fontSize: 40, color: accent, lineHeight: 1 }}>✏️</div>
                <div style={{ fontFamily: T.bodyFont, fontSize: 48, color: T.text }}>{b}</div>
              </div>
            </WriteOn>
          );
        }
        const p = spring({ frame: frame - delay, fps, config: { damping: 20, stiffness: 200 } });
        return (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 20,
              opacity: p,
              transform: `translateX(${interpolate(p, [0, 1], [-60, 0])}px)`,
            }}
          >
            <div style={{ width: 16, height: 16, borderRadius: 8, background: accent, flexShrink: 0 }} />
            <div style={{ fontSize: 40, fontWeight: 600, color: T.text }}>{b}</div>
          </div>
        );
      })}
    </div>
  );
};

/**
 * Dark style only: fetched illustration/video full-bleed behind a scrim.
 * Whiteboard draws the asset in the foreground instead (ScribeLayout).
 */
const SceneBackground: React.FC<{ scene: TimelineScene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { asset, assetKind, type, manim } = scene.visual;
  if (!asset || type === "diagram" || manim) return null;

  const zoom = interpolate(frame, [0, fps * 10], [1.05, 1.15], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      {assetKind === "video" ? (
        <OffthreadVideo
          src={staticFile(asset)}
          muted
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        <Img
          src={staticFile(asset)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${zoom})`,
          }}
        />
      )}
      <AbsoluteFill style={{ background: "rgba(9, 14, 26, 0.68)" }} />
    </AbsoluteFill>
  );
};

/**
 * Whiteboard: the "teacher draws a picture, then writes the point" layout.
 * Used when a scene has a drawable image (fetched illustration or diagram).
 */
const ScribeLayout: React.FC<{
  scene: TimelineScene;
  accent: string;
  durFrames: number;
  imgSrc: string;
}> = ({ scene, accent, durFrames, imgSrc }) => {
  const { width, height } = useVideoConfig();
  const T = THEMES.whiteboard;
  const portrait = height > width;
  const imgW = portrait ? width * 0.8 : Math.min(width * 0.46, 880);
  const imgH = portrait ? height * 0.34 : height * 0.5;
  const drawFrames = Math.max(1, Math.round(durFrames * 0.55));

  return (
    <div
      style={{
        display: "flex",
        flexDirection: portrait ? "column" : "row",
        alignItems: "center",
        justifyContent: "center",
        gap: portrait ? 30 : 70,
        maxWidth: "94%",
      }}
    >
      <ScribeReveal src={imgSrc} durFrames={durFrames} width={imgW} height={imgH} paper={T.paper} />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: portrait ? "center" : "flex-start",
          maxWidth: portrait ? "88%" : width * 0.38,
        }}
      >
        <Title text={scene.title || ""} accent={accent} style="whiteboard" small />
        {/* takeaway writes on AFTER the sketch is mostly drawn — explain, then state */}
        <WriteOn delayFrames={Math.min(drawFrames, 60)} durationFrames={20}>
          <div
            style={{
              fontFamily: T.bodyFont,
              fontSize: 52,
              color: T.text,
              lineHeight: 1.35,
              textAlign: portrait ? "center" : "left",
            }}
          >
            {scene.onScreenText}
          </div>
        </WriteOn>
        {(scene.bullets ?? []).length > 0 && (
          <div style={{ marginTop: 28 }}>
            <Bullets items={scene.bullets!} accent={accent} style="whiteboard" />
          </div>
        )}
        {scene.visual.credit && (
          <div style={{ fontFamily: T.bodyFont, fontSize: 22, color: T.sub, marginTop: 18 }}>
            {scene.visual.credit}
          </div>
        )}
      </div>
    </div>
  );
};

const SceneContent: React.FC<{
  scene: TimelineScene;
  style: SceneStyle;
  durFrames: number;
}> = ({ scene, style, durFrames }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const T = THEMES[style];
  const accent =
    (style === "whiteboard" ? WB_ACCENTS : ACCENTS)[scene.visual.type] || ACCENTS.bullet;
  const entrance = useEntrance(6);
  const emoji = scene.emoji || "";
  const bullets = scene.bullets ?? [];

  // Manim 2D-animation clip → play it full-frame; the animation IS the scene.
  // Captions still overlay from CaptionRenderer, so it stays synced + narrated.
  if (scene.visual.manim && scene.visual.asset) {
    return (
      <OffthreadVideo
        src={staticFile(scene.visual.asset)}
        style={{ width: "100%", height: "100%", objectFit: "contain" }}
      />
    );
  }

  // Whiteboard with a drawable image → the scribe sketch layout, regardless of
  // template. The drawing IS the explanation; text supports it.
  if (style === "whiteboard") {
    const imgSrc =
      scene.visual.image ??
      (scene.visual.assetKind === "image" ? scene.visual.asset : undefined);
    if (imgSrc) {
      return <ScribeLayout scene={scene} accent={accent} durFrames={durFrames} imgSrc={staticFile(imgSrc)} />;
    }
  }

  switch (scene.visual.type) {
    case "chart": {
      const labels = scene.chart?.labels ?? [];
      // negative values floored at 0 — school data is counts/percentages
      const values = (scene.chart?.values ?? []).map((v) => Math.max(0, v));
      const maxV = Math.max(...values, 1);
      return (
        <>
          <Title text={scene.title || scene.onScreenText} accent={accent} style={style} small />
          <div style={{ display: "flex", alignItems: "flex-end", gap: 48, height: 380 }}>
            {values.map((v, i) => {
              const grow = spring({
                frame: frame - (10 + i * 8),
                fps,
                config: { damping: 200 },
              });
              return (
                <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                  <div style={{ fontFamily: T.bodyFont, fontSize: 34, fontWeight: 800, color: T.ink, opacity: grow }}>
                    {scene.chart?.values[i]}
                  </div>
                  <div
                    style={{
                      width: 110,
                      height: Math.max(8, (v / maxV) * 280 * grow),
                      background: `linear-gradient(180deg, ${accent}, ${accent}88)`,
                      borderRadius: "10px 10px 0 0",
                    }}
                  />
                  <div style={{ fontFamily: T.bodyFont, fontSize: 28, fontWeight: 600, color: T.sub, maxWidth: 140, textAlign: "center" }}>
                    {labels[i]}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      );
    }
    case "steps": {
      const steps = (scene.bullets ?? []).slice(0, 5);
      const vertical = width < 1200 || steps.length > 4;
      return (
        <>
          <Title text={scene.title || scene.onScreenText} accent={accent} style={style} small />
          <div
            style={{
              display: "flex",
              flexDirection: vertical ? "column" : "row",
              alignItems: "center",
              gap: 24,
              maxWidth: "90%",
            }}
          >
            {steps.map((s, i) => {
              const p = spring({
                frame: frame - (10 + i * 12),
                fps,
                config: { damping: 20, stiffness: 200 },
              });
              return (
                <React.Fragment key={i}>
                  {i > 0 && (
                    <div style={{ fontSize: 44, color: accent, opacity: p, transform: vertical ? "rotate(90deg)" : "none" }}>
                      →
                    </div>
                  )}
                  <div
                    style={{
                      opacity: p,
                      transform: `scale(${0.8 + 0.2 * p})`,
                      display: "flex",
                      alignItems: "center",
                      gap: 14,
                      background: T.card,
                      border: `2px solid ${accent}`,
                      borderRadius: 16,
                      padding: "22px 28px",
                    }}
                  >
                    <div
                      style={{
                        width: 44,
                        height: 44,
                        borderRadius: 22,
                        background: accent,
                        color: style === "whiteboard" ? "#FFFFFF" : "#0F172A",
                        fontSize: 26,
                        fontWeight: 800,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      {i + 1}
                    </div>
                    <div style={{ fontFamily: T.bodyFont, fontSize: 32, fontWeight: 600, color: T.ink }}>{s}</div>
                  </div>
                </React.Fragment>
              );
            })}
          </div>
        </>
      );
    }
    case "formula": {
      let html: string | null = null;
      try {
        html = katex.renderToString(scene.formula || "", {
          displayMode: true,
          throwOnError: true,
        });
      } catch {
        html = null; // invalid LaTeX from LLM — fall through to plain text
      }
      return (
        <>
          <Title text={scene.title || ""} accent={accent} style={style} small />
          <div
            style={{
              ...entrance,
              background: T.codeBg,
              border: `2px solid ${accent}44`,
              borderRadius: 20,
              padding: "48px 64px",
              maxWidth: "88%",
            }}
          >
            {html ? (
              <div
                style={{ fontSize: 56, color: T.ink }}
                dangerouslySetInnerHTML={{ __html: html }}
              />
            ) : (
              <div style={{ fontSize: 44, fontFamily: "monospace", color: T.ink }}>
                {scene.formula || scene.onScreenText}
              </div>
            )}
          </div>
          <div style={{ ...entrance, fontFamily: T.bodyFont, fontSize: 32, color: T.sub, marginTop: 28, maxWidth: "78%", textAlign: "center" }}>
            {scene.onScreenText}
          </div>
        </>
      );
    }
    case "diagram": {
      if (!scene.visual.image) {
        // fetch failed upstream — render like an image/concept scene
        return (
          <>
            {emoji && <div style={{ fontSize: 150, marginBottom: 24 }}>{emoji}</div>}
            <Title text={scene.title || ""} accent={accent} style={style} small />
            <div style={{ ...entrance, fontFamily: T.bodyFont, fontSize: 44, fontWeight: 600, color: T.text, textAlign: "center", maxWidth: "78%" }}>
              {scene.onScreenText}
            </div>
          </>
        );
      }
      // dark style: diagram card with slow Ken Burns zoom
      const zoom = interpolate(frame, [0, fps * 8], [1, 1.06], {
        extrapolateRight: "clamp",
      });
      return (
        <>
          <Title text={scene.title || scene.onScreenText} accent={accent} style={style} small />
          <div
            style={{
              ...entrance,
              background: "#F8FAFC",
              borderRadius: 20,
              padding: 24,
              maxWidth: "80%",
              maxHeight: "58%",
              overflow: "hidden",
              position: "relative",
            }}
          >
            <Img
              src={staticFile(scene.visual.image)}
              style={{
                maxWidth: "100%",
                maxHeight: "100%",
                objectFit: "contain",
                transform: `scale(${zoom})`,
              }}
            />
          </div>
          {scene.visual.credit && (
            <div style={{ fontSize: 18, color: T.sub, marginTop: 12 }}>
              {scene.visual.credit}
            </div>
          )}
        </>
      );
    }
    case "big-number": {
      const pop = spring({ frame: frame - 6, fps, config: { damping: 8 } });
      return (
        <>
          <Title text={scene.title || ""} accent={accent} style={style} small />
          <div
            style={{
              fontFamily: T.titleFont,
              fontSize: 160,
              fontWeight: 900,
              color: accent,
              transform: `scale(${pop})`,
              textShadow: style === "dark" ? `0 0 60px ${accent}55` : "none",
            }}
          >
            {scene.onScreenText}
          </div>
          {emoji && <div style={{ ...entrance, fontSize: 72, marginTop: 24 }}>{emoji}</div>}
        </>
      );
    }
    case "code":
      return (
        <>
          <Title text={scene.title || ""} accent={accent} style={style} small />
          <div
            style={{
              ...entrance,
              fontFamily: "'Cascadia Code', 'Fira Code', monospace",
              fontSize: 36,
              color: T.codeText,
              background: T.codeBg,
              border: `2px solid ${accent}44`,
              borderRadius: 16,
              padding: "36px 48px",
              maxWidth: "85%",
              whiteSpace: "pre-wrap",
            }}
          >
            {scene.onScreenText}
          </div>
        </>
      );
    case "comparison": {
      const [left, right] = scene.bullets?.length
        ? [scene.bullets[0], scene.bullets[1] ?? ""]
        : [scene.onScreenText, ""];
      return (
        <>
          <Title text={scene.title || scene.onScreenText} accent={accent} style={style} small />
          <div style={{ display: "flex", gap: 40, maxWidth: "88%" }}>
            {[left, right].filter(Boolean).map((side, i) => {
              const p = spring({
                frame: frame - (10 + i * 10),
                fps,
                config: { damping: 200 },
              });
              return (
                <div
                  key={i}
                  style={{
                    opacity: p,
                    transform: `translateY(${interpolate(p, [0, 1], [30, 0])}px)`,
                    flex: 1,
                    background: i === 0 ? T.card : `${accent}22`,
                    border: `2px solid ${i === 0 ? T.border : accent}`,
                    borderRadius: 20,
                    padding: "40px 36px",
                    fontFamily: T.bodyFont,
                    fontSize: 38,
                    fontWeight: 600,
                    color: T.ink,
                    textAlign: "center",
                  }}
                >
                  {side}
                </div>
              );
            })}
          </div>
        </>
      );
    }
    case "image":
      return (
        <>
          {emoji && (
            <div
              style={{
                fontSize: 180,
                transform: `scale(${spring({ frame: frame - 4, fps, config: { damping: 12 } })})`,
                marginBottom: 32,
              }}
            >
              {emoji}
            </div>
          )}
          <Title text={scene.title || ""} accent={accent} style={style} small />
          <div
            style={{
              ...entrance,
              fontFamily: T.bodyFont,
              fontSize: 44,
              fontWeight: 600,
              color: T.text,
              textAlign: "center",
              maxWidth: "78%",
              lineHeight: 1.35,
            }}
          >
            {scene.onScreenText}
          </div>
        </>
      );
    default: // bullet
      return (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            {emoji && <span style={{ fontSize: 56 }}>{emoji}</span>}
            <Title text={scene.title || ""} accent={accent} style={style} />
          </div>
          {bullets.length > 0 ? (
            <Bullets items={bullets} accent={accent} style={style} />
          ) : style === "whiteboard" ? (
            <WriteOn delayFrames={10} durationFrames={22}>
              <div
                style={{
                  fontFamily: T.bodyFont,
                  fontSize: 54,
                  color: T.text,
                  textAlign: "center",
                  maxWidth: "78%",
                  lineHeight: 1.4,
                  margin: "0 auto",
                }}
              >
                {scene.onScreenText}
              </div>
            </WriteOn>
          ) : (
            <div
              style={{
                ...entrance,
                fontSize: 46,
                fontWeight: 600,
                color: T.text,
                textAlign: "center",
                maxWidth: "78%",
                lineHeight: 1.35,
              }}
            >
              {scene.onScreenText}
            </div>
          )}
        </>
      );
  }
};

export const SceneRenderer: React.FC<{
  scenes: TimelineScene[];
  style?: SceneStyle;
}> = ({ scenes, style = "dark" }) => {
  const { fps, durationInFrames } = useVideoConfig();

  return (
    <AbsoluteFill>
      {scenes.map((scene, i) => {
        // first scene covers any leading silence from frame 0
        const from = i === 0 ? 0 : Math.round(scene.start * fps);
        const next = scenes[i + 1] ?? null;
        // hold each scene until the NEXT one starts (sentence gaps = narration
        // pauses — ending at scene.end left BLANK frames during every pause);
        // last scene extends to the end of the audio
        const until = next ? Math.round(next.start * fps) : durationInFrames;
        const dur = Math.max(1, until - from);
        return (
          <Sequence key={scene.idx} from={from} durationInFrames={dur}>
            {style === "dark" && <SceneBackground scene={scene} />}
            <AbsoluteFill
              style={{
                justifyContent: "center",
                alignItems: "center",
                padding: "60px 80px",
                paddingBottom: 220, // keep clear of captions
              }}
            >
              <SceneContent scene={scene} style={style} durFrames={dur} />
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
