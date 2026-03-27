#!/usr/bin/env python3
"""
Parse text from images in a folder using PaddleOCR.

Example:
  python parse_folder_with_paddleocr.py --input ./receipts --output ./output
  python parse_folder_with_paddleocr.py --input ./receipts --output ./output --ollama
"""

from __future__ import annotations

import json
import logging
import urllib.error
from pathlib import Path
from typing import Any

import click
from paddleocr import PaddleOCR

from llm_receipt import OllamaError, parse_ticket_text_with_ollama, write_receipt_csv
from ocr_parsing import concatenate_parsed_text, parse_image, prepare_ocr_run

logger = logging.getLogger(__name__)


@click.command(help="Extract text from all images in a folder using PaddleOCR.")
@click.option(
    "--input",
    "input_path",
    type=click.Path(path_type=Path),
    default="input",
    show_default=True,
    help="Path to folder containing images.",
)
@click.option(
    "--output",
    default="output",
    type=click.Path(path_type=Path),
    show_default=True,
    help="Base output directory. Writes json_output/, text_output/, and optionally csv_output/.",
)
@click.option(
    "--lang", default="es", show_default=True, help="PaddleOCR language code."
)
@click.option(
    "--use-angle-cls",
    is_flag=True,
    default=False,
    help="Enable angle classifier for rotated text.",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=True),
    show_default=True,
    help="Logging level.",
)
@click.option(
    "--ollama",
    is_flag=True,
    default=False,
    help="After OCR, call a local Ollama model to structure the ticket and write CSV to csv_output/.",
)
@click.option(
    "--ollama-host",
    default="http://127.0.0.1:11434",
    show_default=True,
    help="Ollama server base URL (no trailing path).",
)
@click.option(
    "--ollama-model",
    default="qwen2.5:latest",
    show_default=True,
    help="Model name served by Ollama.",
)
def main(
    input_path: Path,
    output: Path,
    lang: str,
    use_angle_cls: bool,
    log_level: str,
    ollama: bool,
    ollama_host: str,
    ollama_model: str,
) -> None:
    """CLI entry: configure logging, validate input, run OCR, write json_output and text_output."""

    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    output_base = output.expanduser().resolve()
    logger.info("Starting OCR run")
    logger.info("Output base directory: %s", output_base)

    input_folder, image_files, ocr = prepare_ocr_run(input_path, lang, use_angle_cls)
    run_parsing(
        image_files,
        ocr,
        input_folder,
        output_base,
        use_ollama=ollama,
        ollama_host=ollama_host,
        ollama_model=ollama_model,
    )


def run_parsing(
    image_files: list[Path],
    ocr: PaddleOCR,
    input_folder: Path,
    output_base: Path,
    *,
    use_ollama: bool = False,
    ollama_host: str = "http://127.0.0.1:11434",
    ollama_model: str = "qwen2.5:latest",
) -> None:
    """Run OCR on each image and write:

    - ``output_base/json_output/ocr_results.json`` — one JSON with all pages
    - ``output_base/text_output/<stem>.txt`` — plain text per image (lines joined with newlines)
    - If ``use_ollama``: ``output_base/csv_output/<stem>.csv`` — structured rows from Ollama
    """
    json_dir = output_base / "json_output"
    text_dir = output_base / "text_output"
    csv_dir = output_base / "csv_output"
    json_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    if use_ollama:
        csv_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Ollama CSV step enabled (host=%s, model=%s)",
            ollama_host.rstrip("/"),
            ollama_model,
        )

    json_path = json_dir / "ocr_results.json"
    all_results: dict[str, Any] = {"input_folder": str(input_folder), "files": []}

    for image_path in image_files:
        logger.info("Processing file: %s", image_path.name)
        parsed = parse_image(ocr, image_path)
        all_results["files"].append(
            {
                "file": image_path.name,
                "full_path": str(image_path),
                "line_count": len(parsed),
                "lines": parsed,
            }
        )
        logger.info(
            "Processed %s with %d extracted line(s)", image_path.name, len(parsed)
        )

        # Same basename as the image so multi-file runs stay easy to match.
        plain_text = concatenate_parsed_text(parsed)
        txt_path = text_dir / f"{image_path.stem}.txt"
        txt_path.write_text(plain_text, encoding="utf-8")
        logger.info("Saved text output to: %s", txt_path)
        logger.debug(
            "Plain text length for %s: %d chars", image_path.name, len(plain_text)
        )

        if use_ollama:
            csv_path = csv_dir / f"{image_path.stem}.csv"
            try:
                structured = parse_ticket_text_with_ollama(
                    plain_text,
                    host=ollama_host,
                    model=ollama_model,
                )
                write_receipt_csv(csv_path, image_path.name, structured)
                logger.info("Saved CSV output to: %s", csv_path)
            except (OllamaError, urllib.error.URLError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Ollama CSV step failed for %s: %s", image_path.name, exc
                )

    json_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    logger.info("Saved JSON output to: %s", json_path)
    logger.info(
        "Done: processed %d image file(s) under %s", len(image_files), input_folder
    )


if __name__ == "__main__":
    main()
