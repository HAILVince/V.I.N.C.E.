"""
VINCE Example Toolkit
─────────────────────────────────────────────────────────────────
This file demonstrates how to write a custom toolkit for VINCE.
Drop this file (or your own) in the toolkits/ folder and it will
be loaded automatically on startup.

You can also load it at runtime via: Sidebar → 📦 Load Toolkit
─────────────────────────────────────────────────────────────────

RULES FOR TOOLKIT FILES:
  1. Import register_tool from tools (not from this file's path).
  2. Decorate your functions with @register_tool.
  3. Always return a string from your tool function.
  4. Handle exceptions — return an error string, never raise.
  5. Parameter dict keys must exactly match function argument names.
  6. Set dangerous=True for tools that modify system state.
─────────────────────────────────────────────────────────────────
"""

from tools import register_tool


# ── Example 1: Simple string tool ────────────────────────────────────────────
@register_tool(
    "repeat_text",
    "Repeat a string N times. Example usage to test toolkit loading.",
    {
        "text":  "string — the text to repeat",
        "times": "int — how many times to repeat (default: 3)",
    },
)
def repeat_text(text: str, times: int = 3) -> str:
    try:
        return (text + " ") * int(times)
    except Exception as e:
        return f"[repeat_text error] {e}"


# ── Example 2: Fetch a joke from an API ───────────────────────────────────────
@register_tool(
    "get_joke",
    "Fetch a random programming joke from an online API.",
    {},
)
def get_joke() -> str:
    try:
        import requests
        r = requests.get(
            "https://v2.jokeapi.dev/joke/Programming?type=single",
            timeout=6,
        )
        data = r.json()
        if data.get("type") == "single":
            return data.get("joke", "No joke found.")
        return f"{data.get('setup','')}\n{data.get('delivery','')}"
    except ImportError:
        return "[get_joke] Install requests: pip install requests"
    except Exception as e:
        return f"[get_joke error] {e}"


# ── Example 3: Word count tool ───────────────────────────────────────────────
@register_tool(
    "word_count",
    "Count words, lines, and characters in a text string.",
    {"text": "string — the text to analyse"},
)
def word_count(text: str) -> str:
    words = len(text.split())
    lines = text.count("\n") + 1
    chars = len(text)
    chars_no_space = len(text.replace(" ", "").replace("\n", ""))
    return (
        f"Words:              {words}\n"
        f"Lines:              {lines}\n"
        f"Characters:         {chars}\n"
        f"Chars (no spaces):  {chars_no_space}"
    )


# ── Example 4: IP lookup ─────────────────────────────────────────────────────
@register_tool(
    "ip_lookup",
    "Look up geolocation and ISP info for an IP address.",
    {"ip": "string — IPv4 address to look up (leave empty for your own IP)"},
)
def ip_lookup(ip: str = "") -> str:
    try:
        import requests
        url = f"https://ipinfo.io/{ip}/json" if ip else "https://ipinfo.io/json"
        r = requests.get(url, timeout=6)
        data = r.json()
        lines = []
        for k in ("ip", "city", "region", "country", "org", "timezone"):
            if k in data:
                lines.append(f"{k.capitalize():12}: {data[k]}")
        return "\n".join(lines) if lines else "No data returned."
    except ImportError:
        return "[ip_lookup] Install requests: pip install requests"
    except Exception as e:
        return f"[ip_lookup error] {e}"
