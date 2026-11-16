from __future__ import annotations

import numpy as np
from PIL import Image


def blank_score(image: Image.Image) -> tuple[float, dict]:
    """Return (score_0_to_1, details) where higher means more likely blank.

    Heuristics:
    - low edge/ink density after adaptive-like thresholding
    - low local variance (mostly uniform)
    - high brightness uniformity (not required, but common for blank scans)
    """
    img = image.convert("L")
    # Downscale for speed
    img.thumbnail((1200, 1200))
    arr = np.asarray(img, dtype=np.float32)

    # Ink: pixels significantly darker than local-ish/global bright background
    # Use percentile as background estimate
    bg = np.percentile(arr, 90)
    thr = max(0, min(255, bg - 25))
    ink = (arr < thr).astype(np.float32)
    ink_ratio = float(ink.mean())

    # Variance / texture
    std = float(arr.std())
    # Gradient magnitude approx
    gy, gx = np.gradient(arr)
    grad = float(np.mean(np.sqrt(gx * gx + gy * gy)))

    # Score components (tuned for typical scans)
    # ink_ratio: 0.0 blank -> 1.0 text-heavy
    ink_component = 1.0 - np.clip(ink_ratio / 0.015, 0.0, 1.0)
    std_component = 1.0 - np.clip(std / 18.0, 0.0, 1.0)
    grad_component = 1.0 - np.clip(grad / 6.0, 0.0, 1.0)

    score = 0.55 * ink_component + 0.25 * std_component + 0.20 * grad_component
    score = float(np.clip(score, 0.0, 1.0))
    details = {
        "ink_ratio": ink_ratio,
        "std": std,
        "grad": grad,
        "bg_p90": float(bg),
    }
    return score, details


def is_blank(image: Image.Image, threshold: float = 0.78) -> tuple[bool, float, dict]:
    score, details = blank_score(image)
    return score >= threshold, score, details
