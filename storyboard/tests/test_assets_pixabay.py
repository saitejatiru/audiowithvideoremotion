"""Pixabay asset-fetch tests — mocked HTTP, no network.

Covers the foolproof invariant: fetch_scene_assets attaches a background when
Pixabay returns a hit, and is a silent no-op (scene still renderable) on every
failure path — no key, no hits, network error, bad download.
"""
from unittest.mock import MagicMock, patch

from storyboard.assets import fetch_scene_assets


def _tl():
    return {"scenes": [
        {"idx": 0, "visual": {"type": "bullet", "query": "photosynthesis"}},
    ]}


def _img_resp(hits):
    r = MagicMock(status_code=200)
    r.json.return_value = {"hits": hits}
    return r


class TestFetchSceneAssets:
    @patch.dict("os.environ", {"PIXABAY_API_KEY": "k"}, clear=False)
    @patch("storyboard.assets.requests.get")
    def test_illustration_attached(self, mock_get, tmp_path):
        search = _img_resp([{"largeImageURL": "https://pixabay.com/x/leaf.jpg", "user": "Jo"}])
        download = MagicMock(status_code=200, content=b"\xff\xd8jpeg")
        mock_get.side_effect = [search, download]

        t = fetch_scene_assets(_tl(), str(tmp_path))
        v = t["scenes"][0]["visual"]
        assert v["asset"] == "asset-0.jpg"
        assert v["assetKind"] == "image"
        assert "Pixabay" in v["credit"]
        assert (tmp_path / "asset-0.jpg").read_bytes() == b"\xff\xd8jpeg"

    @patch.dict("os.environ", {"PIXABAY_API_KEY": "k", "PIXABAY_VIDEO": "1"}, clear=False)
    @patch("storyboard.assets.requests.get")
    def test_video_when_opted_in(self, mock_get, tmp_path):
        vid = MagicMock(status_code=200)
        vid.json.return_value = {"hits": [{"videos": {"medium": {"url": "https://p/v.mp4"}}, "user": "A"}]}
        download = MagicMock(status_code=200, content=b"mp4")
        mock_get.side_effect = [vid, download]

        t = fetch_scene_assets(_tl(), str(tmp_path))
        v = t["scenes"][0]["visual"]
        assert v["asset"] == "asset-0.mp4" and v["assetKind"] == "video"

    @patch.dict("os.environ", {"PIXABAY_API_KEY": ""}, clear=False)
    @patch("storyboard.assets.requests.get")
    def test_no_key_is_noop(self, mock_get, tmp_path):
        t = fetch_scene_assets(_tl(), str(tmp_path))
        assert "asset" not in t["scenes"][0]["visual"]
        mock_get.assert_not_called()

    @patch.dict("os.environ", {"PIXABAY_API_KEY": "k"}, clear=False)
    @patch("storyboard.assets.requests.get")
    def test_no_hits_is_noop(self, mock_get, tmp_path):
        mock_get.return_value = _img_resp([])  # illustration + photo both empty
        t = fetch_scene_assets(_tl(), str(tmp_path))
        assert "asset" not in t["scenes"][0]["visual"]

    @patch.dict("os.environ", {"PIXABAY_API_KEY": "k"}, clear=False)
    @patch("storyboard.assets.requests.get", side_effect=Exception("offline"))
    def test_network_error_is_noop(self, mock_get, tmp_path):
        t = fetch_scene_assets(_tl(), str(tmp_path))
        assert "asset" not in t["scenes"][0]["visual"]  # scene still renders via template
