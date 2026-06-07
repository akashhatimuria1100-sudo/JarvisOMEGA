"""
tools/image_tools.py — JARVIS OMEGA V3 Image Generation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES:
  ✅ Returns local path for GUI to display inline
  ✅ Returns URL as fallback if download fails
  ✅ GUI will render images in the output panel
"""

import re
import time
import logging
import requests
from pathlib import Path

logger = logging.getLogger("JARVIS.IMAGE")
_BASE   = Path(__file__).resolve().parent.parent
IMG_DIR = _BASE / "data/images"
IMG_DIR.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "JARVIS-OMEGA/3.0"}


def generate_image(prompt: str, style: str = "photorealistic",
                   width: int = 1024, height: int = 1024) -> dict:
    """Generate image using Pollinations.ai (free, no API key)."""
    if not prompt.strip():
        return {"type": "error", "error": "Empty prompt"}

    url = _build_url(prompt, style, width, height)
    try:
        logger.info("Generating image: %s", prompt[:60])
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        if "image" in ct:
            save_path = IMG_DIR / f"{_slug(prompt)}_{int(time.time())}.png"
            save_path.write_bytes(resp.content)
            logger.info("Image saved: %s", save_path)
            return {
                "type":    "image",
                "url":     url,
                "path":    str(save_path),
                "prompt":  prompt,
                "source":  "pollinations.ai",
            }
        return {
            "type":    "image",
            "url":     url,
            "path":    "",
            "prompt":  prompt,
            "message": "Image available at URL (could not download). View it in browser.",
        }
    except requests.Timeout:
        return {"type": "image", "url": url, "path": "",
                "prompt": prompt, "message": "Generation timed out. Use this URL: " + url}
    except Exception as exc:
        logger.warning("Image gen error: %s", exc)
        return {"type": "image", "url": url, "path": "",
                "prompt": prompt, "message": f"Use this URL to view: {url}"}


def _build_url(prompt: str, style: str, width: int, height: int) -> str:
    style_map = {
        "photorealistic": "photorealistic, hyperrealistic, 8K, detailed",
        "anime":          "anime, manga, vibrant, Studio Ghibli",
        "3d":             "3D render, octane render, cinematic lighting",
        "concept":        "concept art, digital painting, artstation",
        "dark":           "dark theme, noir, dramatic, cinematic",
        "minimal":        "minimalist, clean, simple, white background",
    }
    style_str = style_map.get(style, style)
    full      = f"{prompt}, {style_str}"
    encoded   = requests.utils.quote(full)
    return f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true&seed={int(time.time())}"


def _slug(text: str, max_len: int = 35) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"\s+", "_", s)[:max_len]
    return s or "image"
