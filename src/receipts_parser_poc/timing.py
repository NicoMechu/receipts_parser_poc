"""Timing utilities (decorators) for logging function runtimes."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import wraps
from inspect import Signature, signature
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def _format_value(value: Any, *, max_len: int) -> str:
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)

    if isinstance(value, str):
        # Avoid logging full OCR/LLM text blobs.
        if len(value) > max_len:
            return f"<str len={len(value)}>"
        return repr(value)

    # Paths are common and readable.
    try:
        from pathlib import Path

        if isinstance(value, Path):
            s = str(value)
            return s if len(s) <= max_len else f"<Path len={len(s)}>"
    except Exception:
        pass

    # Keep containers lightweight.
    if isinstance(value, (list, tuple, set, frozenset)):
        return f"<{type(value).__name__} len={len(value)}>"
    if isinstance(value, dict):
        return f"<dict len={len(value)}>"

    # Fallback to a truncated repr.
    s = repr(value)
    if len(s) > max_len:
        return f"<{type(value).__name__} repr_len={len(s)}>"
    return s


def _format_call_args(
    sig: Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    max_len: int,
    max_items: int,
) -> str:
    try:
        bound = sig.bind_partial(*args, **kwargs)
    except Exception:
        return ""

    items: list[str] = []
    for k, v in bound.arguments.items():
        if k in {"self", "cls"}:
            continue
        items.append(f"{k}={_format_value(v, max_len=max_len)}")
        if len(items) >= max_items:
            break
    return ", ".join(items)


def timed(
    *,
    logger: logging.Logger,
    level: int = logging.INFO,
    name: str | None = None,
    log_args: bool = True,
    max_arg_repr_len: int = 120,
    max_arg_items: int = 4,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that logs elapsed time for a function call.

    Produces a line like:
      "<name>(arg=..., ...) took 123.45 ms"

    Argument logging is best-effort and intentionally lossy/truncated to avoid
    dumping large payloads (e.g. OCR text).
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        display_name = name or func.__name__
        sig = signature(func)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                args_str = (
                    _format_call_args(
                        sig,
                        args,  # type: ignore[arg-type]
                        kwargs,  # type: ignore[arg-type]
                        max_len=max_arg_repr_len,
                        max_items=max_arg_items,
                    )
                    if log_args
                    else ""
                )
                if args_str:
                    logger.log(
                        level, "%s(%s) took %.2f ms", display_name, args_str, elapsed_ms
                    )
                else:
                    logger.log(level, "%s took %.2f ms", display_name, elapsed_ms)

        return wrapper

    return decorator

