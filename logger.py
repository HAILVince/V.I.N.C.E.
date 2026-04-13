"""
VINCE logger.py
Logs all interactions to a file and provides context injection for the LLM.
"""

import logging
import os
from datetime import datetime
from config import LOG_FILE

_MAX_LOG_LINES = 80  # updated at runtime from data.py


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("VINCE")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


logger = setup_logger()


def log_user(msg: str)              -> None: logger.info(f"USER: {msg}")
def log_vince(msg: str)             -> None: logger.info(f"VINCE: {msg}")
def log_tool_call(a: str, p: dict)  -> None: logger.info(f"TOOL_CALL → {a}({p})")
def log_tool_result(a: str, r: str) -> None:
    logger.info(f"TOOL_RESULT ← {a}: {r[:400]}{'...' if len(r)>400 else ''}")
def log_error(msg: str)             -> None: logger.error(f"ERROR: {msg}")
def log_system(msg: str)            -> None: logger.debug(f"SYSTEM: {msg}")


def get_log_context() -> str:
    """Read last N lines from the log for LLM context injection."""
    import data as D
    n = D.get_llm().get("max_log_lines", 40)
    if not os.path.exists(LOG_FILE):
        return ""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[-n:]).strip()
    except Exception as e:
        return f"[log read error: {e}]"


def clear_log() -> None:
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"# VINCE Log — session started {datetime.now()}\n")
        logger.info("Log cleared.")
    except Exception as e:
        logger.error(f"Failed to clear log: {e}")
