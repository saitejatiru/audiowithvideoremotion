"""Manim scene rendering — fail-soft invariants (no real manim/LLM calls)."""
from unittest.mock import patch

from storyboard.manim_gen import render_manim_scenes
from storyboard.schema import LLMSceneItem


def _tl():
    return {"scenes": [
        {"idx": 0, "visual": {"type": "animation", "query": "projectile"}, "animation_brief": "a ball flies in an arc"},
        {"idx": 1, "visual": {"type": "bullet", "query": "x"}},
    ]}


class TestSchemaAnimation:
    def test_animation_needs_brief(self):
        item = LLMSceneItem(on_screen_text="t", visual_type="animation", visual_query="q")
        assert item.visual_type == "bullet"  # empty brief → downgrade

    def test_animation_with_brief_kept(self):
        item = LLMSceneItem(
            on_screen_text="t", visual_type="animation", visual_query="q",
            animation_brief="a block accelerates under a force",
        )
        assert item.visual_type == "animation"


class TestRenderManimScenes:
    @patch("storyboard.manim_gen.shutil.which", return_value=None)
    def test_no_manim_downgrades(self, _which):
        t = render_manim_scenes(_tl(), "/tmp")
        assert t["scenes"][0]["visual"]["type"] == "bullet"  # animation → bullet
        assert t["scenes"][1]["visual"]["type"] == "bullet"  # untouched

    @patch("storyboard.manim_gen.shutil.which", return_value="/usr/bin/manim")
    @patch("storyboard.manim_gen.call_llm", side_effect=Exception("llm down"))
    def test_llm_failure_downgrades(self, _llm, _which):
        t = render_manim_scenes(_tl(), "/tmp")
        assert t["scenes"][0]["visual"]["type"] == "bullet"

    @patch("storyboard.manim_gen.shutil.which", return_value="/usr/bin/manim")
    @patch("storyboard.manim_gen.call_llm", return_value="class GenScene(Scene):\n    def construct(self): pass")
    @patch("storyboard.manim_gen.subprocess.run")
    def test_render_failure_downgrades(self, mock_run, _llm, _which, tmp_path):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "manim error"
        t = render_manim_scenes(_tl(), str(tmp_path))
        assert t["scenes"][0]["visual"]["type"] == "bullet"  # 3 fails → bullet
        assert "asset" not in t["scenes"][0]["visual"]
