"""
VINCE toolkit_loader.py
Dynamically load Python toolkit files at runtime.

A toolkit file is any .py file that:
  1. Imports register_tool from tools: `from tools import register_tool`
  2. Defines functions decorated with @register_tool

VINCE discovers and imports these files, auto-registering their tools.

Example toolkit file (my_toolkit.py):
    from tools import register_tool

    @register_tool(
        "my_tool",
        "Description VINCE uses to decide when to call this.",
        {"param": "string — description of the parameter"},
    )
    def my_tool(param: str) -> str:
        return f"Result for: {param}"
"""

import os
import sys
import importlib.util
from typing import Optional

from config import TOOLS_DIR
from logger import log_system, log_error

# Track loaded toolkits {path: module}
_loaded_toolkits: dict[str, object] = {}


def load_toolkit(path: str) -> tuple[bool, str]:
    """
    Load a Python toolkit file. Returns (success, message).
    The file's @register_tool decorators fire on import, auto-registering tools.
    """
    if not os.path.isfile(path):
        return False, f"File not found: {path}"
    if not path.endswith(".py"):
        return False, "Only .py files are supported as toolkits."

    try:
        import ast
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        tool_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "register_tool":
                if node.args and isinstance(node.args[0], ast.Str):
                    tool_names.append(node.args[0].s)
        from tools import TOOL_REGISTRY
        conflicts = [name for name in tool_names if name in TOOL_REGISTRY]
        if conflicts:
            return False, f"Cannot load toolkit: tool(s) already exist: {', '.join(conflicts)}"
        module_name = f"_vince_toolkit_{os.path.splitext(os.path.basename(path))[0]}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None:
            return False, f"Could not create module spec for: {path}"
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        _loaded_toolkits[path] = module
        log_system(f"Toolkit loaded: {path}")
        return True, f"Toolkit loaded: {os.path.basename(path)}"
    except Exception as e:
        log_error(f"Failed to load toolkit {path}: {e}")
        return False, f"Failed to load toolkit: {e}"


def unload_toolkit(path: str) -> tuple[bool, str]:
    """Remove a loaded toolkit (tools remain registered until restart)."""
    if path in _loaded_toolkits:
        module_name = _loaded_toolkits[path].__name__
        if module_name in sys.modules:
            del sys.modules[module_name]
        del _loaded_toolkits[path]
        return True, f"Unloaded: {os.path.basename(path)}"
    return False, "Toolkit not currently loaded."


def load_all_from_dir(directory: str = TOOLS_DIR) -> list[str]:
    """
    Auto-load all .py files in a directory.
    Returns list of result messages.
    """
    results = []
    if not os.path.isdir(directory):
        return results
    for fname in os.listdir(directory):
        if fname.endswith(".py") and not fname.startswith("_"):
            success, msg = load_toolkit(os.path.join(directory, fname))
            results.append(msg)
    return results


def get_loaded_toolkits() -> list[str]:
    """Return list of currently loaded toolkit paths."""
    return list(_loaded_toolkits.keys())
