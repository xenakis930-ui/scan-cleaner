from __future__ import annotations

from dataclasses import asdict
from .document import PageInfo, Action
from .detectors.blank import is_blank
from .detectors.recycled import is_recycled


def analyze_pages(images, blank_threshold: float = 0.78, recycled_threshold: float = 0.55, default_blank_action: Action = "remove", default_recycled_action: Action = "separate") -> list[PageInfo]:
    pages: list[PageInfo] = []
    for i, img in enumerate(images):
        bdet, bscore, bdetails = is_blank(img, blank_threshold)
        rdet, rscore, rdetails = is_recycled(img, recycled_threshold)
        reasons = []
        action: Action = "keep"
        if bdet:
            reasons.append(f"En blanco ({bscore:.2f})")
            action = default_blank_action
        elif rdet:
            reasons.append(f"Reciclada ({rscore:.2f})")
            action = default_recycled_action
        page = PageInfo(
            index=i,
            image=img,
            blank_score=bscore,
            recycled_score=rscore,
            blank_detected=bdet,
            recycled_detected=rdet,
            action=action,
            auto_action=action,
            reasons=reasons,
            details={"blank": bdetails, "recycled": rdetails},
        )
        pages.append(page)
    return pages
