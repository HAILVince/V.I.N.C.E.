"""VINCE Startup Launcher
- Requests admin elevation if needed.
- Reads last used model from data.json (or picks first .gguf).
- Starts llama-server with that model using saved server config.
- Waits until server is ready.
- Launches main.py.
"""

import os
import sys
import subprocess
import time
import json
import data as D
# Ensure we're in the correct directory
root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)

# ----- Admin elevation -----
def is_admin():
    if os.name == "nt":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    else:
        return os.geteuid() == 0

def restart_as_admin():
    if os.name == "nt":
        script = os.path.abspath(sys.argv[0])
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
        import ctypes
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
    else:
        subprocess.Popen(["pkexec", sys.executable] + sys.argv)
    sys.exit(0)

if not is_admin():
    print("VINCE Startup: Requesting administrator privileges...")
    restart_as_admin()

# ----- Load configuration -----
data_file = os.path.join(root, "data.json")
if not os.path.exists(data_file):
    # minimal default
    default = {
        "current_model": "",
        "server": {
            "exe_path": "",
            "models_dir": "",
            "port": 8080,
            "ctx_size": 32768,
            "gpu_layers": 99,
            "extra_args": ""
        }
    }
    with open(data_file, "w") as f:
        json.dump(default, f)

with open(data_file, "r") as f:
    data = json.load(f)

cfg_server = data.get("server", {})
exe = cfg_server.get("exe_path", "")
models_dir = cfg_server.get("models_dir", "")
model_name = data.get("current_model", "")
port = cfg_server.get("port", 8080)

# If no model selected, pick first .gguf in models_dir
import tkinter as tk
from tkinter import ttk

# Find all models in the directory
available_models = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]

if not available_models:
    print("VINCE: No .gguf models found in models directory.")
    sys.exit(1)

# --- Startup Model Selector ---
def select_model():
    root = tk.Tk()
    root.title("V.I.N.C.E - Select Model")
    root.geometry("400x150")
    root.eval('tk::PlaceWindow . center')
    
    tk.Label(root, text="Select a model to load:", font=("Arial", 12)).pack(pady=10)
    
    selected_model = tk.StringVar(value=D.get("current_model", available_models[0]))
    dropdown = ttk.Combobox(root, textvariable=selected_model, values=available_models, state="readonly", width=40)
    dropdown.pack(pady=5)
    
    def on_start():
        root.destroy()
        
    tk.Button(root, text="Start V.I.N.C.E", command=on_start, bg="#00c8ff", fg="black").pack(pady=10)
    root.mainloop()
    return selected_model.get()

model_name = select_model()
D.set("current_model", model_name) # Save for next time

if not exe or not models_dir or not model_name:
    print("VINCE: Server config incomplete. Please set EXE Path, Models Dir, and select a model in Settings.")
    sys.exit(1)

model_path = os.path.join(models_dir, model_name)
if not os.path.exists(model_path):
    print(f"VINCE: Model file not found: {model_path}")
    sys.exit(1)

# ----- Build command -----
cmd = [
    exe,
    "-m", model_path,
    "-c", "0"  # <--- THIS TELLS LLAMA.CPP TO AUTO-DETECT CONTEXT SIZE
]
extra = cfg_server.get("extra_args", "").split()
if extra:
    cmd.extend(extra)

print(f"Starting server: {' '.join(cmd)}")
proc = subprocess.Popen(
    cmd,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
)

# ----- Wait for server readiness -----
server_url = f"http://127.0.0.1:{port}"
print(f"Waiting for server at {server_url}...")
max_attempts = 30
for i in range(max_attempts):
    try:
        import urllib.request
        urllib.request.urlopen(f"{server_url}/v1/models", timeout=2)
        print("Server is ready!")
        break
    except Exception:
        time.sleep(1)
else:
    print("Server did not become ready in time. Continuing anyway...")

# ----- Launch main UI -----
print("Launching VINCE main interface...")
subprocess.Popen([sys.executable, os.path.join(root, "main.py")])