"""
VINCE — Virtually Intelligent Neural Cognitive Engine
config.py: Static constants and theme definitions.
Mutable runtime settings live in data.json (see data.py).
"""

import os

APP_TITLE   = "V.I.N.C.E"
APP_SUBTITLE = "Virtually Intelligent Neural Cognitive Engine"
APP_VERSION  = "2.0.0"
WINDOW_MIN   = (1000, 650)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
LOG_DIR    = os.path.join(BASE_DIR, "logs")
LOG_FILE   = os.path.join(LOG_DIR, "vince.log")
TOOLS_DIR  = os.path.join(BASE_DIR, "toolkits")
DATA_FILE  = os.path.join(BASE_DIR, "data.json")

os.makedirs(LOG_DIR,   exist_ok=True)
os.makedirs(TOOLS_DIR, exist_ok=True)

# Tool loop tags (must match system prompt)
TOOL_CALL_TAG = "TOOL_CALL:"
FINISH_TAG    = "FINAL_ANSWER:"

# ─── Themes ──────────────────────────────────────────────────────────────────
THEMES = {
    "VINCE Dark": {
        "bg":            "#0b0f1e",
        "bg_secondary":  "#0e1628",
        "bg_card":       "#131f35",
        "bg_input":      "#0e1628",
        "accent":        "#00c8ff",
        "accent2":       "#ff6030",
        "accent3":       "#00ff9f",
        "text":          "#ddeeff",
        "text_dim":      "#4a7a99",
        "text_muted":    "#2a4a66",
        "border":        "#1a3a5c",
        "border_light":  "#1f4570",
        "user_bubble":   "#0c2540",
        "ai_bubble":     "#091830",
        "tool_bubble":   "#0a1e08",
        "error_bubble":  "#220808",
        "sys_text":      "#2a5a7a",
        "button":        "#00c8ff",
        "button_text":   "#060c18",
        "button_hover":  "#33d6ff",
        "sidebar":       "#070b16",
        "sidebar_item":  "#0c1422",
        "sidebar_hover": "#111e33",
        "scrollbar":     "#1a3a5c",
        "radius":        10,
        "font_ui":       ("Segoe UI", 10),
        "font_mono":     ("Consolas", 10),
        "font_title":    ("Consolas", 16, "bold"),
        "font_small":    ("Segoe UI", 8),
    },
    "Cyberpunk": {
        "bg": "#0a0a1a", "bg_secondary": "#0d0f1f", "bg_card": "#11132a",
        "bg_input": "#0a0c1c", "accent": "#ff00cc", "accent2": "#00ffff",
        "accent3": "#ffff00", "text": "#e0e0ff", "text_dim": "#8888aa",
        "text_muted": "#555577", "border": "#2a2a55", "border_light": "#3a3a66",
        "user_bubble": "#1a1a3a", "ai_bubble": "#12122a", "tool_bubble": "#1a2a1a",
        "error_bubble": "#331111", "sys_text": "#5555aa", "button": "#ff00cc",
        "button_text": "#0a0a1a", "button_hover": "#ff44dd", "sidebar": "#080818",
        "sidebar_item": "#0c0c22", "sidebar_hover": "#181840", "scrollbar": "#2a2a55",
        "radius": 10, "font_ui": ("Segoe UI", 10), "font_mono": ("Consolas", 10),
        "font_title": ("Consolas", 16, "bold"), "font_small": ("Segoe UI", 8),
    },
    "Matrix": {
        "bg": "#001000", "bg_secondary": "#001a00", "bg_card": "#002000",
        "bg_input": "#001000", "accent": "#00ff41", "accent2": "#33ff33",
        "accent3": "#88ff88", "text": "#b3ffb3", "text_dim": "#339933",
        "text_muted": "#226622", "border": "#006600", "border_light": "#009900",
        "user_bubble": "#002a00", "ai_bubble": "#002200", "tool_bubble": "#003000",
        "error_bubble": "#330000", "sys_text": "#226622", "button": "#00ff41",
        "button_text": "#001000", "button_hover": "#44ff77", "sidebar": "#000800",
        "sidebar_item": "#001200", "sidebar_hover": "#002a00", "scrollbar": "#006600",
        "radius": 8, "font_ui": ("Courier New", 10), "font_mono": ("Courier New", 10),
        "font_title": ("Courier New", 16, "bold"), "font_small": ("Courier New", 8),
    },
    "Light Mode": {
        "bg": "#f0f2f5", "bg_secondary": "#e4e6ea", "bg_card": "#ffffff",
        "bg_input": "#ffffff", "accent": "#0066cc", "accent2": "#ff6600",
        "accent3": "#009966", "text": "#1a1a1a", "text_dim": "#666666",
        "text_muted": "#999999", "border": "#cccccc", "border_light": "#dddddd",
        "user_bubble": "#e6f0ff", "ai_bubble": "#f2f2f2", "tool_bubble": "#e6ffe6",
        "error_bubble": "#ffe6e6", "sys_text": "#888888", "button": "#0066cc",
        "button_text": "#ffffff", "button_hover": "#3385ff", "sidebar": "#e9ecef",
        "sidebar_item": "#dee2e6", "sidebar_hover": "#ced4da", "scrollbar": "#cccccc",
        "radius": 10, "font_ui": ("Segoe UI", 10), "font_mono": ("Consolas", 10),
        "font_title": ("Segoe UI", 16, "bold"), "font_small": ("Segoe UI", 8),
    },
    "Sunset": {
        "bg": "#2b1b2e", "bg_secondary": "#3a1e2c", "bg_card": "#4a2030",
        "bg_input": "#351a28", "accent": "#ff884d", "accent2": "#ffb84d",
        "accent3": "#ffd966", "text": "#ffddbb", "text_dim": "#cc9966",
        "text_muted": "#885533", "border": "#663344", "border_light": "#884455",
        "user_bubble": "#552a3a", "ai_bubble": "#442230", "tool_bubble": "#2a3a1a",
        "error_bubble": "#551111", "sys_text": "#aa7755", "button": "#ff884d",
        "button_text": "#2b1b2e", "button_hover": "#ffaa77", "sidebar": "#1f1422",
        "sidebar_item": "#2a1828", "sidebar_hover": "#3a2030", "scrollbar": "#663344",
        "radius": 10, "font_ui": ("Segoe UI", 10), "font_mono": ("Consolas", 10),
        "font_title": ("Consolas", 16, "bold"), "font_small": ("Segoe UI", 8),
    },
    "Arc Reactor": {
        "bg":            "#030912",
        "bg_secondary":  "#05101f",
        "bg_card":       "#081520",
        "bg_input":      "#05101f",
        "accent":        "#40b8f0",
        "accent2":       "#70cc70",
        "accent3":       "#f0d040",
        "text":          "#b8ddff",
        "text_dim":      "#3a6080",
        "text_muted":    "#1a3a50",
        "border":        "#0c2540",
        "border_light":  "#103060",
        "user_bubble":   "#061828",
        "ai_bubble":     "#040e1c",
        "tool_bubble":   "#061408",
        "error_bubble":  "#1a0606",
        "sys_text":      "#1a4060",
        "button":        "#40b8f0",
        "button_text":   "#030912",
        "button_hover":  "#66ccff",
        "sidebar":       "#020710",
        "sidebar_item":  "#081018",
        "sidebar_hover": "#0c1a28",
        "scrollbar":     "#0c2540",
        "radius":        10,
        "font_ui":       ("Segoe UI", 10),
        "font_mono":     ("Consolas", 10),
        "font_title":    ("Consolas", 16, "bold"),
        "font_small":    ("Segoe UI", 8),
    },
    "Stealth": {
        "bg":            "#101010",
        "bg_secondary":  "#181818",
        "bg_card":       "#1c1c1c",
        "bg_input":      "#161616",
        "accent":        "#d0d0d0",
        "accent2":       "#808080",
        "accent3":       "#60a060",
        "text":          "#e8e8e8",
        "text_dim":      "#606060",
        "text_muted":    "#303030",
        "border":        "#282828",
        "border_light":  "#303030",
        "user_bubble":   "#1e1e1e",
        "ai_bubble":     "#181818",
        "tool_bubble":   "#141a10",
        "error_bubble":  "#1a1010",
        "sys_text":      "#3a3a3a",
        "button":        "#d0d0d0",
        "button_text":   "#101010",
        "button_hover":  "#ffffff",
        "sidebar":       "#0c0c0c",
        "sidebar_item":  "#141414",
        "sidebar_hover": "#1c1c1c",
        "scrollbar":     "#282828",
        "radius":        10,
        "font_ui":       ("Segoe UI", 10),
        "font_mono":     ("Consolas", 10),
        "font_title":    ("Consolas", 16, "bold"),
        "font_small":    ("Segoe UI", 8),
    },
    "Amber Terminal": {
        "bg":            "#0a0800",
        "bg_secondary":  "#120f00",
        "bg_card":       "#1a1500",
        "bg_input":      "#120f00",
        "accent":        "#ffaa00",
        "accent2":       "#ff6000",
        "accent3":       "#00cc88",
        "text":          "#ffe090",
        "text_dim":      "#806020",
        "text_muted":    "#402010",
        "border":        "#2a2000",
        "border_light":  "#3a2c00",
        "user_bubble":   "#1a1200",
        "ai_bubble":     "#100d00",
        "tool_bubble":   "#0a1408",
        "error_bubble":  "#1a0800",
        "sys_text":      "#3a2800",
        "button":        "#ffaa00",
        "button_text":   "#0a0800",
        "button_hover":  "#ffcc44",
        "sidebar":       "#080600",
        "sidebar_item":  "#100d00",
        "sidebar_hover": "#1a1500",
        "scrollbar":     "#2a2000",
        "radius":        10,
        "font_ui":       ("Segoe UI", 10),
        "font_mono":     ("Consolas", 10),
        "font_title":    ("Consolas", 16, "bold"),
        "font_small":    ("Segoe UI", 8),
    },
}

