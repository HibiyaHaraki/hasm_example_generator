"""Logger adapter for hasm_example_generator scripts.

Prefers the shared hasm_logger Python package when available as a submodule,
then falls back to a local standard-library logger.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Callable

_EXTERNAL_SETUP: Callable[..., logging.Logger] | None = None
_SOURCE_LOGGED = False


def _resolve_candidate_paths() -> list[Path]:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    env_path = os.getenv("HASM_LOGGER_PYTHON_PATH", "").strip()

    candidates = [
        Path(env_path) if env_path else None,
        script_dir / "hasm_logger" / "src" / "python",
        repo_root / "hasm_logger" / "src" / "python",
        repo_root / "submodules" / "hasm_logger" / "src" / "python",
        repo_root.parent / "hasm_logger" / "src" / "python",
    ]

    return [path for path in candidates if path is not None]


def _fallback_setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)

    return logger


def _load_external_setup() -> Callable[[str, str], logging.Logger] | None:
    global _EXTERNAL_SETUP
    if _EXTERNAL_SETUP is not None:
        return _EXTERNAL_SETUP

    for path in _resolve_candidate_paths():
        if not path.exists() or not path.is_dir():
            continue
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
        try:
            from hasm_logger import setup_logger as external_setup_logger

            _EXTERNAL_SETUP = external_setup_logger
            return external_setup_logger
        except Exception:
            continue
    return None


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    global _SOURCE_LOGGED
    external_setup = _load_external_setup()
    if external_setup is not None:
        logger = external_setup(name=name, level=level)
        if not _SOURCE_LOGGED:
            logger.info("Logger source: shared hasm_logger package")
            _SOURCE_LOGGED = True
        return logger

    logger = _fallback_setup_logger(name=name, level=level)
    if not _SOURCE_LOGGED:
        logger.warning("Logger source: fallback standard logging (shared hasm_logger not found)")
        _SOURCE_LOGGED = True
    return logger
