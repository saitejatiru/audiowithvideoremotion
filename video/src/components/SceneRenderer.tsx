/**
 * SceneRenderer — animated educational scene templates.
 *
 * Each scene renders inside its own <Sequence> so entrance springs restart
 * per scene. Templates by visual.type: bullet (staggered reveals), image
 * (big emoji + takeaway), code (mono card), big-number (giant stat pop),
 * comparison (two panels). Scenes switch at sentence boundaries (STORY-03).
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
import type { TimelineScene } from "../types";

/**
 * Background layer: a real Pixabay illustration or stock video behind the
 * scene, with a dark scrim so the animated text stays readable. Absent asset
 * → transparent (the animated gradient/template shows through). Diagram scenes
 * skip this — they render the diagram as a foreground card instead.
 */
const SceneBackground: React.FC<{ scene: TimelineScene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { asset, assetKind, type } = scene.visual;
  if (!asset || type === "diagram") return null;

  // slow Ken Burns on stills so a static illustration still feels alive
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
      {/* scrim: darken so white text keeps contrast over any image */}
      <AbsoluteFill style={{ background: "rgba(9, 14, 26, 0.68)" }} />
    </AbsoluteFill>
  );
};

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

/** Spring entrance: slide up + fade. */
const useEntrance = (delayFrames = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - delayFrames, fps, config: { damping: 200 } });
  return {
    opacity: p,
    transform: `translateY(${interpolate(p, [0, 1], [40, 0])}px)`,
  };
};

const Title: React.FC<{ text: string; accent: string; small?: boolean }> = ({
  text,
  accent,
  small,
}) => {
  const style = useEntrance(0);
  if (!text) return null;
  return (
    <div
      style={{
        ...style,
        fontSize: small ? 44 : 64,
        fontWeight: 800,
        color: "#F8FAFC",
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

const Bullets: React.FC<{ items: string[]; accent: string }> = ({ items, accent }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28, maxWidth: "80%" }}>
      {items.map((b, i) => {
        const delay = 12 + i * 14; // stagger: each bullet ~0.5s after the last
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
            <div
              style={{
                width: 16,
                height: 16,
                borderRadius: 8,
                background: accent,
                flexShrink: 0,
              }}
            />
            <div style={{ fontSize: 40, fontWeight: 600, color: "#E2E8F0" }}>{b}</div>
          </div>
        );
      })}
    </div>
  );
};

const SceneContent: React.FC<{ scene: TimelineScene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const accent = ACCENTS[scene.visual.type] || ACCENTS.bullet;
  const entrance = useEntrance(6);
  const emoji = scene.emoji || "";
  const bullets = scene.bullets ?? [];

  switch (scene.visual.type) {
    case "chart": {
      const labels = scene.chart?.labels ?? [];
      // negative values floored at 0 — school data is counts/percentages
      const values = (scene.chart?.values ?? []).map((v) => Math.max(0, v));
      const maxV = Math.max(...values, 1);
      return (
        <>
          <Title text={scene.title || scene.onScreenText} accent={accent} small />
          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              gap: 48,
              height: 380,
            }}
          >
            {values.map((v, i) => {
              const grow = spring({
                frame: frame - (10 + i * 8),
                fps,
                config: { damping: 200 },
              });
              return (
                <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                  <div style={{ fontSize: 34, fontWeight: 800, color: "#F8FAFC", opacity: grow }}>
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
                  <div style={{ fontSize: 28, fontWeight: 600, color: "#CBD5E1", maxWidth: 140, textAlign: "center" }}>
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
          <Title text={scene.title || scene.onScreenText} accent={accent} small />
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
                      background: "#1E293B",
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
                        color: "#0F172A",
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
                    <div style={{ fontSize: 32, fontWeight: 600, color: "#F1F5F9" }}>{s}</div>
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
          <Title text={scene.title || ""} accent={accent} small />
          <div
            style={{
              ...entrance,
              background: "#0B1220",
              border: `2px solid ${accent}44`,
              borderRadius: 20,
              padding: "48px 64px",
              maxWidth: "88%",
            }}
          >
            {html ? (
              <div
                style={{ fontSize: 56, color: "#F8FAFC" }}
                dangerouslySetInnerHTML={{ __html: html }}
              />
            ) : (
              <div style={{ fontSize: 44, fontFamily: "monospace", color: "#F8FAFC" }}>
                {scene.formula || scene.onScreenText}
              </div>
            )}
          </div>
          <div style={{ ...entrance, fontSize: 32, color: "#94A3B8", marginTop: 28, maxWidth: "78%", textAlign: "center" }}>
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
            <Title text={scene.title || ""} accent={accent} small />
            <div style={{ ...entrance, fontSize: 44, fontWeight: 600, color: "#E2E8F0", textAlign: "center", maxWidth: "78%" }}>
              {scene.onScreenText}
            </div>
          </>
        );
      }
      // slow Ken Burns zoom while the narration explains the diagram
      const zoom = interpolate(frame, [0, fps * 8], [1, 1.06], {
        extrapolateRight: "clamp",
      });
      return (
        <>
          <Title text={scene.title || scene.onScreenText} accent={accent} small />
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
            <div style={{ fontSize: 18, color: "#64748B", marginTop: 12 }}>
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
          <Title text={scene.title || ""} accent={accent} small />
          <div
            style={{
              fontSize: 160,
              fontWeight: 900,
              color: accent,
              transform: `scale(${pop})`,
              textShadow: `0 0 60px ${accent}55`,
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
          <Title text={scene.title || ""} accent={accent} small />
          <div
            style={{
              ...entrance,
              fontFamily: "'Cascadia Code', 'Fira Code', monospace",
              fontSize: 36,
              color: "#A5F3FC",
              background: "#0B1220",
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
          <Title text={scene.title || scene.onScreenText} accent={accent} small />
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
                    background: i === 0 ? "#1E293B" : `${accent}22`,
                    border: `2px solid ${i === 0 ? "#334155" : accent}`,
                    borderRadius: 20,
                    padding: "40px 36px",
                    fontSize: 38,
                    fontWeight: 600,
                    color: "#F1F5F9",
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
          <Title text={scene.title || ""} accent={accent} small />
          <div
            style={{
              ...entrance,
              fontSize: 44,
              fontWeight: 600,
              color: "#E2E8F0",
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
            <Title text={scene.title || ""} accent={accent} />
          </div>
          {bullets.length > 0 ? (
            <Bullets items={bullets} accent={accent} />
          ) : (
            <div
              style={{
                ...entrance,
                fontSize: 46,
                fontWeight: 600,
                color: "#E2E8F0",
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

export const SceneRenderer: React.FC<{ scenes: TimelineScene[] }> = ({ scenes }) => {
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
            <SceneBackground scene={scene} />
            <AbsoluteFill
              style={{
                justifyContent: "center",
                alignItems: "center",
                padding: "60px 80px",
                paddingBottom: 220, // keep clear of captions
              }}
            >
              <SceneContent scene={scene} />
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
