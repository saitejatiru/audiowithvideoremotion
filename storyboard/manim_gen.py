"""storyboard/manim_gen.py — render Manim 2D animations for 'animation' scenes.

For each scene the storyboard marked visual.type == "animation", the LLM writes
a Manim scene from animation_brief, we render it to mp4 (render-in-the-loop:
on failure, feed the error back and retry), and attach the clip as the scene's
video asset. The Remotion renderer then plays it full-frame for that sentence.

Fail-soft everywhere: no manim CLI, LLM error, or 3 failed renders → the scene
downgrades to 'bullet' and still renders. Manim is a bonus, never a hard dep.
Only 'animation' scenes hit this (a handful per video), so render time stays
bounded — Manim is CPU and slow.
"""
import glob
import logging
import os
import re
import shutil
import subprocess

from storyboard.client import call_llm

logger = logging.getLogger(__name__)

_SYS = """You write Manim Community Edition (v0.18) Python for a 2D educational animation.
RULES (strict):
- Output ONLY python code. No markdown fences, no prose.
- Exactly one class: class GenScene(Scene): with construct(self).
- Use ONLY: Text, Circle, Square, Rectangle, Arrow, Line, Dot, VGroup, colors, and
  FadeIn/Write/Create/Transform/GrowArrow/self.play/self.wait. NO MathTex/Tex/LaTeX.
- Frame is ~14x8 units, center ORIGIN. Keep everything on screen, no overlap.
- 6-12 seconds, explain the concept step by step with short Text labels."""

_ATTEMPTS = 3
_TIMEOUT = 300  # seconds per render
# -ql = 480p15 (low quality) renders ~4x faster than -qm on Colab's CPU. A
# finished low-res animation beats a medium-res one that times out to a bullet.
_QUALITY = "-ql"


def _gen_code(brief: str, err: str | None, prev: str | None) -> str:
    user = f"Animate this concept clearly: {brief}"
    if err:
        user = (
            f"Your Manim code failed to render:\n{err}\n\nCODE:\n{prev}\n\n"
            "Fix it. Same rules. Output only corrected python."
        )
    out = call_llm(
        [{"role": "system", "content": _SYS}, {"role": "user", "content": user}]
    )
    return re.sub(r"^```(python)?|```$", "", out or "", flags=re.M).strip()


def render_manim_scenes(timeline: dict, out_dir: str) -> dict:
    """Render every 'animation' scene to a clip; downgrade any that can't be made."""
    has_manim = shutil.which("manim") is not None
    for scene in timeline.get("scenes", []):
        v = scene.get("visual", {})
        if v.get("type") != "animation":
            continue

        idx = scene.get("idx", 0)
        brief = (scene.get("animation_brief") or scene.get("title") or v.get("query") or "").strip()

        if not has_manim or not brief:
            logger.info("animation scene %s: no manim/brief — downgrading to bullet", idx)
            v["type"] = "bullet"
            continue

        code = err = None
        rendered = None
        for attempt in range(_ATTEMPTS):
            try:
                code = _gen_code(brief, err, code)
            except Exception as e:
                logger.warning("animation scene %s: LLM failed: %s", idx, e)
                break
            src = code if code.lstrip().startswith("from manim") else "from manim import *\n\n" + code
            script = os.path.join(out_dir, f"manim_{idx}.py")
            with open(script, "w", encoding="utf-8") as f:
                f.write(src)
            try:
                p = subprocess.run(
                    ["manim", _QUALITY, "--format=mp4", "--media_dir", out_dir, script, "GenScene"],
                    capture_output=True, text=True, timeout=_TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                logger.warning("animation scene %s: render timed out", idx)
                break
            if p.returncode == 0:
                clips = sorted(glob.glob(os.path.join(out_dir, "videos", "**", "GenScene.mp4"), recursive=True))
                if clips:
                    rendered = clips[-1]
                    break
            err = (p.stderr or "")[-1200:]
            logger.warning("animation scene %s: attempt %d failed", idx, attempt + 1)

        if rendered:
            dest = f"manim-{idx}.mp4"
            shutil.copy2(rendered, os.path.join(out_dir, dest))
            v["asset"] = dest
            v["assetKind"] = "video"
            v["manim"] = True
            logger.info("animation scene %s: rendered Manim clip", idx)
        else:
            logger.warning("animation scene %s: unrenderable — downgrading to bullet", idx)
            v["type"] = "bullet"

    return timeline
