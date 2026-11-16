from __future__ import annotations

import numpy as np
from PIL import Image


def recycled_score(image: Image.Image) -> tuple[float, dict]:
    """Return (score_0_to_1, details) where higher means more likely recycled paper.

    Heuristics (editable/approximate):
    - off-white / grayish or warm-gray background instead of bright white
    - visible speckles/texture (local contrast in background regions)
    """
    img = image.convert("RGB")
    img.thumbnail((1200, 1200))
    arr = np.asarray(img, dtype=np.float32)

    # Sample likely background pixels (brightest in luminance)
    lum = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
    bg_mask = lum >= np.percentile(lum, 70)
    if bg_mask.sum() < 100:
        bg_mask = np.ones_like(lum, dtype=bool)
    bg = arr[bg_mask]
    mean_rgb = bg.mean(axis=0)
    mean_lum = float(lum[bg_mask].mean())

    # Recycled paper often: not very bright, and/or slightly warm/gray
    # whiteness: how close channels are and how bright
    channel_spread = float(np.mean(np.std(bg, axis=1)))
    brightness_dev = float(np.clip((245.0 - mean_lum) / 60.0, 0.0, 1.0))
    warmth = float(np.clip((mean_rgb[0] - mean_rgb[2]) / 20.0, -1.0, 1.0))
    grayness = float(np.clip(1.0 - channel_spread / 18.0, 0.0, 1.0))
    color_component = 0.65 * brightness_dev + 0.35 * max(0.0, warmth) * 0.5

    # Texture/speckles in background: high-pass variation
    blur = _box_blur(lum, 9)
    high = np.abs(lum - blur)
    # focus on mid-bright regions to avoid text edges dominating
    tex_mask = (lum > np.percentile(lum, 40)) & (lum < np.percentile(lum, 95))
    speckle = float(np.mean(high[tex_mask])) if tex_mask.any() else float(np.mean(high))
    texture_component = float(np.clip((speckle - 1.5) / 4.0, 0.0, 1.0))

    # combine: need some color/tone evidence; texture boosts confidence
    score = 0.6 * color_component + 0.4 * texture_component
    # very bright clean white paper should score low
    if mean_lum > 242 and channel_spread < 6 and speckle < 2.0:
        score *= 0.25
    score = float(np.clip(score, 0.0, 1.0))
    details = {
        "mean_lum": mean_lum,
        "mean_rgb": [float(x) for x in mean_rgb],
        "channel_spread": channel_spread,
        "speckle": speckle,
    }
    return score, details


def _box_blur(arr: np.ndarray, k: int) -> np.ndarray:
    # simple separable box blur using cumulative sums
    pad = k // 2
    h, w = arr.shape
    out = arr.copy()
    # horizontal
    padded = np.pad(arr, ((0, 0), (pad, pad)), mode="edge")
    c = np.cumsum(padded, axis=1, dtype=np.float64)
    c = np.concatenate([np.zeros((h, 1)), c], axis=1)
    out = (c[:, k:] - c[:, :-k]) / k
    # vertical
    padded = np.pad(out, ((pad, pad), (0, 0)), mode="edge")
    c = np.cumsum(padded, axis=0, dtype=np.float64)
    c = np.concatenate([np.zeros((1, w)), c], axis=0)
    out = (c[k:, :] - c[:-k, :]) / k
    return out.astype(np.float32)


def is_recycled(image: Image.Image, threshold: float = 0.55) -> tuple[bool, float, dict]:
    score, details = recycled_score(image)
    return score >= threshold, score, details
