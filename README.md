# Receipts Parser POC (PaddleOCR + Ollama)

Proof of concept to OCR receipts from images using `PaddleOCR`, persist the extracted text as JSON/plain-text, and (optionally) call `Ollama` to structure the receipt and export a CSV.

## Requirements

- Python `3.12+`
- [Poetry](https://python-poetry.org/)

## Project structure

- `parse_folder_with_paddleocr.py`: main CLI (orchestrates OCR, output writing, optional Ollama step)
- `ocr_parsing.py`: OCR logic (PaddleOCR setup, per-image parsing, text concatenation)
- `llm_receipt.py`: Ollama integration (JSON request/response) + CSV export
- `input/`: input folder (images to process) — **git-ignored**
- `output/`: base output folder — **git-ignored**

## Install with Poetry

From the project root:

```bash
poetry env use python3.12
poetry install
```

> Note: `paddlepaddle` and its dependencies (e.g. `opencv`) are heavy; the first install can take a while. If `pip` times out, you can retry with `poetry run python -m pip install --default-timeout 1200`.

## Run the script

Recommended command:

```bash
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True poetry run python parse_folder_with_paddleocr.py
```

## Available parameters

```bash
poetry run python parse_folder_with_paddleocr.py --help
```

Main options:

- `--input` (optional): folder with images (default: `input`)
- `--output` (optional): base output folder (default: `output`). It will create `json_output/`, `text_output/` and (when using `--ollama`) `csv_output/`
- `--lang` (optional): PaddleOCR language code (default: `es`)
- `--use-angle-cls` (optional): enable rotated-text angle classifier
- `--log-level` (optional): `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)
- `--ollama/--no-ollama` (optional): enable/disable the LLM step (default: enabled). When enabled, it writes one CSV per image into `csv_output/`
- `--ollama-host` (optional): Ollama base URL (default: `http://127.0.0.1:11434`)
- `--ollama-model` (optional): Ollama model name (default: `qwen2.5:latest` — adjust to your installed models)

## Supported formats

The script processes:

- `.png`
- `.jpg`
- `.jpeg`
- `.bmp`
- `.tif`
- `.tiff`
- `.webp`

## Logs

The script logs with timestamp and level:

- run start
- input/output folders
- number of files found
- per-file progress
- final writes

Example with more verbose logs:

```bash
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True poetry run python parse_folder_with_paddleocr.py --log-level DEBUG
```

## Outputs (json_output and text_output)

With `--output ./output` (or any base folder you choose), the following structure is created:

- `output/json_output/ocr_results.json`: one aggregated JSON file (all images in one file)
- `output/text_output/<image_name>.txt`: one plain-text file per image (OCR lines joined with newlines)

If you enable `--ollama`, additionally:

- `output/csv_output/<image_name>.csv`: one CSV per image (one row per detected item)

CSV columns:

- `source_file`
- `date`
- `currency`
- `item_description`
- `quantity`
- `unit_price`
- `line_total`
- `receipt_total`
- `payment_method`

## JSON output

The `json_output/ocr_results.json` file has this general schema:

- `input_folder`: absolute input folder path
- `files`: list of per-file entries with:
  - `file`
  - `full_path`
  - `line_count`
  - `lines` (text, confidence, bounding box)

## Quick troubleshooting

- If it hangs on connectivity checks:
  - use `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True`
- If install is slow or times out:
  - retry with `--default-timeout 1200`
- Editor import warning for `paddleocr`:
  - it is often the IDE interpreter, not Poetry's runtime
- If Ollama returns `model not found`:
  - use an installed model (`ollama list`, then e.g. `--ollama-model qwen2.5:latest`)

