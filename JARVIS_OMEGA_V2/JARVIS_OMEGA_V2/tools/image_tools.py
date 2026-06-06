"""
tools/image_tools.py — FREE Image Generation
Uses Pollinations.ai (completely free, no API key needed)
+ Stability AI / OpenAI if keys are configured
"""

import re
import time
import logging
import requests
from pathlib import Path

logger = logging.getLogger("JARVIS.IMAGE")

_BASE = Path(__file__).resolve().parent.parent
IMG_DIR = _BASE / "data/images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "JARVIS-OMEGA/3.0"}


def generate_image(prompt: str, style: str = "photorealistic",
                   width: int = 1024, height: int = 1024) -> dict:
    """Generate an image — tries Pollinations.ai (free) first."""
    if not prompt.strip():
        return {"type": "error", "error": "Empty prompt"}

    # Try Pollinations (free, no API key)
    result = _pollinations(prompt, style, width, height)
    if result.get("type") == "image" and result.get("path"):
        return result

    # Fallback message
    logger.warning("Image generation failed — all services unavailable")
    return {
        "type": "image",
        "url": _pollinations_url(prompt, style, width, height),
        "path": "",
        "prompt": prompt,
        "warning": "Could not save locally. Use the URL to view the image.",
    }


def _pollinations_url(prompt: str, style: str, width: int, height: int) -> str:
    """Build a Pollinations.ai URL."""
    style_map = {
        "photorealistic": "photorealistic, hyperrealistic, 8K",
        "anime":          "anime style, manga, vibrant colors",
        "3d":             "3D render, octane render, cinematic",
        "concept":        "concept art, digital painting, detailed",
        "dark":           "dark theme, noir, dramatic lighting",
        "minimal":        "minimalist, clean, simple design",
    }
    style_prompt = style_map.get(style, style)
    full_prompt = f"{prompt}, {style_prompt}"
    encoded = requests.utils.quote(full_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"


def _pollinations(prompt: str, style: str, width: int, height: int) -> dict:
    """Generate image via Pollinations.ai (completely free)."""
    url = _pollinations_url(prompt, style, width, height)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("image"):
            save_path = IMG_DIR / f"{_slug(prompt)}_{int(time.time())}.png"
            save_path.write_bytes(resp.content)
            logger.info("Image saved: %s", save_path)
            return {
                "type":   "image",
                "url":    url,
                "path":   str(save_path),
                "prompt": prompt,
                "source": "pollinations.ai (free)",
            }
        return {"type": "error", "error": "Invalid image response from Pollinations"}
    except requests.Timeout:
        return {"type": "error", "error": "Image generation timed out"}
    except Exception as exc:
        logger.warning("Pollinations failed: %s", exc)
        return {"type": "error", "error": str(exc)}


def _stability(prompt: str, style: str, api_key: str) -> dict:
    """Stability AI (if key is configured)."""
    try:
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }
        body = {
            "text_prompts": [{"text": prompt, "weight": 1}],
            "cfg_scale":    7,
            "height":       1024,
            "width":        1024,
            "samples":      1,
            "steps":        30,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=90)
        resp.raise_for_status()
        img_b64 = resp.json()["artifacts"][0]["base64"]
        import base64
        save_path = IMG_DIR / f"{_slug(prompt)}_{int(time.time())}.png"
        save_path.write_bytes(base64.b64decode(img_b64))
        return {"type": "image", "path": str(save_path), "prompt": prompt, "source": "stability.ai"}
    except Exception as exc:
        logger.error("Stability AI error: %s", exc)
        return {"type": "error", "error": str(exc)}


def upscale_image(path: str, scale: int = 2) -> dict:
    """Upscale an image using PIL (basic lanczos upscaling)."""
    try:
        from PIL import Image
        img = Image.open(path)
        new_size = (img.width * scale, img.height * scale)
        upscaled = img.resize(new_size, Image.LANCZOS)
        out_path = path.replace(".png", f"_x{scale}.png")
        upscaled.save(out_path)
        return {"type": "image_upscaled", "path": out_path, "scale": scale}
    except Exception as exc:
        return {"type": "error", "error": str(exc)}


def remove_background(path: str) -> dict:
    """Remove image background using rembg (free, local)."""
    try:
        from rembg import remove
        from PIL import Image
        img = Image.open(path)
        out = remove(img)
        out_path = path.replace(".png", "_nobg.png")
        out.save(out_path, format="PNG")
        return {"type": "bg_removed", "path": out_path}
    except ImportError:
        return {"type": "error", "error": "rembg not installed. Run: pip install rembg"}
    except Exception as exc:
        return {"type": "error", "error": str(exc)}


def _slug(text: str, max_len: int = 35) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"\s+", "_", slug)[:max_len]
    return slug or "image"
