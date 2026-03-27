"""PaddleOCR helpers: discover images, run OCR, join lines to plain text."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import click
from paddleocr import PaddleOCR

# Image extensions PaddleOCR can read directly as file paths.
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
logger = logging.getLogger(__name__)


def prepare_ocr_run(
    input_path: Path, lang: str, use_angle_cls: bool
) -> tuple[Path, list[Path], PaddleOCR]:
    """Resolve the input directory, collect supported images, and construct a PaddleOCR instance.

    ``use_angle_cls`` maps to PaddleOCR's ``use_textline_orientation`` (rotated / skewed text).
    """
    input_folder = input_path.expanduser().resolve()
    logger.info("Input folder: %s", input_folder)

    if not input_folder.exists() or not input_folder.is_dir():
        raise click.ClickException(
            f"Input folder not found or not a directory: {input_folder}"
        )

    image_files = collect_image_files(input_folder)
    if not image_files:
        raise click.ClickException(
            f"No supported image files found in {input_folder}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    logger.info("Found %d supported image file(s)", len(image_files))

    logger.info(
        "Initializing PaddleOCR (lang=%s, use_textline_orientation=%s)",
        lang,
        use_angle_cls,
    )
    ocr = PaddleOCR(use_textline_orientation=use_angle_cls, lang=lang)
    return input_folder, image_files, ocr


def collect_image_files(input_folder: Path) -> list[Path]:
    """Return supported image paths in ``input_folder`` (non-recursive, sorted by name)."""
    files = []
    for path in sorted(input_folder.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return files


def concatenate_parsed_text(parsed: list[dict[str, Any]]) -> str:
    """Join recognition lines into a single UTF-8 string; omit empty strings."""
    lines = [entry["text"] for entry in parsed if entry.get("text")]
    return "\n".join(lines)


def parse_image(ocr: PaddleOCR, image_path: Path) -> list[dict[str, Any]]:
    """Run OCR on one image and return a flat list of dicts with text, confidence, and box.

    PaddleOCR 3.x returns a list of page dicts;
        we read ``rec_texts``, ``rec_scores``, and ``rec_boxes``.
    """
    logger.debug("Running OCR on %s", image_path)
    raw = ocr.predict(str(image_path))
    result: list[dict[str, Any]] = []

    if not raw:
        logger.warning("OCR returned no result pages for %s", image_path.name)
        return result

    page = raw[0]
    rec_texts = page.get("rec_texts", []) if isinstance(page, dict) else []
    rec_scores = page.get("rec_scores", []) if isinstance(page, dict) else []
    rec_boxes = page.get("rec_boxes", []) if isinstance(page, dict) else []

    for idx, text in enumerate(rec_texts):
        confidence = rec_scores[idx] if idx < len(rec_scores) else 0.0
        # Boxes may be numpy arrays; convert so ``json.dumps`` can serialize them.
        box = (
            rec_boxes[idx].tolist()
            if idx < len(rec_boxes) and hasattr(rec_boxes[idx], "tolist")
            else (rec_boxes[idx] if idx < len(rec_boxes) else [])
        )
        result.append(
            {
                "text": text,
                "confidence": float(confidence),
                "box": box,
            }
        )
    logger.debug("OCR extracted %d line(s) from %s", len(result), image_path.name)
    return result
