"""
VINCE tools.py
All built-in tools plus the tool registration system.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO ADD YOUR OWN TOOL (read this before you start)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OPTION A — Add directly to this file:

    @register_tool(
        "my_tool_name",
        "One-line description so VINCE knows when to use it.",
        {
            "param1": "string — what this parameter means",
            "param2": "int — optional, defaults to 5",
        },
    )
    def my_tool_name(param1: str, param2: int = 5) -> str:
        # Your logic here. Always return a string.
        result = do_something(param1, param2)
        return str(result)

OPTION B — Create a standalone toolkit file (recommended for custom tools):

    1. Create a new .py file anywhere (e.g., my_tools.py).
    2. Use this template:

        from tools import register_tool

        @register_tool(
            "weather_lookup",
            "Look up current weather for a city.",
            {"city": "string — city name"},
        )
        def weather_lookup(city: str) -> str:
            import requests
            resp = requests.get(f"https://wttr.in/{city}?format=3")
            return resp.text

    3. Load it via the UI (📦 Toolkits → Load .py Toolkit), or
       drop it in the toolkits/ folder for auto-loading on startup.

TIPS:
  - Always return a STRING from your tool function.
  - Handle exceptions inside your function and return an error string.
  - Keep descriptions clear — VINCE reads them to decide when to use the tool.
  - Parameter dict keys = Python argument names (must match exactly).
  - Mark destructive tools with the DANGEROUS_TOOL flag (see run_command below).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import subprocess
import math
import ast
import glob
import shutil
import json
import hashlib
from typing import Any, Callable, Optional

from logger import log_tool_call, log_tool_result, log_error, log_system
from config import BASE_DIR

# Optional imports — degrade gracefully
try:
    import requests
    from bs4 import BeautifulSoup
    WEB_ENABLED = True
except ImportError:
    WEB_ENABLED = False

try:
    from duckduckgo_search import DDGS
    SEARCH_ENABLED = True
except ImportError:
    SEARCH_ENABLED = False


# ─── Confirmation Callback ───────────────────────────────────────────────────
# The UI registers this callback so that dangerous tools can ask for
# confirmation before proceeding. Set via set_confirm_callback().
_confirm_callback: Optional[Callable[[str, str], bool]] = None

def set_confirm_callback(fn: Callable[[str, str], bool]) -> None:
    """
    Register a confirmation function.
    fn(title, message) -> bool: True = user approved, False = cancel.
    """
    global _confirm_callback
    _confirm_callback = fn

def _ask_confirm(title: str, message: str) -> bool:
    """Ask user for confirmation. Falls back to True (allow) if no callback set."""
    if _confirm_callback:
        return _confirm_callback(title, message)
    return True  # headless / no UI — allow by default


# ─── Tool Registry ───────────────────────────────────────────────────────────
TOOL_REGISTRY: dict[str, dict] = {}

def register_tool(name: str, description: str, parameters: dict,
                  dangerous: bool = False):
    """
    Decorator to register a function as a VINCE tool.

    Args:
        name:        Unique tool identifier (used in TOOL_CALL JSON).
        description: One-line description for VINCE to understand when to use it.
        parameters:  Dict of {arg_name: "description"} for all parameters.
        dangerous:   If True, tool will request user confirmation before running.
    """
    def decorator(fn):
        TOOL_REGISTRY[name] = {
            "function":    fn,
            "description": description,
            "parameters":  parameters,
            "dangerous":   dangerous,
        }
        return fn
    return decorator


# ─── Tool: search_online ─────────────────────────────────────────────────────
@register_tool(
    "search_online",
    "Search the web using DuckDuckGo. Returns top 5 results with titles, URLs, snippets.",
    {"query": "string — what to search for"},
)
def search_online(query: str) -> str:
    log_tool_call("search_online", {"query": query})
    if not SEARCH_ENABLED:
        return "[search_online] Install: pip install duckduckgo-search"
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.text(query, max_results=5))
        if not hits:
            return "No results found."
        lines = []
        for i, h in enumerate(hits, 1):
            lines.append(f"{i}. {h.get('title', '')}")
            lines.append(f"   URL: {h.get('href', '')}")
            lines.append(f"   {h.get('body', '')[:250]}\n")
        result = "\n".join(lines)
    except Exception as e:
        result = f"[search error] {e}"
    log_tool_result("search_online", result)
    return result


# ─── Tool: scrape_website ────────────────────────────────────────────────────
@register_tool(
    "scrape_website",
    "Fetch a URL and return its readable text. Strips scripts/styles/nav.",
    {"url": "string — full URL including https://"},
)
def scrape_website(url: str) -> str:
    log_tool_call("scrape_website", {"url": url})
    if not WEB_ENABLED:
        return "[scrape_website] Install: pip install requests beautifulsoup4"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "noscript", "iframe", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        result = text[:5000] + ("\n...[truncated]" if len(text) > 5000 else "")
    except Exception as e:
        result = f"[scrape error] {e}"
    log_tool_result("scrape_website", result)
    return result


# ─── Tool: read_file ────────────────────────────────────────────────────────
@register_tool(
    "read_file",
    "Read the contents of any file from disk. Supports text and code files.",
    {"path": "string — absolute or relative file path"},
)
def read_file(path: str) -> str:
    log_tool_call("read_file", {"path": path})
    try:
        path = os.path.expandvars(os.path.expanduser(path))
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        result = content[:10000] + ("\n...[truncated]" if len(content) > 10000 else "")
    except FileNotFoundError:
        result = f"[read_file] Not found: {path}"
    except Exception as e:
        result = f"[read_file error] {e}"
    log_tool_result("read_file", result)
    return result


# ─── Tool: write_file ────────────────────────────────────────────────────────
@register_tool(
    "write_file",
    "Write content to a file. Creates directories as needed. Overwrites existing files.",
    {
        "path":    "string — destination file path",
        "content": "string — text content to write",
        "append":  "bool — if true, append instead of overwrite (optional, default false)",
    },
)
def write_file(path: str, content: str, append: bool = False) -> str:
    log_tool_call("write_file", {"path": path, "content": f"{content[:80]}..."})
    try:
        path = os.path.expandvars(os.path.expanduser(path))
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)
        action = "Appended" if append else "Written"
        result = f"{action} successfully: {path} ({len(content)} chars)"
    except Exception as e:
        result = f"[write_file error] {e}"
    log_tool_result("write_file", result)
    return result


# ─── Tool: delete_file ───────────────────────────────────────────────────────
@register_tool(
    "delete_file",
    "Delete a file or empty directory from disk. REQUIRES USER CONFIRMATION.",
    {"path": "string — path to the file or directory to delete"},
    dangerous=True,
)
def delete_file(path: str) -> str:
    log_tool_call("delete_file", {"path": path})
    path = os.path.expandvars(os.path.expanduser(path))
    approved = _ask_confirm(
        "⚠ Confirm Deletion",
        f"VINCE wants to delete:\n\n  {path}\n\nAre you sure?",
    )
    if not approved:
        result = "[delete_file] Cancelled by user."
        log_tool_result("delete_file", result)
        return result
    try:
        if os.path.isdir(path):
            os.rmdir(path)
            result = f"Directory deleted: {path}"
        elif os.path.isfile(path):
            os.remove(path)
            result = f"File deleted: {path}"
        else:
            result = f"[delete_file] Path not found: {path}"
    except Exception as e:
        result = f"[delete_file error] {e}"
    log_tool_result("delete_file", result)
    return result


# ─── Tool: find_file ────────────────────────────────────────────────────────
@register_tool(
    "find_file",
    "Search for files by name (supports wildcards: *.py, report*.docx).",
    {
        "name":      "string — filename or glob pattern (e.g. '*.log')",
        "directory": "string — root directory (optional, defaults to home folder)",
    },
)
def find_file(name: str, directory: str = "") -> str:
    log_tool_call("find_file", {"name": name, "directory": directory})
    start = os.path.expanduser(directory) if directory else os.path.expanduser("~")
    try:
        matches = glob.glob(os.path.join(start, "**", name), recursive=True)
        if matches:
            result = "\n".join(matches[:25])
            if len(matches) > 25:
                result += f"\n...and {len(matches) - 25} more"
        else:
            result = f"No files matching '{name}' found under {start}"
    except Exception as e:
        result = f"[find_file error] {e}"
    log_tool_result("find_file", result)
    return result


# ─── Tool: list_directory ────────────────────────────────────────────────────
@register_tool(
    "list_directory",
    "List the contents of a directory (files and subdirectories).",
    {
        "path":    "string — directory path (default: current working dir)",
        "pattern": "string — optional glob filter e.g. '*.py'",
    },
)
def list_directory(path: str = ".", pattern: str = "*") -> str:
    log_tool_call("list_directory", {"path": path, "pattern": pattern})
    try:
        path = os.path.expandvars(os.path.expanduser(path))
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
        lines = [f"Contents of: {os.path.abspath(path)}", ""]
        for e in entries:
            if not glob.fnmatch.fnmatch(e.name, pattern):
                continue
            kind = "📁" if e.is_dir() else "📄"
            size = ""
            if e.is_file():
                try:
                    size = f"  ({e.stat().st_size:,} B)"
                except Exception:
                    pass
            lines.append(f"  {kind} {e.name}{size}")
        result = "\n".join(lines)
    except Exception as e:
        result = f"[list_directory error] {e}"
    log_tool_result("list_directory", result)
    return result


# ─── Tool: calculate ────────────────────────────────────────────────────────
@register_tool(
    "calculate",
    "Safely evaluate a math expression. Supports sqrt, sin, cos, log, pi, e, etc.",
    {"expression": "string — math expression e.g. 'sqrt(144) + 2**10'"},
)
def calculate(expression: str) -> str:
    log_tool_call("calculate", {"expression": expression})
    safe_globals = {
        "__builtins__": {},
        "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
        "pow": pow, "int": int, "float": float,
        "sqrt": math.sqrt, "floor": math.floor, "ceil": math.ceil,
        "log": math.log, "log10": math.log10, "log2": math.log2,
        "exp": math.exp,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan,
        "atan2": math.atan2, "degrees": math.degrees, "radians": math.radians,
        "pi": math.pi, "e": math.e, "inf": math.inf, "tau": math.tau,
        "factorial": math.factorial, "gcd": math.gcd,
        "hypot": math.hypot, "isnan": math.isnan, "isinf": math.isinf,
    }
    try:
        node = ast.parse(expression, mode="eval")
        result = str(eval(compile(node, "<expr>", "eval"), safe_globals, {}))
    except ZeroDivisionError:
        result = "Division by zero."
    except Exception as e:
        result = f"[calculate error] {e}"
    log_tool_result("calculate", result)
    return result


# ─── Tool: run_command ───────────────────────────────────────────────────────
@register_tool(
    "run_command",
    "Execute a shell command and return its output. REQUIRES USER CONFIRMATION.",
    {
        "command": "string — the shell command to execute",
        "timeout": "int — max seconds to wait (optional, default 30)",
    },
    dangerous=True,
)
def run_command(command: str, timeout: int = 30) -> str:
    log_tool_call("run_command", {"command": command})
    approved = _ask_confirm(
        "⚠ Confirm Command",
        f"VINCE wants to run:\n\n  {command}\n\nProceed?",
    )
    if not approved:
        return "[run_command] Cancelled by user."
    try:
        proc = subprocess.run(
            command, shell=True, capture_output=True,
            text=True, timeout=int(timeout),
        )
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        parts = []
        if out:
            parts.append(f"STDOUT:\n{out[:3000]}")
        if err:
            parts.append(f"STDERR:\n{err[:1000]}")
        result = "\n".join(parts) or "(no output)"
        if proc.returncode != 0:
            result = f"[exit code {proc.returncode}]\n" + result
    except subprocess.TimeoutExpired:
        result = f"[run_command] Timed out after {timeout}s."
    except Exception as e:
        result = f"[run_command error] {e}"
    log_tool_result("run_command", result)
    return result


# ─── Tool: run_app ──────────────────────────────────────────────────────────
@register_tool(
    "run_app",
    "Launch an application by name or full path. Non-blocking.",
    {"app": "string — app name (e.g. 'notepad') or full executable path"},
)
def run_app(app: str) -> str:
    log_tool_call("run_app", {"app": app})
    try:
        resolved = shutil.which(app) or app
        subprocess.Popen(resolved, shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        result = f"Launched: {app}"
    except Exception as e:
        result = f"[run_app error] {e}"
    log_tool_result("run_app", result)
    return result


# ─── Tool: read_own_files ────────────────────────────────────────────────────
@register_tool(
    "read_own_files",
    "Read one of VINCE's own source files for self-inspection or debugging.",
    {"filename": "string — e.g. 'tools.py', 'config.py', 'ui.py'"},
)
def read_own_files(filename: str) -> str:
    log_tool_call("read_own_files", {"filename": filename})
    safe = os.path.join(BASE_DIR, os.path.basename(filename))
    if not os.path.exists(safe):
        return f"[read_own_files] Not found: {filename}"
    return read_file(safe)


# ─── Tool: get_system_info ───────────────────────────────────────────────────
@register_tool(
    "get_system_info",
    "Get information about the current system: OS, CPU, RAM, disk, Python version.",
    {},
)
def get_system_info() -> str:
    log_tool_call("get_system_info", {})
    lines = []
    import platform
    lines.append(f"OS:      {platform.system()} {platform.release()} ({platform.version()})")
    lines.append(f"Machine: {platform.machine()}")
    lines.append(f"Python:  {platform.python_version()}")
    lines.append(f"CWD:     {os.getcwd()}")
    try:
        import psutil
        cpu = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        lines.append(f"CPU:     {cpu} logical cores @ {freq.current:.0f} MHz")
        lines.append(f"RAM:     {ram.used/1e9:.1f} GB used / {ram.total/1e9:.1f} GB total ({ram.percent}%)")
        lines.append(f"Disk:    {disk.used/1e9:.1f} GB used / {disk.total/1e9:.1f} GB total ({disk.percent}%)")
    except ImportError:
        lines.append("(psutil not installed — install for CPU/RAM/disk info)")
    result = "\n".join(lines)
    log_tool_result("get_system_info", result)
    return result


# ─── Tool: clipboard_read ────────────────────────────────────────────────────
@register_tool(
    "clipboard_read",
    "Read the current contents of the system clipboard.",
    {},
)
def clipboard_read() -> str:
    log_tool_call("clipboard_read", {})
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        content = root.clipboard_get()
        root.destroy()
        result = content[:3000]
    except Exception as e:
        result = f"[clipboard_read error] {e}"
    log_tool_result("clipboard_read", result)
    return result


# ─── Tool: clipboard_write ───────────────────────────────────────────────────
@register_tool(
    "clipboard_write",
    "Write text to the system clipboard.",
    {"text": "string — text to copy to clipboard"},
)
def clipboard_write(text: str) -> str:
    log_tool_call("clipboard_write", {"text": text[:50]})
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        result = f"Copied {len(text)} chars to clipboard."
    except Exception as e:
        result = f"[clipboard_write error] {e}"
    log_tool_result("clipboard_write", result)
    return result


# ─── Tool: http_request ──────────────────────────────────────────────────────
@register_tool(
    "http_request",
    "Make an HTTP GET or POST request and return the response text/JSON.",
    {
        "url":     "string — full URL",
        "method":  "string — 'GET' or 'POST' (default: GET)",
        "data":    "string — JSON body for POST requests (optional)",
        "headers": "string — JSON-encoded headers dict (optional)",
    },
)
def http_request(url: str, method: str = "GET",
                 data: str = "", headers: str = "") -> str:
    log_tool_call("http_request", {"url": url, "method": method})
    if not WEB_ENABLED:
        return "[http_request] Install: pip install requests"
    try:
        hdrs = json.loads(headers) if headers else {}
        hdrs.setdefault("User-Agent", "VINCE/2.0")
        payload = json.loads(data) if data else None
        if method.upper() == "POST":
            resp = requests.post(url, json=payload, headers=hdrs, timeout=15)
        else:
            resp = requests.get(url, headers=hdrs, timeout=15)
        ct = resp.headers.get("content-type", "")
        if "json" in ct:
            try:
                result = json.dumps(resp.json(), indent=2)[:8000]
            except Exception:
                result = resp.text[:8000]
        else:
            result = resp.text[:8000]
        result = f"[{resp.status_code}]\n{result}"
    except Exception as e:
        result = f"[http_request error] {e}"
    log_tool_result("http_request", result)
    return result

# ── Tool: Search Text in Website HTML ────────────────────────────────────────
@register_tool(
    "search_website_text",
    "Search for a specific phrase or word within a website's text and return the surrounding context.",
    {
        "url": "string — the full URL to search (including https://)",
        "query": "string — the word or phrase to look for",
        "context_window": "int — number of characters to show before and after the match (default 150)"
    },
)
def search_website_text(url: str, query: str, context_window: int = 150) -> str:
    try:
        import requests
        from bs4 import BeautifulSoup
        import re

        # Fetch the website content
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()

        # Clean the HTML to get readable text
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        
        # Get all text and normalize whitespace
        visible_text = soup.get_text(separator=" ", strip=True)
        visible_text = " ".join(visible_text.split())

        # Search for the query (case-insensitive)
        # We use re.escape to handle special characters in the query
        matches = list(re.finditer(re.escape(query), visible_text, re.IGNORECASE))

        if not matches:
            return f"The phrase '{query}' was not found in the visible text of {url}."

        results = [f"Found {len(matches)} match(es) for '{query}' on {url}:\n"]
        
        for i, match in enumerate(matches[:5], 1):  # Limit to first 5 matches
            start = max(0, match.start() - context_window)
            end = min(len(visible_text), match.end() + context_window)
            
            snippet = visible_text[start:end]
            results.append(f"Match {i}:\n... {snippet} ...\n")

        if len(matches) > 5:
            results.append(f"(Showing 5 of {len(matches)} total matches)")

        return "\n".join(results)

    except ImportError:
        return "[search_website_text] Error: requests and beautifulsoup4 must be installed."
    except Exception as e:
        return f"[search_website_text error] {e}"
# ─── Tool: hash_file ────────────────────────────────────────────────────────
@register_tool(
    "hash_file",
    "Compute the MD5, SHA1, or SHA256 hash of a file.",
    {
        "path":      "string — path to the file",
        "algorithm": "string — 'md5', 'sha1', or 'sha256' (default: sha256)",
    },
)
def hash_file(path: str, algorithm: str = "sha256") -> str:
    log_tool_call("hash_file", {"path": path, "algorithm": algorithm})
    path = os.path.expandvars(os.path.expanduser(path))
    try:
        h = hashlib.new(algorithm)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        result = f"{algorithm.upper()}: {h.hexdigest()}\nFile: {path}"
    except Exception as e:
        result = f"[hash_file error] {e}"
    log_tool_result("hash_file", result)
    return result


# ─── Dispatcher ─────────────────────────────────────────────────────────────
def execute_tool(action: str, parameters: dict) -> str:
    """Dispatch a tool call by name. Returns the result string."""
    if action not in TOOL_REGISTRY:
        msg = (f"[unknown tool] '{action}' is not registered. "
               f"Available: {', '.join(TOOL_REGISTRY.keys())}")
        log_error(msg)
        return msg
    try:
        fn = TOOL_REGISTRY[action]["function"]
        return fn(**parameters)
    except TypeError as e:
        msg = f"[tool parameter error] {action}: {e}"
        log_error(msg)
        return msg
    except Exception as e:
        msg = f"[tool execution error] {action}: {e}"
        log_error(msg)
        return msg


def get_tools_summary() -> str:
    """Human-readable list of available tools."""
    lines = []
    for name, info in TOOL_REGISTRY.items():
        danger = " ⚠" if info.get("dangerous") else ""
        lines.append(f"• {name}{danger}\n  {info['description']}")
    return "\n".join(lines)


def get_tools_for_prompt() -> str:
    """Compact tool list for injection into the system prompt."""
    lines = ["Available tools:"]
    for name, info in TOOL_REGISTRY.items():
        params = ", ".join(f'{k}: {v}' for k, v in info["parameters"].items())
        danger = " [REQUIRES CONFIRMATION]" if info.get("dangerous") else ""
        lines.append(f"- {name}{danger}: {{{params}}}")
    return "\n".join(lines)
