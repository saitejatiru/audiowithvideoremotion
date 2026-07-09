"""Tier 1 tests — rich scene schema downgrades + Wikimedia diagram fetcher."""
from unittest.mock import MagicMock, patch

from storyboard.assets import fetch_diagrams
from storyboard.schema import LLMSceneItem


class TestSchemaDowngrades:
    def test_chart_valid(self):
        item = LLMSceneItem(
            on_screen_text="t", visual_type="chart", visual_query="q",
            chart_labels=["A", "B"], chart_values=["45%", "1,000"],
        )
        assert item.visual_type == "chart"
        assert item.chart_values == [45.0, 1000.0]

    def test_chart_too_few_points_downgrades(self):
        item = LLMSceneItem(
            on_screen_text="t", visual_type="chart", visual_query="q",
            chart_labels=["A"], chart_values=[1.0],
        )
        assert item.visual_type == "bullet"

    def test_chart_mismatched_lengths_truncate(self):
        item = LLMSceneItem(
            on_screen_text="t", visual_type="chart", visual_query="q",
            chart_labels=["A", "B", "C"], chart_values=[1, 2],
        )
        assert item.chart_labels == ["A", "B"]
        assert item.chart_values == [1.0, 2.0]

    def test_chart_non_numeric_values_dropped(self):
        item = LLMSceneItem(
            on_screen_text="t", visual_type="chart", visual_query="q",
            chart_labels=["A", "B"], chart_values=["12", "n/a"],
        )
        # only one usable value -> downgrade
        assert item.visual_type == "bullet"

    def test_steps_needs_two(self):
        item = LLMSceneItem(
            on_screen_text="t", visual_type="steps", visual_query="q",
            bullets=["only one"],
        )
        assert item.visual_type == "bullet"

    def test_empty_formula_downgrades(self):
        item = LLMSceneItem(
            on_screen_text="t", visual_type="formula", visual_query="q", formula="  ",
        )
        assert item.visual_type == "bullet"

    def test_old_output_still_validates(self):
        item = LLMSceneItem(on_screen_text="t", visual_type="bullet", visual_query="q")
        assert item.chart_labels == [] and item.formula == ""


def _timeline_with_diagram():
    return {
        "scenes": [
            {"idx": 0, "visual": {"type": "diagram", "query": "human heart labeled diagram"}},
            {"idx": 1, "visual": {"type": "bullet", "query": "x"}},
        ]
    }


class TestFetchDiagrams:
    @patch("storyboard.assets.requests.get")
    def test_success_sets_image_and_credit(self, mock_get, tmp_path):
        search = MagicMock(status_code=200)
        search.json.return_value = {
            "query": {"pages": {"1": {"imageinfo": [{
                "thumburl": "https://upload.wikimedia.org/x/heart.png",
                "extmetadata": {
                    "Artist": {"value": "<a href='x'>Jane Doe</a>"},
                    "LicenseShortName": {"value": "CC BY-SA 4.0"},
                },
            }]}}}
        }
        download = MagicMock(status_code=200, content=b"\x89PNG fake")
        mock_get.side_effect = [search, download]

        t = fetch_diagrams(_timeline_with_diagram(), str(tmp_path))

        v = t["scenes"][0]["visual"]
        assert v["type"] == "diagram"
        assert v["image"] == "diagram-0.png"
        assert "Jane Doe" in v["credit"] and "CC BY-SA" in v["credit"]
        assert (tmp_path / "diagram-0.png").read_bytes() == b"\x89PNG fake"
        # non-diagram scene untouched
        assert t["scenes"][1]["visual"] == {"type": "bullet", "query": "x"}

    @patch("storyboard.assets.requests.get")
    def test_no_result_downgrades(self, mock_get, tmp_path):
        empty = MagicMock(status_code=200)
        empty.json.return_value = {"query": {"pages": {}}}
        mock_get.return_value = empty

        t = fetch_diagrams(_timeline_with_diagram(), str(tmp_path))
        assert t["scenes"][0]["visual"]["type"] == "image"

    @patch("storyboard.assets.requests.get", side_effect=Exception("offline"))
    def test_network_error_downgrades(self, mock_get, tmp_path):
        t = fetch_diagrams(_timeline_with_diagram(), str(tmp_path))
        assert t["scenes"][0]["visual"]["type"] == "image"

    @patch("storyboard.assets.requests.get")
    def test_download_failure_downgrades(self, mock_get, tmp_path):
        search = MagicMock(status_code=200)
        search.json.return_value = {
            "query": {"pages": {"1": {"imageinfo": [{
                "thumburl": "https://upload.wikimedia.org/x/h.png", "extmetadata": {},
            }]}}}
        }
        bad = MagicMock()
        bad.raise_for_status.side_effect = Exception("404")
        mock_get.side_effect = [search, bad]

        t = fetch_diagrams(_timeline_with_diagram(), str(tmp_path))
        assert t["scenes"][0]["visual"]["type"] == "image"
        assert "image" != t["scenes"][0]["visual"].get("image", "")  # no file recorded
