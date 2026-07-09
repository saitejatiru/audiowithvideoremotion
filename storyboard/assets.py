"""storyboard/assets.py — fetch labeled diagrams from Wikimedia Commons.

For every scene with visual.type == "diagram", searches Commons for the
scene's visual_query, downloads a 1280px thumbnail into out_dir, and records
the filename + license credit on the scene.

Edge cases (all non-fatal — a diagram scene NEVER breaks the pipeline):
  - no search result / network error / timeout / bad download
      -> scene downgrades to visual.type "image" (emoji template renders)
  - missing license metadata -> credit falls back to "Wikimedia Commons"
Diagrams are correctness-critical for board-exam content: Commons hosts
textbook-grade labeled diagrams; we never generate diagrams with AI.
"""
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

_API = "https://commons.wikimedia.org/w/api.php"
_HEADERS = {"User-Agent": "explainer-video-pipeline/1.0 (educational; contact via repo)"}
_TIMEOUT = 8.0


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _search_commons(query: str) -> dict | None:
    """Return {"url", "credit"} for the top Commons image match, or None."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap|drawing {query}",
        "gsrnamespace": 6,  # File: namespace
        "gsrlimit": 1,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1280,  # thumbnail: bounded size, SVGs rasterized to PNG
    }
    resp = requests.get(_API, params=params, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", {})
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        meta = info.get("extmetadata") or {}
        artist = _strip_html((meta.get("Artist") or {}).get("value", ""))
        license_ = _strip_html((meta.get("LicenseShortName") or {}).get("value", ""))
        credit = " · ".join(p for p in (artist[:60], license_) if p) or "Wikimedia Commons"
        return {"url": url, "credit": credit}
    return None


def fetch_diagrams(timeline: dict, out_dir: str) -> dict:
    """Download a diagram for each 'diagram' scene; downgrade on any failure.

    Mutates and returns the timeline. Files land in out_dir as
    diagram-<idx>.<ext>; scene.visual gains "image" (bare filename, resolved
    by render_bridge into video/public/) and "credit".
    """
    for scene in timeline.get("scenes", []):
        visual = scene.get("visual", {})
        if visual.get("type") != "diagram":
            continue
        query = (visual.get("query") or "").strip()
        try:
            hit = _search_commons(query) if query else None
        except Exception as e:
            logger.warning("Commons search failed for %r: %s", query, e)
            hit = None
        if hit is None:
            logger.info("No diagram for %r — downgrading scene %s to image", query, scene.get("idx"))
            visual["type"] = "image"
            continue

        ext = os.path.splitext(hit["url"].split("?")[0])[1] or ".png"
        fname = f"diagram-{scene.get('idx', 0)}{ext}"
        try:
            resp = requests.get(hit["url"], headers=_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
            with open(os.path.join(out_dir, fname), "wb") as f:
                f.write(resp.content)
        except Exception as e:
            logger.warning("Diagram download failed for %r: %s", query, e)
            visual["type"] = "image"
            continue

        visual["image"] = fname
        visual["credit"] = hit["credit"]
    return timeline
