"""Ollama chat + receipt JSON extraction and CSV export."""

from __future__ import annotations

import csv
import json
import logging
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Strip optional Markdown code fences around JSON. Models sometimes reply with
# ```json ... ``` even when asked for raw JSON; ``_extract_json_object`` uses
# this to recover the inner payload before ``json.loads``.
#
# Pattern (anchors match the whole string because we use ``^`` / ``$``):
#   ^\s*                 — start, skip leading whitespace
#   ```(?:json)?        — opening fence: ``` or ```json (language tag is optional)
#   \s*\n?               — optional space/newline after the opening tag
#   (.*?)                — capture group 1: the JSON body (non-greedy)
#   \n?```\s*$           — optional newline, closing ```, trailing space, end
#
# re.DOTALL — ``.`` matches newlines so multi-line JSON inside the fence matches.
# re.IGNORECASE — the optional ``json`` language tag on the fence is matched case-insensitively.
_JSON_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL | re.IGNORECASE
)

CSV_FIELDNAMES = [
    "source_file",
    "date",
    "currency",
    "item_description",
    "quantity",
    "unit_price",
    "line_total",
    "receipt_total",
    "payment_method",
]

RECEIPT_JSON_SYSTEM = """You extract structured data from retail receipt OCR text.
Respond with ONE JSON object only (no markdown), using this shape:
{
  "date": string or null,
  "currency": string or null,
  "items": [
    {
      "description": string,
      "quantity": number or null,
      "unit_price": number or null,
      "line_total": number or null
    }
  ],
  "total": number or null,
  "payment_method": string or null
}
Use null when unknown. Numbers must be JSON numbers (no thousands separators)."""


class OllamaError(RuntimeError):
    """Raised when the Ollama HTTP API returns an unexpected or error response."""


def _extract_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from model output, allowing a single ```json ... ``` fence."""
    stripped = text.strip()
    m = _JSON_FENCE_RE.match(stripped)
    if m:
        logger.debug(
            "Model output was wrapped in a Markdown code fence; using inner JSON only"
        )
        stripped = m.group(1).strip()
    return json.loads(stripped)


def ollama_chat_json(
    host: str,
    model: str,
    system: str,
    user: str,
    *,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """Call Ollama ``/api/chat`` with ``format: json`` and return the parsed JSON object."""
    base = host.rstrip("/")
    url = f"{base}/api/chat"
    logger.debug(
        "Ollama POST %s model=%s format=json timeout=%ss",
        url,
        model,
        timeout_s,
    )
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "format": "json",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        logger.warning("Ollama HTTP %s: %s", e.code, err_body[:500])
        raise OllamaError(f"HTTP {e.code}: {err_body}") from e
    except urllib.error.URLError as e:
        logger.warning("Ollama request failed (%s): %s", url, e.reason)
        raise

    outer = json.loads(body)
    content = outer.get("message", {}).get("content")
    if not isinstance(content, str):
        logger.warning("Ollama response missing message.content: %r", outer)
        raise OllamaError(f"Unexpected Ollama response shape: {outer!r}")
    parsed = _extract_json_object(content)
    logger.info(
        "Ollama structured JSON parsed (%d top-level keys: %s)",
        len(parsed),
        ", ".join(sorted(parsed.keys())),
    )
    return parsed


def parse_ticket_text_with_ollama(
    ticket_text: str,
    *,
    host: str = "http://127.0.0.1:11434",
    model: str = "qwen2.5:latest",
) -> dict[str, Any]:
    """Send OCR plain text to Ollama and return a structured receipt dict."""
    logger.info(
        "Parsing ticket with Ollama (model=%s, host=%s, OCR text length=%d chars)",
        model,
        host.rstrip("/"),
        len(ticket_text),
    )
    user = (
        "Parse this receipt text into the required JSON schema.\n\n"
        "---\n"
        f"{ticket_text}\n"
        "---"
    )
    return ollama_chat_json(host, model, RECEIPT_JSON_SYSTEM, user)


def write_receipt_csv(
    csv_path: Path, source_file: str, structured: dict[str, Any]
) -> None:
    """Write one row per line item; repeat header-level fields on each row."""
    date = structured.get("date")
    currency = structured.get("currency")
    total = structured.get("total")
    payment = structured.get("payment_method")
    items = structured.get("items")
    if not isinstance(items, list):
        logger.debug("Structured receipt had no list at key 'items'; treating as empty")
        items = []

    rows: list[dict[str, Any]] = []
    skipped = 0
    if items:
        for it in items:
            if not isinstance(it, dict):
                skipped += 1
                continue
            rows.append(
                {
                    "source_file": source_file,
                    "date": date if date is not None else "",
                    "currency": currency if currency is not None else "",
                    "item_description": it.get("description", "") or "",
                    "quantity": it.get("quantity", ""),
                    "unit_price": it.get("unit_price", ""),
                    "line_total": it.get("line_total", ""),
                    "receipt_total": total if total is not None else "",
                    "payment_method": payment if payment is not None else "",
                }
            )
    else:
        rows.append(
            {
                "source_file": source_file,
                "date": date if date is not None else "",
                "currency": currency if currency is not None else "",
                "item_description": "",
                "quantity": "",
                "unit_price": "",
                "line_total": "",
                "receipt_total": total if total is not None else "",
                "payment_method": payment if payment is not None else "",
            }
        )

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    if skipped:
        logger.warning("Skipped %d non-object entries in items list for %s", skipped, source_file)
    logger.info(
        "Wrote CSV %s (%d data row(s), source=%s)",
        csv_path,
        len(rows),
        source_file,
    )
