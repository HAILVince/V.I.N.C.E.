"""
VINCE ui.py
Modern Iron-Man-HUD-style UI.
Features: rounded panels, model selector, profiles, TTS/PTT controls,
          streaming chat, tool visualisation, full settings panel.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import datetime
import re
import psutil
try:
    import GPUtil
except ImportError:
    GPUtil = None
import data as D
from config import APP_TITLE, APP_VERSION, THEMES, DEFAULT_THEME, WINDOW_MIN
from logger import log_system, clear_log
from tools import get_tools_summary, TOOL_REGISTRY, set_confirm_callback
from admin_utils import is_admin, restart_as_admin, admin_status_string, admin_status_color
import tts_engine
import voice_input as vi_module
import toolkit_loader


# ─── Rounded helpers ─────────────────────────────────────────────────────────

def _round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r=10, **kwargs):
    """Draw a rounded rectangle on a Canvas."""
    r = min(r, (x2-x1)//2, (y2-y1)//2)
    pts = [
        x1+r, y1,  x2-r, y1,
        x2,   y1,  x2,   y1+r,
        x2,   y2-r,x2,   y2,
        x2-r, y2,  x1+r, y2,
        x1,   y2,  x1,   y2-r,
        x1,   y1+r,x1,   y1,
        x1+r, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kwargs)


class RoundedButton(tk.Canvas):
    """A Canvas that renders as a styled rounded button."""

    def __init__(self, parent, text, command=None,
                 bg="#00c8ff", fg="#060c18", hover_bg=None,
                 radius=8, font_spec=None, width=120, height=32,
                 outer_bg="#0b0f1e", **kwargs):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, bd=0,
                         cursor="hand2", bg=outer_bg)
        self._text      = text
        self._command   = command
        self._bg        = bg
        self._fg        = fg
        self._hover     = hover_bg or self._lighten(bg, 0.2)
        self._radius    = radius
        self._font      = font_spec or ("Segoe UI", 9, "bold")
        self._disabled  = False
        self._outer_bg  = outer_bg

        self._draw(bg)
        self.bind("<Enter>",    lambda e: self._on_hover(True))
        self.bind("<Leave>",    lambda e: self._on_hover(False))
        self.bind("<Button-1>", lambda e: self._on_click())

    def _draw(self, fill):
        self.delete("all")
        w = int(self["width"])
        h = int(self["height"])
        _round_rect(self, 1, 1, w-1, h-1, r=self._radius,
                    fill=fill, outline=self._outer_bg)
        self.create_text(w//2, h//2, text=self._text, fill=self._fg,
                         font=self._font)

    def _on_hover(self, entering):
        if not self._disabled:
            self._draw(self._hover if entering else self._bg)

    def _on_click(self):
        if not self._disabled and self._command:
            self._command()

    def configure(self, **kw):
        if "text" in kw:
            self._text = kw.pop("text")
            self._draw(self._bg)
        if "state" in kw:
            s = kw.pop("state")
            self._disabled = (s == tk.DISABLED)
            self._draw(self._lighten(self._bg, -0.3) if self._disabled else self._bg)
        if "bg" in kw:
            self._bg    = kw.pop("bg")
            self._hover = self._lighten(self._bg, 0.2)
            self._draw(self._bg)
        if "fg" in kw:
            self._fg = kw.pop("fg")
            self._draw(self._bg)
        if "outer_bg" in kw:
            self._outer_bg = kw.pop("outer_bg")
            self.config(bg=self._outer_bg)
            self._draw(self._bg)
        super().configure(**kw)

    @staticmethod
    def _lighten(hex_col: str, amount: float) -> str:
        try:
            r = int(hex_col[1:3], 16)
            g = int(hex_col[3:5], 16)
            b = int(hex_col[5:7], 16)
            factor = 1 + amount
            r = max(0, min(255, int(r * factor)))
            g = max(0, min(255, int(g * factor)))
            b = max(0, min(255, int(b * factor)))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_col


class RoundedPanel(tk.Canvas):
    """A container with a rounded rectangle background. Children go into .frame."""

    def __init__(self, parent, bg_color, outer_bg,
                 radius=10, border_color=None, **kwargs):
        super().__init__(parent, bg=outer_bg, highlightthickness=0, bd=0, **kwargs)
        self._fill    = bg_color
        self._border  = border_color or bg_color
        self._radius  = radius
        self._outer   = outer_bg
        self.frame    = tk.Frame(self, bg=bg_color)
        self._win_id  = self.create_window(0, 0, window=self.frame, anchor="nw")
        self.bind("<Configure>", self._redraw)

    def _redraw(self, _=None):
        self.delete("rrect")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        _round_rect(self, 0, 0, w, h, r=self._radius,
                    fill=self._fill, outline=self._border, tags="rrect")
        self.tag_lower("rrect")
        self.itemconfig(self._win_id, width=w, height=h)

    def update_colors(self, bg_color, outer_bg, border_color=None):
        self._fill   = bg_color
        self._border = border_color or bg_color
        self._outer  = outer_bg
        self.config(bg=outer_bg)
        self.frame.config(bg=bg_color)
        self._redraw()


# ─── Main Application ─────────────────────────────────────────────────────────

class VINCEApp(tk.Tk):

    def __init__(self, llm_client):
        super().__init__()
        self._cpu_bar = None
        self._ram_bar = None
        self._cpu_label = None
        self._ram_label = None
        self._update_resources()
        self.llm            = llm_client
        self._theme_name    = D.get("current_theme") or DEFAULT_THEME
        self.T              = THEMES.get(self._theme_name, THEMES[DEFAULT_THEME])
        self._is_thinking   = False
        self._stream_tokens = 0
        self._last_response = ""
        self._ptt_held      = False
        self._voice_input   = None
        self._tts           = tts_engine.get_engine()

        # Register confirmation callback (tools → UI)
        set_confirm_callback(self._confirm_dialog)

        self._setup_window()
        self._build_ui()
        self._apply_theme(self._theme_name)
        self._show_welcome()
        self._init_voice()

        # Load toolkits from toolkits/ folder
        msgs = toolkit_loader.load_all_from_dir()
        for m in msgs:
            log_system(m)

        log_system("VINCEApp initialised.")

    # ─── Window ──────────────────────────────────────────────────────────────
    def _update_resources(self):
        try:
            # Update CPU & RAM
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            
            self._cpu_label.config(text=f"CPU: {cpu}%")
            self._cpu_bar['value'] = cpu
            
            self._ram_label.config(text=f"RAM: {ram}%")
            self._ram_bar['value'] = ram
            
            # Update GPU
            if GPUtil is not None:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_load = gpus[0].load * 100
                    # You could also add VRAM here if you wanted: f"GPU: {gpu_load:.1f}% | VRAM: {gpus[0].memoryUtil * 100:.1f}%"
                    self._gpu_label.config(text=f"GPU: {gpu_load:.1f}%")
                    self._gpu_bar['value'] = gpu_load
                else:
                    self._gpu_label.config(text="GPU: N/A")
                    self._gpu_bar['value'] = 0
            else:
                self._gpu_label.config(text="GPU: Missing GPUtil")
                self._gpu_bar['value'] = 0

        except Exception as e:
            pass # Fail silently if sensors glitch momentarily
            
        # Schedule the next update in 1.5 seconds
        self.after(1500, self._update_resources)
    def _setup_window(self):
        self.title(f"{APP_TITLE} — Virtually Intelligent Neural Cognitive Engine - v{APP_VERSION}")##########################################################
        geo = D.get("window_geometry") or "1280x820"
        self.geometry(geo)
        self.minsize(*WINDOW_MIN)
        self.configure(bg=self.T["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, _=None):
        geo = self.geometry()
        if "x" in geo and "+" in geo:
            D.set("window_geometry", geo.split("+")[0])

    # ─── UI ld ────────────────────────────────────────────────────────────

    def _build_ui(self):
        t = self.T
        # ── Top bar ──────────────────────────────────────────────────────────
        self._top = tk.Frame(self, height=52)
        self._top.pack(fill=tk.X, side=tk.TOP)
        self._top.pack_propagate(False)

        self._title_lbl = tk.Label(
            self._top, text=f"◈  {APP_TITLE}",
            font=t["font_title"],
        )
        self._title_lbl.pack(side=tk.LEFT, padx=18, pady=10)

        self._status_lbl = tk.Label(self._top, text="● ONLINE", font=("Consolas", 8))
        self._status_lbl.pack(side=tk.LEFT, padx=4)

        self._admin_lbl = tk.Label(
            self._top,
            text=f"[{admin_status_string()}]",
            font=("Consolas", 8),
        )
        self._admin_lbl.pack(side=tk.LEFT, padx=6)

        # Top-right buttons (we'll re-create on theme change)
        self._top_btn_frame = tk.Frame(self._top)
        self._top_btn_frame.pack(side=tk.RIGHT, padx=8, pady=8)
        self._build_top_buttons()

        # ── Separator ─────────────────────────────────────────────────────────
        self._sep = tk.Frame(self, height=1)
        self._sep.pack(fill=tk.X)

        # ── Body: sidebar + chat ──────────────────────────────────────────────
        self._body = tk.Frame(self)
        self._body.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        self._sidebar = tk.Frame(self._body, width=210)
        self._sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self._sidebar.pack_propagate(False)
        self._build_sidebar()

        tk.Frame(self._body, width=1).pack(side=tk.LEFT, fill=tk.Y)

        # Chat column
        self._chat_col = tk.Frame(self._body)
        self._chat_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Model + profile bar
        self._model_bar = tk.Frame(self._chat_col, height=38)
        self._model_bar.pack(fill=tk.X)
        self._model_bar.pack_propagate(False)
        self._build_model_bar()

        # Chat history
        self._chat_hist = tk.Text(
            self._chat_col,
            wrap=tk.WORD, state=tk.DISABLED,
            relief=tk.FLAT, padx=14, pady=10,
            cursor="arrow", spacing3=4,
        )
        sb = tk.Scrollbar(self._chat_col, command=self._chat_hist.yview)
        self._chat_hist.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._chat_hist.pack(fill=tk.BOTH, expand=True)
        self._setup_tags()

        # ── Input bar ─────────────────────────────────────────────────────────
        self._inp_bar = tk.Frame(self, height=80)
        self._inp_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._inp_bar.pack_propagate(False)
        self._build_input_bar()

        # ── Status bar ────────────────────────────────────────────────────────
        self._stat_bar = tk.Frame(self, height=22)
        self._stat_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self._stat_left = tk.Label(self._stat_bar, anchor=tk.W, font=("Consolas", 8))
        self._stat_left.pack(side=tk.LEFT, padx=8)
        self._stat_right = tk.Label(self._stat_bar, anchor=tk.E, font=("Consolas", 8))
        self._stat_right.pack(side=tk.RIGHT, padx=8)
        self._update_statusbar()

    def _build_top_buttons(self):
        for w in self._top_btn_frame.winfo_children():
            w.destroy()
        t = self.T
        btns = [
            ("📦 Modules",  self._open_modules),
            ("🛠 Tools",    self._open_tools),
            ("🎨 Themes",   self._open_themes),
            ("⚙ Settings", self._open_settings),
            ("❓ Help",     self._open_help),
        ]
        for label, cmd in btns:
            b = tk.Button(
                self._top_btn_frame, text=label, command=cmd,
                font=t["font_small"], relief=tk.FLAT, cursor="hand2",
                padx=8, pady=3,
            )
            b.pack(side=tk.LEFT, padx=2)
        self._top_btns = self._top_btn_frame.winfo_children()

    def _build_model_bar(self):
        for w in self._model_bar.winfo_children():
            w.destroy()
        t = self.T

        tk.Label(self._model_bar, text="Model:", font=("Consolas", 8)).pack(
            side=tk.LEFT, padx=(10, 2), pady=8)

        # Combobox for model selection
        self._model_var = tk.StringVar(value=D.get("current_model") or "")
        self._model_combo = ttk.Combobox(
            self._model_bar, textvariable=self._model_var,
            width=38, font=("Consolas", 8),
        )
        self._model_combo["values"] = D.get("known_models") or []
        self._model_combo.pack(side=tk.LEFT, padx=4, pady=6)
        self._model_combo.bind("<<ComboboxSelected>>", self._on_model_select)
        self._model_combo.bind("<Return>", self._on_model_enter)

        tk.Button(
            self._model_bar, text="＋", font=("Consolas", 9),
            relief=tk.FLAT, cursor="hand2", padx=4,
            command=self._add_model_from_combo,
        ).pack(side=tk.LEFT)

        tk.Button(
            self._model_bar, text="⟳ Fetch", font=("Consolas", 8),
            relief=tk.FLAT, cursor="hand2", padx=6,
            command=self._fetch_models,
        ).pack(side=tk.LEFT, padx=4)

        # Profile selector
        tk.Label(self._model_bar, text="│", font=("Consolas", 9)).pack(
            side=tk.LEFT, padx=6)
        tk.Label(self._model_bar, text="Profile:", font=("Consolas", 8)).pack(
            side=tk.LEFT, padx=(0, 2))

        profiles = D.get_profiles()
        self._profile_var = tk.StringVar(value=D.get("current_profile") or "default")
        self._profile_combo = ttk.Combobox(
            self._model_bar, textvariable=self._profile_var,
            width=14, font=("Consolas", 8),
        )
        self._profile_combo["values"] = list(profiles.keys())
        self._profile_combo.pack(side=tk.LEFT, padx=4)
        self._profile_combo.bind("<<ComboboxSelected>>", self._on_profile_select)

        tk.Button(
            self._model_bar, text="✎", font=("Consolas", 9),
            relief=tk.FLAT, cursor="hand2", padx=4,
            command=self._edit_profile,
        ).pack(side=tk.LEFT)

        self._apply_model_bar_theme()

    def _apply_model_bar_theme(self):
        t = self.T
        self._model_bar.configure(bg=t["bg_secondary"])
        for w in self._model_bar.winfo_children():
            if isinstance(w, tk.Label):
                w.configure(bg=t["bg_secondary"], fg=t["text_dim"])
            elif isinstance(w, tk.Button):
                w.configure(bg=t["bg_secondary"], fg=t["accent"],
                             activebackground=t["bg_card"],
                             activeforeground=t["accent"])

    def _build_sidebar(self):
        t = self.T
        self._sidebar.configure(bg=t["sidebar"])

        # Section: Quick Actions
        self._sb_header("QUICK ACTIONS")
        sb_items = [
            ("🗑  Clear Chat",       self._clear_chat),
            ("📋 Copy Last Reply",   self._copy_last),
            ("📁 Open Log",          self._open_log),
            ("🔄 New Session",       self._new_session),
            ("📂 Load File",         self._load_file),
            ("📦 Load Toolkit",      self._load_toolkit),
        ]
        self._sidebar_btns = []
        for lbl, cmd in sb_items:
            b = tk.Button(
                self._sidebar, text=lbl, command=cmd,
                font=t["font_small"], relief=tk.FLAT, cursor="hand2",
                anchor=tk.W, padx=10, pady=5,
            )
            b.pack(fill=tk.X, padx=6, pady=1)
            self._sidebar_btns.append(b)

        # Section: Server control
        self._sb_sep()
        self._sb_header("SERVER")
        self._start_server_btn = tk.Button(
            self._sidebar, text="▶ Start Server",
            command=self._start_server,
            font=t["font_small"], relief=tk.FLAT, cursor="hand2",
            anchor=tk.W, padx=10, pady=5,
        )
        self._start_server_btn.pack(fill=tk.X, padx=6, pady=1)
        self._sidebar_btns.append(self._start_server_btn)

        if not is_admin():
            self._admin_btn = tk.Button(
                self._sidebar, text="🔒 Restart as Admin",
                command=self._do_restart_admin,
                font=t["font_small"], relief=tk.FLAT, cursor="hand2",
                anchor=tk.W, padx=10, pady=5,
            )
            self._admin_btn.pack(fill=tk.X, padx=6, pady=1)
            self._sidebar_btns.append(self._admin_btn)

        # Section: TTS
        self._sb_sep()
        self._sb_header("VOICE")
        self._tts_var = tk.BooleanVar(value=D.get_tts().get("enabled", False))
        tk.Checkbutton(
            self._sidebar, text=" 🔊 TTS Read-aloud",
            variable=self._tts_var, command=self._toggle_tts,
            font=t["font_small"], anchor=tk.W,
        ).pack(fill=tk.X, padx=10, pady=2)

        self._auto_read_var = tk.BooleanVar(value=D.get_tts().get("auto_read", False))
        tk.Checkbutton(
            self._sidebar, text=" Auto-read replies",
            variable=self._auto_read_var, command=self._toggle_auto_read,
            font=t["font_small"], anchor=tk.W,
        ).pack(fill=tk.X, padx=10, pady=1)

        self._stop_tts_btn = tk.Button(
            self._sidebar, text="⏹ Stop TTS",
            command=self._stop_tts,
            font=t["font_small"], relief=tk.FLAT, cursor="hand2",
            anchor=tk.W, padx=10, pady=3,
        )
        self._stop_tts_btn.pack(fill=tk.X, padx=6, pady=1)
        self._sidebar_btns.append(self._stop_tts_btn)

        tk.Button(
            self._sidebar, text="🎙 Voice Settings",
            command=self._open_voice_settings,
            font=t["font_small"], relief=tk.FLAT, cursor="hand2",
            anchor=tk.W, padx=10, pady=3,
        ).pack(fill=tk.X, padx=6, pady=1)

        self._sb_sep()
        self._sb_header("SYSTEM")
        frame_res = tk.Frame(self._sidebar, bg=t["sidebar"])
        frame_res.pack(fill=tk.X, padx=10, pady=5)
        
        # CPU
        self._cpu_label = tk.Label(frame_res, text="CPU: --%", font=("Consolas", 8), anchor=tk.W, bg=t["sidebar"], fg=t["text"])
        self._cpu_label.pack(fill=tk.X)
        self._cpu_bar = ttk.Progressbar(frame_res, length=100, mode='determinate')
        self._cpu_bar.pack(fill=tk.X, pady=(0,4))
        
        # RAM
        self._ram_label = tk.Label(frame_res, text="RAM: --%", font=("Consolas", 8), anchor=tk.W, bg=t["sidebar"], fg=t["text"])
        self._ram_label.pack(fill=tk.X)
        self._ram_bar = ttk.Progressbar(frame_res, length=100, mode='determinate')
        self._ram_bar.pack(fill=tk.X, pady=(0,4))
        
        # --- NEW: GPU ---
        self._gpu_label = tk.Label(frame_res, text="GPU: --%", font=("Consolas", 8), anchor=tk.W, bg=t["sidebar"], fg=t["text"])
        self._gpu_label.pack(fill=tk.X)
        self._gpu_bar = ttk.Progressbar(frame_res, length=100, mode='determinate')
        self._gpu_bar.pack(fill=tk.X)

        self._update_resources()
        
        # Status indicators
        self._sb_sep()
        self._thinking_lbl = tk.Label(
            self._sidebar, text="", font=("Consolas", 8),
            wraplength=186, justify=tk.LEFT, anchor=tk.NW,
        )
        self._thinking_lbl.pack(fill=tk.X, padx=10, pady=4)

        # Style all checkbuttons
        self._sidebar_checks = [
            w for w in self._sidebar.winfo_children()
            if isinstance(w, tk.Checkbutton)
        ]

    def _sb_header(self, text: str):
        t = self.T
        lbl = tk.Label(self._sidebar, text=text, font=("Consolas", 7, "bold"),
                       anchor=tk.W)
        lbl.pack(fill=tk.X, padx=10, pady=(10, 2))
        self._sidebar_headers = getattr(self, "_sidebar_headers", [])
        self._sidebar_headers.append(lbl)

    def _sb_sep(self):
        t = self.T
        f = tk.Frame(self._sidebar, height=1)
        f.pack(fill=tk.X, padx=6, pady=2)
        self._sidebar_seps = getattr(self, "_sidebar_seps", [])
        self._sidebar_seps.append(f)

    def _build_input_bar(self):
        t = self.T
        self._inp_bar.configure(bg=t["bg_secondary"])

        left = tk.Frame(self._inp_bar, bg=t["bg_secondary"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 6), pady=10)

        self._input_box = tk.Text(
            left, height=3, wrap=tk.WORD, relief=tk.FLAT,
            font=t["font_mono"], padx=8, pady=6,
        )
        self._input_box.pack(fill=tk.BOTH, expand=True)
        self._input_box.bind("<Return>",       self._on_enter)
        self._input_box.bind("<Shift-Return>", lambda e: None)

        right = tk.Frame(self._inp_bar, bg=t["bg_secondary"])
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 12), pady=10)

        self._send_btn = RoundedButton(
            right, text="SEND  ▶", command=self._send,
            bg=t["button"], fg=t["button_text"],
            hover_bg=t["button_hover"],
            outer_bg=t["bg_secondary"],
            width=110, height=34, radius=8,
            font_spec=("Consolas", 9, "bold"),
        )
        self._send_btn.pack(pady=(0, 4))

        # PTT button (hold to speak)
        self._ptt_btn = RoundedButton(
            right, text="🎤 HOLD", command=None,
            bg=t["bg_card"], fg=t["text_dim"],
            hover_bg=t["border_light"],
            outer_bg=t["bg_secondary"],
            width=110, height=28, radius=8,
            font_spec=("Consolas", 8, "bold"),
        )
        self._ptt_btn.pack()
        self._ptt_btn.bind("<ButtonPress-1>",   self._ptt_press)
        self._ptt_btn.bind("<ButtonRelease-1>", self._ptt_release)

    # ─── Tag setup ──────────────────────────────────────────────────────────

    def _setup_tags(self):
        t = self.T
        h = self._chat_hist
        f_ui   = t["font_ui"]
        f_mono = t["font_mono"]

        h.tag_configure("user_hdr",   foreground=t["accent2"],     font=("Consolas", 8, "bold"), spacing1=14)
        h.tag_configure("user_body",  foreground=t["text"],        background=t["user_bubble"], font=f_ui,
                        lmargin1=10, lmargin2=10, rmargin=8, spacing3=6)
        h.tag_configure("ai_hdr",     foreground=t["accent"],      font=("Consolas", 8, "bold"), spacing1=14)
        h.tag_configure("ai_body",    foreground=t["text"],        background=t["ai_bubble"],   font=f_ui,
                        lmargin1=10, lmargin2=10, rmargin=8, spacing3=6)
        h.tag_configure("tool_hdr",   foreground=t["accent3"],     font=("Consolas", 8, "bold"), spacing1=8)
        h.tag_configure("tool_body",  foreground="#99ffcc",        background=t["tool_bubble"], font=f_mono,
                        lmargin1=10, lmargin2=10, rmargin=8, spacing3=4)
        h.tag_configure("error",      foreground="#ff7777",        background=t["error_bubble"],font=f_mono,
                        lmargin1=10, lmargin2=10, spacing3=4)
        h.tag_configure("sys",        foreground=t["sys_text"],    font=("Consolas", 8, "italic"), spacing1=2)
        h.tag_configure("streaming",  foreground=t["text"],        background=t["ai_bubble"],   font=f_ui,
                        lmargin1=10, lmargin2=10, rmargin=8)
        h.configure(bg=t["bg"], fg=t["text"], insertbackground=t["accent"])

    # ─── Theme application ──────────────────────────────────────────────────

    def _apply_theme(self, name: str):
        self._theme_name = name
        self.T = THEMES.get(name, THEMES[DEFAULT_THEME])
        t = self.T
        D.set("current_theme", name)

        self.configure(bg=t["bg"])
        self._top.configure(bg=t["bg_secondary"])
        self._sep.configure(bg=t["border"])
        self._body.configure(bg=t["bg"])
        self._sidebar.configure(bg=t["sidebar"])
        self._chat_col.configure(bg=t["bg"])
        self._inp_bar.configure(bg=t["bg_secondary"])
        self._stat_bar.configure(bg=t["bg_secondary"])

        self._title_lbl.configure(bg=t["bg_secondary"], fg=t["accent"], font=t["font_title"])
        self._status_lbl.configure(bg=t["bg_secondary"], fg="#00ff88")
        self._admin_lbl.configure(bg=t["bg_secondary"],
                                  fg=admin_status_color())
        self._top_btn_frame.configure(bg=t["bg_secondary"])
        for w in self._top_btns:
            w.configure(bg=t["bg_secondary"], fg=t["text_dim"],
                        activebackground=t["bg_card"], activeforeground=t["accent"])

        # Model bar
        self._apply_model_bar_theme()

        # Sidebar
        for h in getattr(self, "_sidebar_headers", []):
            h.configure(bg=t["sidebar"], fg=t["text_muted"])
        for s in getattr(self, "_sidebar_seps", []):
            s.configure(bg=t["border"])
        for b in self._sidebar_btns:
            b.configure(bg=t["sidebar"], fg=t["text"],
                        activebackground=t["sidebar_hover"], activeforeground=t["accent"])
        for c in getattr(self, "_sidebar_checks", []):
            c.configure(bg=t["sidebar"], fg=t["text"],
                        selectcolor=t["bg_card"], activebackground=t["sidebar"])
        self._thinking_lbl.configure(bg=t["sidebar"], fg=t["accent"])

        # Input
        self._input_box.configure(bg=t["bg_input"], fg=t["text"],
                                  insertbackground=t["accent"])
        self._send_btn.configure(bg=t["button"], fg=t["button_text"],
                                 outer_bg=t["bg_secondary"])
        self._ptt_btn.configure(bg=t["bg_card"], fg=t["text_dim"],
                                outer_bg=t["bg_secondary"])

        # Status bar
        self._stat_left.configure(bg=t["bg_secondary"], fg=t["text_dim"])
        self._stat_right.configure(bg=t["bg_secondary"], fg=t["text_dim"])

        # ttk Combobox style
        style = ttk.Style(self)
        style.configure("TCombobox",
                        fieldbackground=t["bg_input"],
                        background=t["bg_card"],
                        foreground=t["text"],
                        arrowcolor=t["accent"],
                        selectbackground=t["bg_card"],
                        selectforeground=t["text"])

        # Re-setup chat tags
        self._setup_tags()
        self._update_statusbar()

    # ─── Model bar interactions ──────────────────────────────────────────────

    def _on_model_select(self, _=None):
        model = self._model_var.get().strip()
        if model:
            D.set("current_model", model)
            D.add_model(model)
            self._append_msg("sys", f"Model set: {model}. Restarting server...")
            self._update_statusbar()
            self._do_start_server() # Auto-restart server with new model

    def _on_model_enter(self, _=None):
        self._add_model_from_combo()

    def _add_model_from_combo(self):
        model = self._model_var.get().strip()
        if model:
            D.add_model(model)
            D.set("current_model", model)
            self._model_combo["values"] = D.get("known_models") or []
            self._append_msg("sys", f"Model saved: {model}")
            self._update_statusbar()

    def _fetch_models(self):
        """Scan the local models_dir for .gguf files."""
        cfg = D.get_server()
        models_dir = cfg.get("models_dir", "")
        
        if not models_dir or not os.path.isdir(models_dir):
            self._append_msg("error", "Models directory not set or invalid. Check Settings.")
            return

        import glob
        pattern = os.path.join(models_dir, "*.gguf")
        files = glob.glob(pattern)
        model_names = [os.path.basename(f) for f in files]

        if model_names:
            D.set("known_models", model_names)
            self._refresh_model_combo()
            self._append_msg("sys", f"Found {len(model_names)} model(s) in {models_dir}.")
        else:
            self._append_msg("sys", f"No .gguf files found in {models_dir}.")

    def _refresh_model_combo(self):
        self._model_combo["values"] = D.get("known_models") or []

    def _on_profile_select(self, _=None):
        pid = self._profile_var.get().strip()
        D.set("current_profile", pid)
        profile = D.get_current_profile()
        # If profile has a theme preference, apply it
        if profile.get("theme"):
            self._apply_theme(profile["theme"])
        self._append_msg("sys", f"Profile: {profile.get('name', pid)}")

    # ─── Welcome ────────────────────────────────────────────────────────────

    def _show_welcome(self):
        now = datetime.datetime.now().strftime("%A, %d %B %Y  %H:%M")
        profile = D.get_current_profile()
        self._append_msg("ai", (
            f"System initialised. Good day, {profile.get('name', 'sir')}.\n"
            f"Date: {now}\n\n"
            f"V.I.N.C.E is online and at your disposal.\n"
            f"Model: {D.get('current_model')} | Theme: {self._theme_name}"
        ))
        self._append_msg("sys",
            "Enter to send · Shift+Enter for newline · Hold 🎤 to speak")

    # ─── Message display ─────────────────────────────────────────────────────

    def _append_msg(self, kind: str, text: str):
        """Thread-safe message append."""
        self.after(0, self._append_msg_main, kind, text)

    def _append_msg_main(self, kind: str, text: str):
        h = self._chat_hist
        h.configure(state=tk.NORMAL)
        if kind == "user":
            profile = D.get_current_profile()
            h.insert(tk.END, f"  {profile.get('avatar','👤')} {profile.get('name','YOU')}\n", "user_hdr")
            h.insert(tk.END, f"  {text}\n", "user_body")
        elif kind == "ai":
            h.insert(tk.END, "  ◈ V.I.N.C.E\n", "ai_hdr")
            h.insert(tk.END, f"  {text}\n", "ai_body")
        elif kind == "tool":
            h.insert(tk.END, "  ⚙ TOOL\n", "tool_hdr")
            h.insert(tk.END, f"  {text}\n", "tool_body")
        elif kind == "error":
            h.insert(tk.END, f"  ⚠ {text}\n", "error")
        elif kind == "sys":
            h.insert(tk.END, f"  ○ {text}\n", "sys")
        h.configure(state=tk.DISABLED)
        h.see(tk.END)

    def _start_stream_bubble(self):
        self.after(0, self._start_stream_bubble_main)

    def _start_stream_bubble_main(self):
        h = self._chat_hist
        h.configure(state=tk.NORMAL)
        h.insert(tk.END, "  ◈ V.I.N.C.E\n", "ai_hdr")
        h.insert(tk.END, "  ", "streaming")
        h.configure(state=tk.DISABLED)
        h.see(tk.END)

    def _append_token(self, tok: str):
        self.after(0, self._append_token_main, tok)

    def _append_token_main(self, tok: str):
        h = self._chat_hist
        h.configure(state=tk.NORMAL)
        h.insert(tk.END, tok, "streaming")
        h.configure(state=tk.DISABLED)
        h.see(tk.END)
        self._stream_tokens += 1
        self.after(0, self._stat_right.configure,
                   {"text": f"tokens: ~{self._stream_tokens}"})

    def _close_stream_bubble(self):
        self.after(0, self._close_stream_bubble_main)

    def _close_stream_bubble_main(self):
        h = self._chat_hist
        h.configure(state=tk.NORMAL)
        h.insert(tk.END, "\n")
        h.configure(state=tk.DISABLED)

    # ─── Sending ────────────────────────────────────────────────────────────

    def _on_enter(self, event):
        if event.state & 0x1:
            return
        self._send()
        return "break"

    def _send(self, text: str = ""):
        if self._is_thinking:
            return
        msg = text or self._input_box.get("1.0", tk.END).strip()
        if not msg:
            return
        self._input_box.delete("1.0", tk.END)
        self._append_msg("user", msg)
        self._set_thinking(True)
        self._stream_tokens = 0
        self._last_response = ""
        stream_buf = []

        self._start_stream_bubble()

        def on_token(tok):
            stream_buf.append(tok)
            self._last_response += tok
            self._append_token(tok)

        def on_tool_call(action, params):
            self._close_stream_bubble()
            self._append_msg("tool", f"Calling: {action}\nParams: {params}")
            self.after(0, self._thinking_lbl.configure,
                       {"text": f"⚙ Running: {action}..."})
            self.after(50, self._start_stream_bubble)
            stream_buf.clear()

        def on_tool_result(action, result):
            preview = result[:400] + ("..." if len(result) > 400 else "")
            self._append_msg("tool", f"Result [{action}]:\n{preview}")

        def on_done(final):
            self._close_stream_bubble()
            if not stream_buf:
                self._append_msg("ai", final)
                self._last_response = final
            self._set_thinking(False)
            self.after(0, self._thinking_lbl.configure, {"text": ""})
            # Auto-read TTS
            cfg = D.get_tts()
            if cfg.get("auto_read") and cfg.get("enabled"):
                self._tts.speak(self._last_response)

        def on_error(err):
            self._close_stream_bubble()
            self._append_msg("error", err)
            self._set_thinking(False)
            self.after(0, self._thinking_lbl.configure, {"text": ""})

        self.llm.chat(msg,
                      on_token=on_token,
                      on_tool_call=on_tool_call,
                      on_tool_result=on_tool_result,
                      on_done=on_done,
                      on_error=on_error)

    def _set_thinking(self, state: bool):
        self.after(0, self._set_thinking_main, state)

    def _set_thinking_main(self, state: bool):
        self._is_thinking = state
        if state:
            self._send_btn.configure(text="...")
            self._send_btn.configure(state=tk.DISABLED)
            self._status_lbl.configure(text="● THINKING", fg="#ffaa00")
            self._thinking_lbl.configure(text="Processing")
            # Start dot animation
            self._thinking_dots = 0
            self._animate_thinking()
        else:
            self._send_btn.configure(text="SEND  ▶")
            self._send_btn.configure(state=tk.NORMAL)
            self._status_lbl.configure(text="● ONLINE", fg="#00ff88")
            self._thinking_lbl.configure(text="")

    def _animate_thinking(self):
        if not self._is_thinking:
            return
        dots = "." * (self._thinking_dots % 4)
        self._thinking_lbl.configure(text=f"Processing{dots}")
        self._thinking_dots += 1
        self.after(500, self._animate_thinking)
    # ─── PTT ────────────────────────────────────────────────────────────────

    def _init_voice(self):
        try:
            self._voice_input = vi_module.VoiceInput(
                on_result=self._on_stt_result,
                on_error=self._on_stt_error,
                on_listening=self._on_stt_listening,
            )
            if not self._voice_input.available:
                log_system("STT not available (install speechrecognition + pyaudio)")
        except Exception as e:
            log_system(f"Voice input init error: {e}")

    def _ptt_press(self, _=None):
        if not self._voice_input or not self._voice_input.available:
            self._append_msg("sys", "Voice input unavailable. Install: pip install SpeechRecognition pyaudio")
            return
        if not D.get_stt().get("enabled", False):
            self._append_msg("sys", "Voice input is disabled. Enable it in Voice Settings.")
            return
        self._ptt_held = True
        self._voice_input.start_recording()

    def _ptt_release(self, _=None):
        if self._ptt_held:
            self._ptt_held = False
            if self._voice_input:
                self._voice_input.stop_recording()

    def _on_stt_result(self, text: str):
        self.after(0, self._stt_to_input, text)

    def _stt_to_input(self, text: str):
        self._input_box.delete("1.0", tk.END)
        self._input_box.insert("1.0", text)
        cfg = D.get_stt()
        if cfg.get("auto_send", True):
            self._send()

    def _on_stt_error(self, err: str):
        self._append_msg("error", f"Voice input: {err}")

    def _on_stt_listening(self, listening: bool):
        t = self.T
        if listening:
            self.after(0, self._ptt_btn.configure, {"bg": "#ff4040"})
            self.after(0, self._ptt_btn.configure, {"fg": "#ffffff"})
            self.after(0, self._status_lbl.configure, {"text": "● LISTENING", "fg": "#ff6644"})
        else:
            self.after(0, self._ptt_btn.configure, {"bg": t["bg_card"]})
            self.after(0, self._ptt_btn.configure, {"fg": t["text_dim"]})
            self.after(0, self._status_lbl.configure, {"text": "● ONLINE", "fg": "#00ff88"})

    # ─── TTS controls ────────────────────────────────────────────────────────

    def _toggle_tts(self):
        enabled = self._tts_var.get()
        self._tts.set_enabled(enabled)
        self._append_msg("sys", f"TTS {'enabled' if enabled else 'disabled'}.")

    def _toggle_auto_read(self):
        D.set_tts({"auto_read": self._auto_read_var.get()})

    def _stop_tts(self):
        self._tts.stop()

    def _read_last(self):
        if self._last_response:
            self._tts.speak(self._last_response)

    # ─── Sidebar actions ────────────────────────────────────────────────────

    def _clear_chat(self):
        self._chat_hist.configure(state=tk.NORMAL)
        self._chat_hist.delete("1.0", tk.END)
        self._chat_hist.configure(state=tk.DISABLED)
        self._append_msg("sys", "Chat display cleared.")

    def _copy_last(self):
        if self._last_response:
            self.clipboard_clear()
            self.clipboard_append(self._last_response)
            self._append_msg("sys", "Last reply copied.")
        else:
            content = self._chat_hist.get("1.0", tk.END)
            idx = content.rfind("◈ V.I.N.C.E")
            if idx != -1:
                snippet = content[idx:].split("\n", 1)[-1].strip()[:3000]
                self.clipboard_clear()
                self.clipboard_append(snippet)
                self._append_msg("sys", "Last reply copied.")

    def _open_log(self):
        from config import LOG_FILE
        if os.path.exists(LOG_FILE):
            if os.name == "nt":
                os.startfile(LOG_FILE)
            else:
                os.system(f"xdg-open '{LOG_FILE}'")
        else:
            messagebox.showinfo("Log", "Log file not found yet.")

    def _new_session(self):
        if messagebox.askyesno("New Session", "Clear conversation history and log?"):
            self.llm.clear_history()
            clear_log()
            self._clear_chat()
            self._show_welcome()

    def _load_file(self):
        path = filedialog.askopenfilename(title="Load file as context")
        if path:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(10000)
                self._input_box.insert(tk.END,
                    f"[File: {os.path.basename(path)}]\n{content}")
                self._append_msg("sys", f"File loaded into input: {path}")
            except Exception as e:
                self._append_msg("error", str(e))

    def _load_toolkit(self):
        path = filedialog.askopenfilename(
            title="Load Python Toolkit",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        )
        if path:
            success, msg = toolkit_loader.load_toolkit(path)
            self._append_msg("sys" if success else "error", msg)
            if success:
                # Refresh tools summary
                self._append_msg("sys",
                    f"New tools available: {', '.join(TOOL_REGISTRY.keys())}")

    def _start_server(self):
        self._open_server_settings()

    def _do_restart_admin(self):
        if messagebox.askyesno("Restart as Admin",
                               "Restart VINCE with administrator privileges?\n"
                               "This will close the current window."):
            restart_as_admin()

    # ─── Menu windows ────────────────────────────────────────────────────────

    def _open_modules(self):
        txt = (
            "BUILT-IN MODULES\n"
            "───────────────────────────────────────────\n"
            "• search_online      DuckDuckGo web search\n"
            "• scrape_website     Fetch & parse any URL\n"
            "• read_file          Read files from disk\n"
            "• write_file         Write / create files\n"
            "• delete_file ⚠      Delete files (asks first)\n"
            "• find_file          Find files by name/glob\n"
            "• list_directory     Browse folder contents\n"
            "• calculate          Safe math evaluation\n"
            "• run_command ⚠      Execute shell commands\n"
            "• run_app            Launch applications\n"
            "• read_own_files     Inspect VINCE source\n"
            "• get_system_info    OS/CPU/RAM/disk stats\n"
            "• clipboard_read     Read clipboard\n"
            "• clipboard_write    Write clipboard\n"
            "• http_request       HTTP GET/POST\n"
            "• hash_file          MD5/SHA1/SHA256 of file\n"
            "\nFUTURE MODULES (planned)\n"
            "───────────────────────────────────────────\n"
            "• More voice/STT languages\n"
            "• Screen capture & OCR\n"
            "• Email/calendar integration\n"
            "• Self-made tool generation\n"
        )
        self._popup("Modules", txt, 480, 500)

    def _open_tools(self):
        self._popup("Available Tools", get_tools_summary(), 520, 480)

    def _open_help(self):
        txt = (
            "V.I.N.C.E — HELP\n"
            "══════════════════════════════════════════\n\n"
            "V.I.N.C.E = Virtually Intelligent Neural Cognitive Engine\n"
            "KEYBOARD\n"
            "  Enter         → Send message\n"
            "  Shift+Enter   → New line in input\n\n"
            "TOOLBAR\n"
            "  Modules  → Built-in capabilities overview\n"
            "  Tools    → All registered tools\n"
            "  Themes   → Switch visual theme\n"
            "  Settings → LLM, server, and app settings\n"
            "  Help     → This window\n\n"
            "SIDEBAR\n"
            "  Load Toolkit → Load a .py file with custom tools\n"
            "  Start Server → Launch llama-server subprocess\n"
            "  Restart as Admin → Elevate privileges (Windows)\n"
            "  TTS controls → Read-aloud and auto-read toggles\n\n"
            "VOICE INPUT (PTT)\n"
            "  Hold 🎤 HOLD button → microphone records\n"
            "  Release → transcribed text appears; sends if auto-send on\n"
            "  Enable in: Voice Settings (sidebar) or Settings panel\n\n"
            "MODEL SELECTOR\n"
            "  Pick from dropdown or type any model name + press ＋\n"
            "  ⟳ Fetch → auto-discover models from running server\n\n"
            "PROFILES\n"
            "  Each profile has a name, avatar, and custom system prompt.\n"
            "  Click ✎ to edit the current profile.\n\n"
            "TOOLKITS\n"
            "  Drop any .py file with @register_tool functions into\n"
            "  the toolkits/ folder — auto-loaded on startup.\n"
            "  Or use 📦 Load Toolkit in the sidebar at runtime.\n\n"
            "ADMIN\n"
            "  [USER] / [ADMIN] shown in the top bar.\n"
            "  'Restart as Admin' re-launches with elevated privileges.\n"
            "  run_command and delete_file always ask for confirmation.\n"
        )
        self._popup("Help", txt, 560, 580)

    def _open_themes(self):
        win = self._make_window("Themes", 320, 280)
        tk.Label(win, text="SELECT THEME", font=("Consolas", 10, "bold"),
                 bg=self.T["bg"], fg=self.T["accent"]).pack(pady=14)
        for name in THEMES:
            def _sel(n=name):
                self._apply_theme(n)
                win.destroy()
                self._append_msg("sys", f"Theme: {n}")
            RoundedButton(
                win, text=name, command=_sel,
                bg=THEMES[name]["accent"],
                fg=THEMES[name]["button_text"],
                outer_bg=self.T["bg"],
                width=240, height=34, radius=8,
                font_spec=("Segoe UI", 9),
            ).pack(pady=4)

    def _open_settings(self):
        win = self._make_window("Settings", 560, 640)
        t = self.T

        nb = ttk.Notebook(win)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # ── LLM Tab ──────────────────────────────────────────────────────────
        llm_frame = tk.Frame(nb, bg=t["bg"])
        nb.add(llm_frame, text="  LLM  ")
        cfg_llm = D.get_llm()

        llm_fields = [
            ("Base URL",         "base_url",      cfg_llm.get("base_url", "http://localhost:8080/v1")),
            ("Temperature",      "temperature",   str(cfg_llm.get("temperature", 0.7))),
            ("Max Tokens",       "max_tokens",    str(cfg_llm.get("max_tokens", 4096))),
            ("Top P",            "top_p",         str(cfg_llm.get("top_p", 0.95))),
            ("Repeat Penalty",   "repeat_penalty",str(cfg_llm.get("repeat_penalty", 1.1))),
            ("Max Ctx Messages", "max_ctx_messages", str(cfg_llm.get("max_ctx_messages", 60))),
            ("Max Log Lines",    "max_log_lines", str(cfg_llm.get("max_log_lines", 80))),
            ("Max Tool Iters",   "max_tool_iters",str(cfg_llm.get("max_tool_iters", 8))),
        ]
        llm_entries = self._build_settings_form(llm_frame, llm_fields)

        stream_var = tk.BooleanVar(value=cfg_llm.get("stream", True))
        tk.Checkbutton(llm_frame, text="Streaming", variable=stream_var,
                       bg=t["bg"], fg=t["text"], selectcolor=t["bg_card"],
                       activebackground=t["bg"],
                       font=t["font_ui"]).pack(anchor=tk.W, padx=20, pady=4)

        def _apply_llm():
            try:
                D.set_llm({
                    "base_url":       llm_entries["base_url"].get(),
                    "temperature":    float(llm_entries["temperature"].get()),
                    "max_tokens":     int(llm_entries["max_tokens"].get()),
                    "top_p":          float(llm_entries["top_p"].get()),
                    "repeat_penalty": float(llm_entries["repeat_penalty"].get()),
                    "max_ctx_messages": int(llm_entries["max_ctx_messages"].get()),
                    "max_log_lines":  int(llm_entries["max_log_lines"].get()),
                    "max_tool_iters": int(llm_entries["max_tool_iters"].get()),
                    "stream":         stream_var.get(),
                })
                self.llm._make_client()
                self._append_msg("sys", "LLM settings applied.")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=win)

        self._settings_apply_btn(llm_frame, _apply_llm)

        # ── Server Tab ───────────────────────────────────────────────────────
        srv_frame = tk.Frame(nb, bg=t["bg"])
        nb.add(srv_frame, text=" Server ")
        cfg_srv = D.get_server()

        srv_fields = [
            ("EXE Path",       "exe_path",   cfg_srv.get("exe_path", "")),
            ("Models Dir",     "models_dir", cfg_srv.get("models_dir", "")), # <-- Changed this line
            ("Port",           "port",       str(cfg_srv.get("port", 8080))),
            ("Context Size",   "ctx_size",   str(cfg_srv.get("ctx_size", 32768))),
            ("GPU Layers",     "gpu_layers", str(cfg_srv.get("gpu_layers", 99))),
            ("Extra Args",     "extra_args", cfg_srv.get("extra_args", "")),
        ]
        srv_entries = self._build_settings_form(srv_frame, srv_fields)

        auto_var = tk.BooleanVar(value=cfg_srv.get("auto_start", False))
        tk.Checkbutton(srv_frame, text="Auto-start server on launch",
                       variable=auto_var,
                       bg=t["bg"], fg=t["text"], selectcolor=t["bg_card"],
                       activebackground=t["bg"],
                       font=t["font_ui"]).pack(anchor=tk.W, padx=20, pady=4)

        def _apply_srv():
            try:
                D.set_server({
                    "exe_path":   srv_entries["exe_path"].get().strip(),
                    "models_dir": srv_entries["models_dir"].get().strip(), # <-- Changed this line
                    "port":       int(srv_entries["port"].get()),
                    "ctx_size":   int(srv_entries["ctx_size"].get()),
                    "gpu_layers": int(srv_entries["gpu_layers"].get()),
                    "extra_args": srv_entries["extra_args"].get().strip(),
                    "auto_start": auto_var.get(),
                })
                self._append_msg("sys", "Server settings saved.")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=win)

        def _start_now():
            _apply_srv()
            #self._do_start_server()

        self._settings_apply_btn(srv_frame, _apply_srv, extra_label="▶ Start Now",
                                 extra_cmd=_start_now)

        # ── Voice Tab ────────────────────────────────────────────────────────
        voice_frame = tk.Frame(nb, bg=t["bg"])
        nb.add(voice_frame, text=" Voice ")
        self._build_voice_tab(voice_frame)

        # Style notebook
        style = ttk.Style(self)
        style.configure("TNotebook",        background=t["bg"])
        style.configure("TNotebook.Tab",    background=t["bg_card"],
                        foreground=t["text_dim"], padding=[10, 4])
        style.map("TNotebook.Tab",          background=[("selected", t["bg"])],
                  foreground=[("selected", t["accent"])])

    def _open_voice_settings(self):
        win = self._make_window("Voice Settings", 500, 480)
        self._build_voice_tab(win)

    def _build_voice_tab(self, parent):
        t = self.T
        cfg_tts = D.get_tts()
        cfg_stt = D.get_stt()

        # TTS section
        tk.Label(parent, text="TEXT-TO-SPEECH", font=("Consolas", 9, "bold"),
                 bg=t["bg"], fg=t["accent"]).pack(anchor=tk.W, padx=20, pady=(14, 4))

        tts_fields = [
            ("Rate (words/min)", "rate",   str(cfg_tts.get("rate", 175))),
            ("Volume (0.0–1.0)", "volume", str(cfg_tts.get("volume", 1.0))),
        ]
        tts_entries = self._build_settings_form(parent, tts_fields)

        # Voice selector
        tk.Label(parent, text="Voice:", bg=t["bg"], fg=t["text"],
                 font=t["font_ui"]).pack(anchor=tk.W, padx=20)
        voices = self._tts.get_voices()
        voice_names = [v["name"] for v in voices]
        cur_vid = cfg_tts.get("voice_id", "")
        cur_name = next((v["name"] for v in voices if v["id"] == cur_vid),
                        voice_names[0] if voice_names else "")
        voice_var = tk.StringVar(value=cur_name)
        vcb = ttk.Combobox(parent, textvariable=voice_var,
                           values=voice_names, width=40, font=("Consolas", 9))
        vcb.pack(anchor=tk.W, padx=20, pady=4)

        def _apply_tts():
            try:
                rate   = int(tts_entries["rate"].get())
                volume = float(tts_entries["volume"].get())
                vname  = voice_var.get()
                vid    = next((v["id"] for v in voices if v["name"] == vname), "")
                self._tts.set_rate(rate)
                self._tts.set_volume(volume)
                if vid:
                    self._tts.set_voice(vid)
                self._append_msg("sys", "TTS settings applied.")
                self._tts.speak("Voice settings applied.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        self._settings_apply_btn(parent, _apply_tts)

        # STT section
        tk.Label(parent, text="SPEECH RECOGNITION (PTT)", font=("Consolas", 9, "bold"),
                 bg=t["bg"], fg=t["accent"]).pack(anchor=tk.W, padx=20, pady=(18, 4))

        stt_enabled_var = tk.BooleanVar(value=cfg_stt.get("enabled", False))
        tk.Checkbutton(parent, text="Enable voice input (PTT)",
                       variable=stt_enabled_var,
                       bg=t["bg"], fg=t["text"], selectcolor=t["bg_card"],
                       activebackground=t["bg"],
                       font=t["font_ui"]).pack(anchor=tk.W, padx=20)

        auto_send_var = tk.BooleanVar(value=cfg_stt.get("auto_send", True))
        tk.Checkbutton(parent, text="Auto-send after speaking",
                       variable=auto_send_var,
                       bg=t["bg"], fg=t["text"], selectcolor=t["bg_card"],
                       activebackground=t["bg"],
                       font=t["font_ui"]).pack(anchor=tk.W, padx=20)

        stt_fields = [("Energy Threshold", "energy",
                        str(cfg_stt.get("energy_threshold", 300)))]
        stt_entries = self._build_settings_form(parent, stt_fields)

        def _apply_stt():
            D.set_stt({
                "enabled":          stt_enabled_var.get(),
                "auto_send":        auto_send_var.get(),
                "energy_threshold": int(stt_entries["energy"].get()),
            })
            self._append_msg("sys", "STT settings saved.")

        self._settings_apply_btn(parent, _apply_stt)

    def _open_server_settings(self):
        """Quick Start Server dialog that reads existing server config."""
        cfg = D.get_server()
        if not cfg.get("exe_path") or not cfg.get("model_path"):
            if not messagebox.askyesno("Server Config Missing",
                                       "No server EXE/model path configured.\n"
                                       "Open Settings → Server tab to configure first.\n\n"
                                       "Open Settings now?"):
                return
            self._open_settings()
            return
        self._do_start_server()

    def _do_start_server(self):   #############################
            """Launch llama-server as a subprocess with the dynamically selected model."""
            cfg = D.get_server()
            exe = cfg.get("exe_path", "llama-server")
            models_dir = cfg.get("models_dir", "")
            current_model = D.get("current_model")

            if not exe or not models_dir or not current_model:
                self._append_msg("error", "Missing Server EXE, Models Directory, or Model selection. Check Settings.")
                return

            model_path = os.path.join(models_dir, current_model)
            
            if not os.path.exists(model_path):
                self._append_msg("error", f"Model file not found: {model_path}")
                return

            port  = str(cfg.get("port", 8080))
            ctx   = str(cfg.get("ctx_size", 32768))
            ngl   = str(cfg.get("gpu_layers", 99))
            extra = cfg.get("extra_args", "").split()

            cmd = [exe, "-m", model_path, "--port", port] + extra

            # Kill existing server if running
            if getattr(self, "_server_proc", None):
                self._append_msg("sys", "Stopping existing server...")
                self._server_proc.terminate()
                try:
                    self._server_proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._server_proc.kill()

            try:
                import subprocess
                self._server_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
                )
                self._append_msg("sys", f"Server started with {current_model} (PID {self._server_proc.pid}).")
            except Exception as e:
                self._append_msg("error", f"Failed to start server: {e}")

    def _edit_profile(self):
        pid     = D.get("current_profile") or "default"
        profile = D.get_current_profile()
        win     = self._make_window(f"Edit Profile — {pid}", 440, 420)
        t       = self.T

        tk.Label(win, text="PROFILE EDITOR", font=("Consolas", 10, "bold"),
                 bg=t["bg"], fg=t["accent"]).pack(pady=12)

        fields = [
            ("Name",   "name",   profile.get("name", "User")),
            ("Avatar", "avatar", profile.get("avatar", "👤")),
        ]
        entries = self._build_settings_form(win, fields)

        tk.Label(win, text="Extra System Context:", bg=t["bg"], fg=t["text"],
                 font=t["font_ui"]).pack(anchor=tk.W, padx=20, pady=(8, 2))
        sys_text = tk.Text(win, height=5, wrap=tk.WORD, relief=tk.FLAT,
                           bg=t["bg_input"], fg=t["text"],
                           font=("Consolas", 9), padx=8, pady=6)
        sys_text.pack(fill=tk.X, padx=20, pady=4)
        sys_text.insert("1.0", profile.get("system_extra", ""))

        tk.Label(win, text="User Backstory (loaded into system prompt):", bg=t["bg"], fg=t["text"],
                font=t["font_ui"]).pack(anchor=tk.W, padx=20, pady=(8,2))
        backstory_text = tk.Text(win, height=8, wrap=tk.WORD, relief=tk.FLAT,
                                bg=t["bg_input"], fg=t["text"],
                                font=("Consolas", 9), padx=8, pady=6)
        backstory_text.pack(fill=tk.X, padx=20, pady=4)
        backstory_text.insert("1.0", profile.get("user_backstory", ""))

        def load_backstory_from_file():
            from tkinter import filedialog
            path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
            if path:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    backstory_text.delete("1.0", tk.END)
                    backstory_text.insert("1.0", content)
                except Exception as e:
                    messagebox.showerror("Error", str(e))

        load_btn = tk.Button(win, text="Load from .txt file", command=load_backstory_from_file,
                            bg=t["button"], fg=t["button_text"], font=t["font_ui"], relief=tk.FLAT)
        load_btn.pack(anchor=tk.W, padx=20, pady=2)

        # In _save, include:
        updated["user_backstory"] = backstory_text.get("1.0", tk.END).strip()
        
        
        # Theme for this profile
        tk.Label(win, text="Theme preference:", bg=t["bg"], fg=t["text"],
                 font=t["font_ui"]).pack(anchor=tk.W, padx=20)
        theme_var = tk.StringVar(value=profile.get("theme", ""))
        tcb = ttk.Combobox(win, textvariable=theme_var,
                           values=[""] + list(THEMES.keys()), width=24)
        tcb.pack(anchor=tk.W, padx=20, pady=4)

        def _save():
            updated = {
                "name":         entries["name"].get().strip() or "User",
                "avatar":       entries["avatar"].get().strip() or "👤",
                "system_extra": sys_text.get("1.0", tk.END).strip(),
                "theme":        theme_var.get(),
                "created":      profile.get("created",
                                            datetime.datetime.now().strftime("%Y-%m-%d")),
            }
            D.save_profile(pid, updated)
            self._append_msg("sys", f"Profile '{pid}' saved.")
            win.destroy()

        def _new_profile():
            import uuid
            new_pid = f"profile_{uuid.uuid4().hex[:6]}"
            D.save_profile(new_pid, {
                "name": "New Profile", "avatar": "👤",
                "system_extra": "", "theme": "",
                "created": datetime.datetime.now().strftime("%Y-%m-%d"),
            })
            D.set("current_profile", new_pid)
            self._profile_var.set(new_pid)
            self._profile_combo["values"] = list(D.get_profiles().keys())
            self._append_msg("sys", f"Created profile: {new_pid}")
            win.destroy()

        def _del_profile():
            if pid == "default":
                messagebox.showwarning("Cannot Delete", "Cannot delete the default profile.")
                return
            if messagebox.askyesno("Delete Profile", f"Delete profile '{pid}'?"):
                D.delete_profile(pid)
                self._profile_combo["values"] = list(D.get_profiles().keys())
                self._profile_var.set("default")
                D.set("current_profile", "default")
                self._append_msg("sys", f"Profile '{pid}' deleted.")
                win.destroy()

        btn_row = tk.Frame(win, bg=t["bg"])
        btn_row.pack(pady=14)
        for lbl, cmd in [("💾 Save", _save), ("＋ New", _new_profile), ("🗑 Delete", _del_profile)]:
            tk.Button(btn_row, text=lbl, command=cmd,
                      bg=t["button"], fg=t["button_text"],
                      font=t["font_ui"], relief=tk.FLAT, cursor="hand2",
                      padx=12, pady=4).pack(side=tk.LEFT, padx=6)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _build_settings_form(self, parent, fields: list) -> dict:
        t = self.T
        entries = {}
        for label, key, default in fields:
            row = tk.Frame(parent, bg=t["bg"])
            row.pack(fill=tk.X, padx=20, pady=3)
            tk.Label(row, text=label, width=18, anchor=tk.W,
                     bg=t["bg"], fg=t["text"], font=t["font_ui"]).pack(side=tk.LEFT)
            e = tk.Entry(row, font=("Consolas", 9),
                         bg=t["bg_input"], fg=t["text"],
                         insertbackground=t["accent"],
                         relief=tk.FLAT, width=32)
            e.insert(0, default)
            e.pack(side=tk.LEFT, padx=6)
            entries[key] = e
            
        return entries

    def _settings_apply_btn(self, parent, cmd, extra_label=None, extra_cmd=None):
        t = self.T
        row = tk.Frame(parent, bg=t["bg"])
        row.pack(pady=10)
        tk.Button(row, text="Apply", command=cmd,
                  bg=t["button"], fg=t["button_text"],
                  font=t["font_ui"], relief=tk.FLAT, cursor="hand2",
                  padx=14, pady=4).pack(side=tk.LEFT, padx=6)
        if extra_label and extra_cmd:
            tk.Button(row, text=extra_label, command=extra_cmd,
                      bg=t["accent2"], fg=t["button_text"],
                      font=t["font_ui"], relief=tk.FLAT, cursor="hand2",
                      padx=14, pady=4).pack(side=tk.LEFT, padx=6)

    def _make_window(self, title: str, w: int, h: int) -> tk.Toplevel:
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry(f"{w}x{h}")
        win.configure(bg=self.T["bg"])
        win.transient(self)
        return win

    def _popup(self, title: str, body: str, w: int = 500, h: int = 460):
        win = self._make_window(title, w, h)
        tk.Label(win, text=title, font=("Consolas", 11, "bold"),
                 bg=self.T["bg"], fg=self.T["accent"]).pack(pady=10)
        txt = scrolledtext.ScrolledText(
            win, wrap=tk.WORD, bg=self.T["bg_card"], fg=self.T["text"],
            font=("Consolas", 9), relief=tk.FLAT, padx=12, pady=10,
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        txt.insert(tk.END, body)
        txt.configure(state=tk.DISABLED)

    def _confirm_dialog(self, title: str, message: str) -> bool:
        """
        Confirmation callback registered with tools.py.
        Called from a background thread — blocks that thread until user responds.
        """
        result  = [False]
        event   = threading.Event()

        def _ask():
            try:
                result[0] = messagebox.askyesno(title, message, parent=self)
            except Exception:
                result[0] = False
            finally:
                event.set()

        self.after(0, _ask)
        event.wait(timeout=120)   # wait up to 2 minutes for user response
        return result[0]

    def _update_statusbar(self):
        model = D.get("current_model") or "—"
        profile = D.get_current_profile()
        self._stat_left.configure(
            text=f"  {APP_TITLE} v{APP_VERSION}  │  {model}  │  "
                 f"{profile.get('name','?')}  │  {self._theme_name}"
        )

    # ─── Close ───────────────────────────────────────────────────────────────

    def _on_close(self):
        log_system("Application closed.")
        D.save()
        self.destroy()
