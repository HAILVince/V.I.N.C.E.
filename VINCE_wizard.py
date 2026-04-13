import os
os.system("pip install requests tkinter beautifulsoup4 ctypes tempfile zipfile shutil --quiet")
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import os
import zipfile
import subprocess
import threading
import shutil
import os
import sys
import ctypes
import tempfile


def run_as_admin_if_needed():
    """
    Relaunch the script as administrator if not already.
    Returns True if already running as admin, False if relaunched and exiting.
    """
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        is_admin = False

    if not is_admin:
        # Relaunch the script as admin
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join([os.path.abspath(sys.argv[0])] + sys.argv[1:]),
            None,
            1
        )
        sys.exit()  # Close the current non-admin process
    return True  # Already admin, continue normal execution
run_as_admin_if_needed()

def download_repo(repo_url, extract_path, progress_callback):
    def move_file(src, dst):
        """
            Move a file from src to dst.
            - src: source file path
            - dst: destination path (folder or full file path)
        """
        try:
            # If destination is a folder, keep the same filename
            if os.path.isdir(dst):
                dst = os.path.join(dst, os.path.basename(src))

            shutil.move(src, dst)
            print(f"Moved: {src} -> {dst}")
        except Exception as e:
            print(f"Error moving file: {e}")
    # Form the URL for the main branch zip
    zip_url = repo_url + "/archive/refs/heads/main.zip"
    response = requests.get(zip_url, stream=True)
    if response.status_code != 200:
        raise Exception(f"Failed to download repo: {response.status_code}")
    
    total_size = int(response.headers.get('content-length', 0))
    zip_path = os.path.join(os.path.dirname(extract_path), "temp.zip")
    downloaded = 0
    
    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    progress_callback(progress)
    
    # Extract the zip
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    destinations = {
            "tl_skin_cape_forge_1.20.6_1.21-1.36.jar": "/mods",
            "minescript-forge-1.21.5-4.0.jar": "/mods",
            "aimbot.py": "/minescript",
            "config.txt": "/minescript",
            "aimbot1_WIP.py": "/minescript",
            "version.txt": "/minescript/system",
            "help.py": "/minescript/system/exec",
            "eval.py": "/minescript/system/exec",
            "copy_blocks.py": "/minescript/system/exec",
            "paste.py": "/minescript/system/exec",
            "minescript.py": "/minescript/system/lib",
            "minescript_runtime.py": "/minescript/system/lib",
            "minescript.cpython-311.pyc": "/minescript/system/lib/__pycache__",
            "minescript_runtime.cpython-311.pyc": "/minescript/system/lib/__pycache__",
        }
    def move_file_safe(src_file, dst_folder, base_dir):
        """
        Move src_file into dst_folder.
        - base_dir: root folder for relative paths
        - strips leading slashes and converts slashes for Windows
        - ensures destination exists
        """
        # Normalize slashes and remove leading slashes
        dst_folder = dst_folder.replace("/", os.sep).replace("\\", os.sep).lstrip(os.sep)
        abs_dst_folder = os.path.join(base_dir, dst_folder)

        # Make sure destination exists
        os.makedirs(abs_dst_folder, exist_ok=True)

        # Full destination path
        dst_file = os.path.join(abs_dst_folder, os.path.basename(src_file))

        # Move file
        try:
            shutil.move(src_file, dst_file)
            print(f"Moved: {src_file} -> {dst_file}")
            return True
        except Exception as e:
            print(f"Error moving file: {e}")
            return False
    base_dir = extract_path
    for root, _, files in os.walk(extract_path):
        for file in files:
            if file in destinations:
                src = os.path.join(root, file)
                move_file_safe(src, destinations[file], base_dir)
    folder_to_remove = os.path.join(extract_path, "minecraft-cheat-1.21-main")
    if os.path.exists(folder_to_remove):
        shutil.rmtree(folder_to_remove)
        print(f"Removed folder: {folder_to_remove}")
    else:
        print(f"Folder does not exist: {folder_to_remove}")