DEFAULT_THEME = "VINCE Dark"

# ─── System Prompt Template ──────────────────────────────────────────────────
# {profile_extra} and {tools_list} are replaced at runtime
PROMPT_FILE = os.path.join(BASE_DIR, "system_prompt.txt")

# Default prompt to create if the file doesn't exist yet
DEFAULT_PROMPT = """\
You are V.I.N.C.E. — Virtually Intelligent Neural Cognitive Engine.
You serve as a personal AI assistant. You are calm, precise, and efficient — \
with dry wit and subtle sarcasm when appropriate. Think of Tony Stark's JARVIS: \
loyal, slightly condescending when the situation warrants it, and always helpful.

{profile_extra}

## Tool Usage
When you need to use a tool, output EXACTLY this format on its own line:

TOOL_CALL: {{"action": "tool_name", "parameters": {{"param1": "value1"}}}}

{tools_list}

After receiving a TOOL_RESULT:, continue — call another tool or finish.
When done, prefix your final answer with:

FINAL_ANSWER: <your reply here>
"""

if not os.path.exists(PROMPT_FILE):
    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        f.write(DEFAULT_PROMPT)

def get_system_prompt():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()

# For backwards compatibility, assign it as a property or fetch it live
SYSTEM_PROMPT_TEMPLATE = get_system_prompt()