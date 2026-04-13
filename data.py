"""
VINCE data.py
Persistent settings stored in data.json.
All mutable runtime settings live here so they survive restarts.
"""

import json
import os
import copy
from datetime import datetime
from config import DATA_FILE, DEFAULT_THEME

# ─── Default data structure ──────────────────────────────────────────────────
_DEFAULTS: dict = {
    "version":         "2.0.0",
    "current_theme":   DEFAULT_THEME,
    "current_profile": "default",
    "current_model":   "Qwen3-8B-Instruct-Q4_K_M.gguf",
    "known_models":    ["Qwen3-8B-Instruct-Q4_K_M.gguf"],
    "window_geometry": "1280x820",

    # LLM / inference settings
    "llm": {
        "base_url":      "http://127.0.0.1:8080/v1",
        "temperature":   0.7,
        "max_tokens":    4096,
        "top_p":         0.95,
        "repeat_penalty": 1.1,
        "stream":        True,
        "max_ctx_messages": 60,
        "max_log_lines": 80,
        "max_tool_iters": 8,
    },

    # llama-server launch settings (used by the Start Server button)
    "server": {
        "exe_path":    "",
        "models_dir":  "",  # <-- Changed from model_path
        "port":        8080,
        "ctx_size":    32768,
        "gpu_layers":  99,
        "extra_args":  "",
        "auto_start":  False,
    },

    # TTS settings
    "tts": {
        "enabled":   False,
        "voice_id":  "",
        "rate":      175,
        "volume":    1.0,
        "auto_read": False,
    },

    # Voice input (STT) settings
    "stt": {
        "enabled":    False,
        "auto_send":  True,
        "energy_threshold": 300,
    },

    # User profiles
    "profiles": {
    "default": {
        "name": "User",
        "avatar": "👤",
        "system_extra": "",
        "user_backstory": "",   # new field
        "theme": "",
        "created": datetime.now().strftime("%Y-%m-%d"),
    }

},
}

# ─── In-memory state ─────────────────────────────────────────────────────────
_data: dict = {}


def load() -> dict:
    """Load data.json from disk. Creates it with defaults if missing."""
    global _data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Deep-merge loaded over defaults (adds any new keys from defaults)
            _data = _deep_merge(copy.deepcopy(_DEFAULTS), loaded)
        except Exception as e:
            print(f"[data] Failed to load data.json: {e}. Using defaults.")
            _data = copy.deepcopy(_DEFAULTS)
    else:
        _data = copy.deepcopy(_DEFAULTS)
    save()  # write back (ensures new keys are persisted)
    return _data


def save() -> None:
    """Write current state to data.json."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[data] Failed to save data.json: {e}")


def get(key: str, default=None):
    """Get a top-level key."""
    return _data.get(key, default)


def set(key: str, value) -> None:
    """Set a top-level key and save."""
    _data[key] = value
    save()


def get_llm() -> dict:
    return _data.get("llm", _DEFAULTS["llm"])


def set_llm(updates: dict) -> None:
    _data["llm"].update(updates)
    save()


def get_server() -> dict:
    return _data.get("server", _DEFAULTS["server"])


def set_server(updates: dict) -> None:
    _data["server"].update(updates)
    save()


def get_tts() -> dict:
    return _data.get("tts", _DEFAULTS["tts"])


def set_tts(updates: dict) -> None:
    _data["tts"].update(updates)
    save()


def get_stt() -> dict:
    return _data.get("stt", _DEFAULTS["stt"])


def set_stt(updates: dict) -> None:
    _data["stt"].update(updates)
    save()


def get_profiles() -> dict:
    return _data.get("profiles", _DEFAULTS["profiles"])


def get_current_profile() -> dict:
    profiles = get_profiles()
    pid = _data.get("current_profile", "default")
    return profiles.get(pid, profiles.get("default", _DEFAULTS["profiles"]["default"]))


def save_profile(pid: str, profile_data: dict) -> None:
    if "profiles" not in _data:
        _data["profiles"] = {}
    _data["profiles"][pid] = profile_data
    save()


def delete_profile(pid: str) -> bool:
    if pid == "default":
        return False  # cannot delete default
    profiles = _data.get("profiles", {})
    if pid in profiles:
        del profiles[pid]
        if _data.get("current_profile") == pid:
            _data["current_profile"] = "default"
        save()
        return True
    return False


def add_model(model_name: str) -> None:
    models = _data.get("known_models", [])
    if model_name not in models:
        models.append(model_name)
        _data["known_models"] = models
        save()


def remove_model(model_name: str) -> None:
    models = _data.get("known_models", [])
    if model_name in models:
        models.remove(model_name)
        _data["known_models"] = models
        save()


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Base keys not in override are kept."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


# Auto-load on import
load()
