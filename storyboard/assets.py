"""storyboard/assets.py — fetch real visuals per scene.

Two sources, both free, both allow downloading for local render:
  - Wikimedia Commons (no key) — labeled science diagrams for 'diagram' scenes.
    Correctness-critical; we NEVER AI-generate a diagram.
  - Pixabay (free key, PIXABAY_API_KEY) — flat vector illustrations (and,
    opt-in via PIXABAY_VIDEO=1, stock video b-roll) for every other scene.

Design rule: assets are decoration, never a dependency. Every failure path
(no key, no result, network error, bad download) leaves the scene renderable
by its CSS template. So visuals degrade smoothly and the pipeline never breaks
— and they do NOT depend on the LLM producing rich scenes.

Fields written onto scene["visual"]:
  diagram scenes:  image=<file>, credit=<attribution>   (shown as a card)
  other scenes:    asset=<file>, assetKind=image|video, credit=<attribution>
                                                          (shown as background)
"""
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
_PIXABAY_IMG = "https://pixabay.com/api/"
_PIXABAY_VID = "https://pixabay.com/api/videos/"
_HEADERS = {"User-Agent": "explainer-video-pipeline/1.0 (educational; contact via repo)"}
_TIMEOUT = 10.0


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _download_to(url: str, path: str) -> bool:
    """Download url to path. Returns True on success, False on any error."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        with open(path, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        logger.warning("Download failed for %s: %s", url, e)
        return False


# ── Wikimedia Commons (diagrams) ─────────────────────────────────────────

def _search_commons(query: str) -> dict | None:
    """Return {"url", "credit"} for the top Commons image match, or None."""
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap|drawing {query}", "gsrnamespace": 6,
        "gsrlimit": 1, "prop": "imageinfo", "iiprop": "url|extmetadata",
        "iiurlwidth": 1280,
    }
    resp = requests.get(_COMMONS_API, params=params, headers=_HEADERS, timeout=_TIMEOUT)
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


# ── Pixabay (illustrations + video) ──────────────────────────────────────

def _search_pixabay_image(query: str, key: str) -> dict | None:
    """Prefer flat illustration (matches textbook explainer look), else photo."""
    for image_type in ("illustration", "photo"):
        try:
            resp = requests.get(_PIXABAY_IMG, params={
                "key": key, "q": query, "image_type": image_type,
                "safesearch": "true", "per_page": 3, "order": "popular",
            }, headers=_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            if hits:
                h = hits[0]
                return {
                    "url": h.get("largeImageURL") or h.get("webformatURL"),
                    "credit": f"Pixabay · {h.get('user', '')}".strip(" ·"),
                }
        except Exception as e:
            logger.warning("Pixabay image search failed for %r (%s): %s", query, image_type, e)
    return None


def _search_pixabay_video(query: str, key: str) -> dict | None:
    try:
        resp = requests.get(_PIXABAY_VID, params={
            "key": key, "q": query, "safesearch": "true",
            "per_page": 3, "order": "popular",
        }, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        if hits:
            v = hits[0].get("videos", {})
            stream = v.get("medium") or v.get("small") or v.get("large") or v.get("tiny")
            if stream and stream.get("url"):
                return {"url": stream["url"], "credit": f"Pixabay · {hits[0].get('user', '')}".strip(" ·")}
    except Exception as e:
        logger.warning("Pixabay video search failed for %r: %s", query, e)
    return None


# ── Entry point ──────────────────────────────────────────────────────────

def fetch_scene_assets(timeline: dict, out_dir: str) -> dict:
    """Attach a real visual to each scene where possible. Mutates + returns.

    diagram scenes  -> Wikimedia Commons labeled diagram (visual.image)
    every other type -> Pixabay illustration, or video if PIXABAY_VIDEO=1
                        (visual.asset + visual.assetKind)
    All failures are silent no-ops: the scene still renders via its template.
    """
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    want_video = os.environ.get("PIXABAY_VIDEO", "").strip() not in ("", "0", "false")
    if not key:
        logger.warning(
            "PIXABAY_API_KEY not set — concept scenes will use CSS templates only "
            "(no illustrations/video). Get a free key at https://pixabay.com/api/docs/"
        )

    for scene in timeline.get("scenes", []):
        visual = scene.get("visual", {})
        query = (visual.get("query") or scene.get("title") or "").strip()
        idx = scene.get("idx", 0)
        if not query:
            continue

        if visual.get("type") == "diagram":
            try:
                hit = _search_commons(query)
            except Exception as e:
                logger.warning("Commons search failed for %r: %s", query, e)
                hit = None
            if hit and hit["url"]:
                ext = os.path.splitext(hit["url"].split("?")[0])[1] or ".png"
                fname = f"diagram-{idx}{ext}"
                if _download_to(hit["url"], os.path.join(out_dir, fname)):
                    visual["image"] = fname
                    visual["credit"] = hit["credit"]
                    continue
            # no diagram → fall through to a Pixabay illustration instead of
            # dropping to plain text (better than nothing for the concept)
            logger.info("No Commons diagram for %r — trying Pixabay", query)

        if not key:
            continue

        hit = None
        kind = "image"
        if want_video:
            hit = _search_pixabay_video(query, key)
            kind = "video"
        if hit is None:
            hit = _search_pixabay_image(query, key)
            kind = "image"
        if hit is None or not hit.get("url"):
            continue

        ext = os.path.splitext(hit["url"].split("?")[0])[1] or (".mp4" if kind == "video" else ".jpg")
        fname = f"asset-{idx}{ext}"
        if _download_to(hit["url"], os.path.join(out_dir, fname)):
            visual["asset"] = fname
            visual["assetKind"] = kind
            visual["credit"] = hit["credit"]

    return timeline


# Back-compat: orchestrator/tests may still import fetch_diagrams.
def fetch_diagrams(timeline: dict, out_dir: str) -> dict:
    """Diagram-only subset of fetch_scene_assets (Wikimedia, no Pixabay)."""
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
            visual["type"] = "image"
            continue
        ext = os.path.splitext(hit["url"].split("?")[0])[1] or ".png"
        fname = f"diagram-{scene.get('idx', 0)}{ext}"
        if _download_to(hit["url"], os.path.join(out_dir, fname)):
            visual["image"] = fname
            visual["credit"] = hit["credit"]
        else:
            visual["type"] = "image"
    return timeline
