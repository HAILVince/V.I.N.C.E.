"""
VINCE admin_utils.py
Cross-platform admin privilege detection and restart-as-admin helper.
"""

import sys
import os
import subprocess


def is_admin() -> bool:
    """Return True if the current process has admin/root privileges."""
    try:
        if os.name == "nt":
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        else:
            return os.geteuid() == 0
    except Exception:
        return False


def restart_as_admin() -> None:
    """
    Relaunch this script with elevated privileges.
    On Windows: uses ShellExecute with 'runas' verb.
    On Linux/macOS: uses pkexec / sudo.
    """
    if is_admin():
        return  # already admin, nothing to do

    if os.name == "nt":
        import ctypes
        params = " ".join(f'"{a}"' for a in sys.argv)
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
    else:
        try:
            subprocess.Popen(["pkexec"] + [sys.executable] + sys.argv)
        except FileNotFoundError:
            subprocess.Popen(["sudo"] + [sys.executable] + sys.argv)

    # Exit current (non-admin) instance
    sys.exit(0)


def admin_status_string() -> str:
    """Return a short string describing current privilege level."""
    return "ADMIN" if is_admin() else "USER"


def admin_status_color() -> str:
    """Return a colour for the admin status indicator."""
    return "#ff6030" if is_admin() else "#4a7a99"
