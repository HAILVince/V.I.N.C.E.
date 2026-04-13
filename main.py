"""
V.I.N.C.E — Virtually Intelligent Neural Cognitive Engine
Entry point.

Usage:
    python main.py

Requirements:
    pip install openai duckduckgo-search requests beautifulsoup4
    Optional: pip install pyttsx3 SpeechRecognition pyaudio psutil

    llama.cpp server running (or configure auto-start in Settings → Server).
"""

import sys
import os
import threading

# ── Make sure imports resolve from project root ──────────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ── Dependency check ─────────────────────────────────────────────────────────
def check_deps():
    missing = []
    try:
        import openai
    except ImportError:
        missing.append("openai")
    if missing:
        print("─" * 55)
        print("VINCE: Missing required packages.\n")
        print(f"  pip install {' '.join(missing)}")
        print("─" * 55)
        sys.exit(1)

check_deps()

# ── Imports ──────────────────────────────────────────────────────────────────
import data as D
from logger import log_system
from llm_client import VINCEClient
from ui import VINCEApp
from admin_utils import is_admin, admin_status_string


def main():
    log_system("=" * 60)
    log_system(f"V.I.N.C.E starting up | Admin: {admin_status_string()}")
    log_system("=" * 60)
    
    # Init LLM client
    try:
        client = VINCEClient()
    except Exception as e:
        print(f"\n[VINCE] LLM client init failed: {e}")
        print("Ensure 'openai' is installed: pip install openai")
        sys.exit(1)

    # Launch GUI
    app = VINCEApp(client)

    # Ping LLM server in background
    def _ping():
        import urllib.request
        cfg = D.get_llm()
        base = cfg.get("base_url", "http://127.0.0.1:8080")
        try:
            urllib.request.urlopen(f"{base}/models", timeout=4)
            app.after(0, lambda: app._status_lbl.configure(
                text="● ONLINE", fg="#00ff88"))
            log_system("LLM server reachable.")
        except Exception:
            app.after(0, lambda: app._status_lbl.configure(
                text="● LLM OFFLINE", fg="#ff4444"))
            app.after(0, lambda: app._append_msg(
                "error",
                "Cannot reach llama.cpp server.\n"
                "Configure and start it via Settings → Server → ▶ Start Now,\n"
                "or launch manually:\n"
                "  llama-server -m /path/to/model.gguf --port 8080 --ctx-size 32768"
            ))
            log_system("WARNING: LLM server not reachable.")

    threading.Thread(target=_ping, daemon=True).start()

    app.mainloop()
    log_system("VINCE shut down cleanly.")


def _try_auto_start_server():
    """Start llama-server in background if auto_start is set."""
    import subprocess
    cfg = D.get_server()
    exe = cfg.get("exe_path", "")
    models_dir = cfg.get("models_dir", "")
    current_model = D.get("current_model", "")
    
    if not exe or not models_dir or not current_model:
        log_system("Auto-start: exe_path, models_dir, or current_model not set — skipping.")
        return
        
    model_path = os.path.join(models_dir, current_model)
    if not os.path.exists(model_path):
        log_system(f"Auto-start failed: Model not found at {model_path}")
        return

    port  = str(cfg.get("port", 8080))
    ctx   = str(cfg.get("ctx_size", 2048))
    ngl   = str(cfg.get("gpu_layers", 99))
    extra = cfg.get("extra_args", "").split()
    
    cmd = [exe, "-m", model_path, "--port", port, "--ctx-size", ctx, "-ngl", ngl] + extra
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
        )
        log_system(f"Server auto-started with {current_model} (PID {proc.pid}).")
        import time; time.sleep(3) 
    except Exception as e:
        log_system(f"Auto-start failed: {e}")


if __name__ == "__main__":
    main()