def main():
    root = tk.Tk()
    root.title("mc cheat Installer Wizard")
    root.geometry("500x400")
    root.configure(bg='lightgrey')

    # Download and set wizard icon
    temp_dir = tempfile.mkdtemp()
    icon_url = "https://www.iconarchive.com/download/i/real-vista-development-icons-by-iconshock/wizard.ico"
    icon_path = os.path.join(temp_dir, 'wizard.ico')
    response = requests.get(icon_url)
    if response.status_code == 200:
        with open(icon_path, 'wb') as f:
            f.write(response.content)
        root.iconbitmap(icon_path)

    # Header with stickman and message
    header_frame = tk.Frame(root, bg='lightgrey')
    header_frame.pack(fill='x', pady=10)

    canvas = tk.Canvas(header_frame, width=100, height=100, bg='lightgrey', highlightthickness=0)
    canvas.pack(side='left', padx=10)
    # Draw stickman
    canvas.create_oval(40, 10, 60, 30, fill='black')  # head
    canvas.create_line(50, 30, 50, 70, width=2)  # body
    canvas.create_line(50, 40, 30, 50, width=2)  # left arm
    canvas.create_line(50, 40, 70, 50, width=2)  # right arm
    canvas.create_line(50, 70, 40, 90, width=2)  # left leg
    canvas.create_line(50, 70, 60, 90, width=2)  # right leg

    message_label = tk.Label(header_frame, text="Welcome! Let's start with the Terms of Service.", bg='lightgrey', font=('Arial', 12), wraplength=300)
    message_label.pack(side='left', padx=10)

    # Frames for each step
    tos_frame = tk.Frame(root, bg='lightgrey')
    choose_path_frame = tk.Frame(root, bg='lightgrey')
    progress_frame = tk.Frame(root, bg='lightgrey')
    finish_frame = tk.Frame(root, bg='lightgrey')
    
    # TOS Frame
    tos_label = tk.Label(tos_frame, text="Terms of Service", bg='lightgrey')
    tos_label.pack(pady=10)
    
    tos_text = tk.Text(tos_frame, height=10, width=50)
    tos_text.insert(tk.END, "By installing this app, you agree to use it responsibly. No warranties provided. Use at your own risk.")
    tos_text.pack()
    
    accept_var = tk.BooleanVar()
    check = tk.Checkbutton(tos_frame, text="I accept the Terms of Service", variable=accept_var, bg='lightgrey')
    check.pack(pady=10)
    
    def next_tos():
        if accept_var.get():
            tos_frame.pack_forget()
            choose_path_frame.pack()
            message_label.config(text="Now, choose the Minecraft folder where to install.")
        else:
            messagebox.showerror("Error", "You must accept the TOS to proceed.")
    
    button_next_tos = tk.Button(tos_frame, text="Next", command=next_tos)
    button_next_tos.pack()
    
    # Choose Path Frame
    path_label = tk.Label(choose_path_frame, text="Choose the minecraft folder:", bg='lightgrey')
    path_label.pack(pady=10)
    
    path_var = tk.StringVar(value=os.path.expanduser("~"))
    entry = tk.Entry(choose_path_frame, textvariable=path_var, width=50)
    entry.pack()
    
    def browse():
        dir_path = filedialog.askdirectory()
        if dir_path:
            path_var.set(dir_path)
    
    button_browse = tk.Button(choose_path_frame, text="Browse", command=browse)
    button_browse.pack(pady=10)
    
    def next_path():
        global extract_path
        folder = path_var.get()
        if folder and os.path.isdir(folder):
            extract_path = folder
            choose_path_frame.pack_forget()
            progress_frame.pack()
            message_label.config(text="Downloading and setting up the cheat...")
            # Start download in a thread
            thread = threading.Thread(target=do_download)
            thread.start()
        else:
            messagebox.showerror("Error", "Please select a the minecraft folder's valid directory.")
    
    button_next_path = tk.Button(choose_path_frame, text="Next", command=next_path)
    button_next_path.pack()
    
    # Progress Frame
    progress_label = tk.Label(progress_frame, text="Downloading and setting up the cheat...", bg='lightgrey')
    progress_label.pack(pady=10)
    
    progressbar = ttk.Progressbar(progress_frame, orient="horizontal", length=300, mode="determinate")
    progressbar.pack(pady=10)
    
    def update_progress(value):
        progressbar['value'] = value
    
    def finish_download():
        progress_label.config(text="Finished")
        progress_frame.pack_forget()
        finish_frame.pack()
        message_label.config(text="Installation complete! Enjoy your cheat.")
    
    def show_error(msg):
        messagebox.showerror("Error", msg)
        # Reset to choose path or something, but for simplicity, close
        root.quit()
    
    def do_download():
        # Replace with your actual GitHub repo URL, e.g., "https://github.com/yourusername/yourapprepo"
        repo_url = "https://github.com/kovacsagoston312-cell/minecraft-cheat-1.21"
        try:
            download_repo(repo_url, extract_path, lambda v: root.after(0, update_progress, v))
            root.after(0, finish_download)
        except Exception as e:
            root.after(0, show_error, str(e))
    
    # Finish Frame
    finish_label = tk.Label(finish_frame, text="Installation complete!\n now you just need to run tlauncher on version 1.21 Forge\n and to start the aimbot in the chat type \\aimbot", bg='lightgrey')
    finish_label.pack(pady=10)
    
    def close():
        root.quit()
    
    button_close = tk.Button(finish_frame, text="Close", command=close)
    button_close.pack(pady=5)
    def create_folder(path):
        """
        Create a folder at the given path.
        If the folder already exists, nothing happens.
        """
        try:
            os.makedirs(path, exist_ok=True)
            print(f"Folder created (or already exists): {path}")
        except Exception as e:
            print(f"Error creating folder: {e}")
    
    
    # Start with TOS frame
    tos_frame.pack()
    
    root.mainloop()

if __name__ == "__main__":
    main()