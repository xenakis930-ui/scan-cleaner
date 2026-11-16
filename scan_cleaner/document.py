from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF
from PIL import Image


Action = Literal["keep", "remove", "separate"]


@dataclass
class PageInfo:
    index: int
    image: Image.Image
    blank_score: float = 0.0
    recycled_score: float = 0.0
    blank_detected: bool = False
    recycled_detected: bool = False
    action: Action = "keep"
    auto_action: Action = "keep"
    reasons: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def load_document(path: str | Path) -> list[Image.Image]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        img = Image.open(path)
        # handle multi-page tiff
        frames = []
        try:
            i = 0
            while True:
                img.seek(i)
                frames.append(img.convert("RGB"))
                i += 1
        except EOFError:
            pass
        return frames or [img.convert("RGB")]
    raise ValueError(f"Formato no soportado: {suffix}")


def _load_pdf(path: Path, zoom: float = 2.0) -> list[Image.Image]:
    doc = fitz.open(path)
    images = []
    mat = fitz.Matrix(zoom, zoom)
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
    finally:
        doc.close()
    return images


def export_pdf(pages: list[PageInfo], out_path: str | Path, include_actions: set[Action] | None = None) -> None:
    """Export selected pages as PDF based on their PIL images."""
    if include_actions is None:
        include_actions = {"keep"}
    selected = [p for p in pages if p.action in include_actions]
    if not selected:
        raise ValueError("No hay páginas para exportar con la acción seleccionada.")
    imgs = [p.image.convert("RGB") for p in selected]
    first, rest = imgs[0], imgs[1:]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    first.save(out_path, save_all=True, append_images=rest, format="PDF")


def export_separated(original_pages: list[PageInfo], keep_path: str | Path, removed_path: str | Path, separated_path: str | Path) -> dict[str, int]:
    counts = {"keep": 0, "remove": 0, "separate": 0}
    for p in original_pages:
        counts[p.action] += 1
    if counts["keep"]:
        export_pdf(original_pages, keep_path, {"keep"})
    if counts["remove"]:
        export_pdf(original_pages, removed_path, {"remove"})
    if counts["separate"]:
        export_pdf(original_pages, separated_path, {"separate"})
    return counts
