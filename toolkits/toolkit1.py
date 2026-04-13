"""
VINCE Custom Toolkit
─────────────────────────────────────────────────────────────────
This file contains the custom tools requested: Selenium web search,
facial recognition, system storage checks, app launchers, networking
utilities, and extra AI utility tools.

Drop this file in the toolkits/ folder and it will be loaded 
automatically on startup.

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

import os
import platform
import subprocess
from tools import register_tool

# ── Tool 2: Check tuzvizsgalo.eu Status ──────────────────────────────────────
@register_tool(
    "check_tuzvizsgalo",
    "Check if the website tuzvizsgalo.eu is currently online and responding. it does not take arguments and returns a simple status message.",
    {},
)
def check_tuzvizsgalo() -> str:
    try:
        import requests
        resp = requests.get("https://tuzvizsgalo.eu", timeout=10)
        if resp.status_code == 200:
            return "tuzvizsgalo.eu is ONLINE and functioning correctly (Status 200)."
        return f"tuzvizsgalo.eu responded, but with status code: {resp.status_code}"
    except ImportError:
        return "[check_tuzvizsgalo error] Please run: pip install requests"
    except Exception as e:
        return f"tuzvizsgalo.eu appears to be OFFLINE. Error: {e}"


# ── Tool 3: Network Ping ─────────────────────────────────────────────────────
@register_tool(
    "ping_target",
    "Ping an IP address or website domain to check connectivity and latency.",
    {"target": "string — IP address or domain name (e.g., '8.8.8.8' or 'google.com')"},
)
def ping_target(target: str) -> str:
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "4", target]
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True)
        return output
    except subprocess.CalledProcessError as e:
        return f"[ping_target error] Failed to ping {target}:\n{e.output}"
    except Exception as e:
        return f"[ping_target error] {e}"


# ── Tool 4: Total SSD Free Space ─────────────────────────────────────────────
@register_tool(
    "get_total_free_space",
    "Get the total free space in GB across all mounted physical drives.",
    {},
)
def get_total_free_space() -> str:
    try:
        import psutil
        total_free = 0
        details = []
        
        partitions = psutil.disk_partitions(all=False)
        for p in partitions:
            if 'cdrom' in p.opts or p.fstype == '':
                continue
            try:
                usage = psutil.disk_usage(p.mountpoint)
                free_gb = usage.free / (1024 ** 3)
                total_free += free_gb
                details.append(f"Drive {p.mountpoint}: {free_gb:.2f} GB free")
            except PermissionError:
                continue

        result = f"Total Free Space: {total_free:.2f} GB\n" + "\n".join(details)
        return result
    except ImportError:
        return "[get_total_free_space error] Please run: pip install psutil"
    except Exception as e:
        return f"[get_total_free_space error] {e}"


# ── Tool 5: Open Calculator ──────────────────────────────────────────────────
@register_tool(
    "open_calculator",
    "Open the system calculator.",
    {},
)
def open_calculator() -> str:
    try:
        sys_os = platform.system().lower()
        if sys_os == "windows":
            subprocess.Popen("calc.exe")
        elif sys_os == "darwin":  # macOS
            subprocess.Popen(["open", "-a", "Calculator"])
        else:  # Linux
            subprocess.Popen("gnome-calculator")
        return "Calculator launched successfully."
    except Exception as e:
        return f"[open_calculator error] {e}"


# ── Tool 6: Big Idea Dev Launcher ────────────────────────────────────────────
@register_tool(
    "i_have_a_big_idea",
    "Developer mode launcher: Opens VSCode, Discord, and Opera GX simultaneously.",
    {},
)
def i_have_a_big_idea() -> str:
    apps_launched = []
    errors = []
    sys_os = platform.system().lower()
    
    commands = {
        "VSCode": "code",
        "Discord": "Update.exe --processStart Discord.exe" if sys_os == "windows" else "discord",
        "Opera GX": "opera" if sys_os == "linux" else "opera-gx" 
    }

    for app, cmd in commands.items():
        try:
            if sys_os == "windows" or sys_os == "linux":
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys_os == "darwin":
                subprocess.Popen(["open", "-a", app])
            apps_launched.append(app)
        except Exception as e:
            errors.append(f"{app}: {e}")
            
    result = f"Launched: {', '.join(apps_launched)}"
    if errors:
        result += f"\nErrors: {'; '.join(errors)}"
    return result


# ── Tool 7: Strict Face Counter ──────────────────────────────────────────────
@register_tool(
    "count_faces",
    "Strict facial recognition tool to count the number of human faces in an image.",
    {"image_path": "string — absolute path to the image file"},
)
def count_faces(image_path: str) -> str:
    try:
        import cv2
        path = os.path.expandvars(os.path.expanduser(image_path))
        if not os.path.exists(path):
            return f"Image not found at: {path}"

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        img = cv2.imread(path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=8,  # High minNeighbors = strict mode
            minSize=(30, 30)
        )
        
        return f"Found {len(faces)} face(s) in the image (Strict Mode)."
    except ImportError:
        return "[count_faces error] Please run: pip install opencv-python"
    except Exception as e:
        return f"[count_faces error] {e}"


# ── Tool 8: Get System Time ──────────────────────────────────────────────────
@register_tool(
    "get_current_time",
    "Get the exact current local date and time.",
    {},
)
def get_current_time() -> str:
    try:
        from datetime import datetime
        return f"Current System Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        return f"[get_current_time error] {e}"


# ── Tool 9: Take Screenshot ──────────────────────────────────────────────────
@register_tool(
    "take_screenshot",
    "Takes a screenshot of the main monitor and saves it to a specified path.",
    {"save_path": "string — absolute path where the .png should be saved (e.g. C:/temp/screen.png)"},
)
def take_screenshot(save_path: str) -> str:
    try:
        from PIL import ImageGrab
        path = os.path.expandvars(os.path.expanduser(save_path))
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        screenshot = ImageGrab.grab()
        screenshot.save(path)
        return f"Screenshot successfully saved to {path}"
    except ImportError:
        return "[take_screenshot error] Please run: pip install Pillow"
    except Exception as e:
        return f"[take_screenshot error] {e}"


# ── Tool 10: Extract Text From Image (OCR) ───────────────────────────────────
@register_tool(
    "extract_text_from_image",
    "Uses OCR to extract readable text from an image file.",
    {"image_path": "string — absolute path to the image"},
)
def extract_text_from_image(image_path: str) -> str:
    try:
        from PIL import Image
        import pytesseract
        
        path = os.path.expandvars(os.path.expanduser(image_path))
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        
        if not text.strip():
            return "No text could be extracted."
        return text.strip()
    except ImportError:
        return "[extract_text error] Please run: pip install pytesseract Pillow"
    except Exception as e:
        return f"[extract_text error] {e} (Note: Tesseract-OCR must be installed on your OS)"


# ── Tool 11: Top Active Processes ────────────────────────────────────────────
@register_tool(
    "get_active_processes",
    "Lists the top 15 processes currently running on the system by memory usage.",
    {},
)
def get_active_processes() -> str:
    try:
        import psutil
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        processes.sort(key=lambda x: x['memory_info'].rss if x['memory_info'] else 0, reverse=True)
        
        lines = ["PID\tName\t\tMemory (MB)"]
        for p in processes[:15]:
            mem_mb = p['memory_info'].rss / (1024 * 1024) if p['memory_info'] else 0
            lines.append(f"{p['pid']}\t{p['name'][:15]:<15}\t{mem_mb:.1f} MB")
            
        return "\n".join(lines)
    except ImportError:
        return "[get_active_processes error] Please run: pip install psutil"
    except Exception as e:
        return f"[get_active_processes error] {e}"
    
# ── Tool: Enhanced Selenium Search ───────────────────────────────────────────
@register_tool(
    "selenium_search",
    "Search the web using Selenium. Improved to wait for results to prevent 'No results found'.",
    {"query": "string — what to search for"},
)
def selenium_search(query: str) -> str:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        # User agent helps prevent being blocked as a bot
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        
        driver = webdriver.Chrome(options=chrome_options)
        # Using Google instead of DuckDuckGo HTML for better results
        driver.get(f"https://www.google.com/search?q={query}")
        
        # Wait up to 10 seconds for results to actually load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "search"))
            )
            # Find result snippets
            results = driver.find_elements(By.CSS_SELECTOR, "div.VwiC3b")
            text_results = [res.text for res in results[:5] if res.text]
        except:
            text_results = []

        driver.quit()
        
        if not text_results:
            return f"No results found for '{query}'. The site might be blocking automated access or took too long to load."
        
        return "Search Results:\n\n" + "\n\n---\n\n".join(text_results)
    except Exception as e:
        return f"[selenium_search error] {e}"


# ── Tool: Website Author Finder ─────────────────────────────────────────────
@register_tool(
    "get_website_author",
    "Scans a website's HTML, meta tags, and footer for 'Made by', 'Author', or 'Developed by' info.",
    {"url": "string — the full URL of the website to scan"},
)
def get_website_author(url: str) -> str:
    try:
        import requests
        from bs4 import BeautifulSoup
        import re

        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        findings = []

        # 1. Check Meta Tags (Standard SEO practice)
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author:
            findings.append(f"Meta Tag Author: {meta_author.get('content')}")

        # 2. Search for common 'Credit' patterns in the text
        # Patterns: Made by, Developed by, Created by, Website by
        patterns = [
            r"(?i)made\s+by\s+([\w\s&]+)", 
            r"(?i)developed\s+by\s+([\w\s&]+)", 
            r"(?i)created\s+by\s+([\w\s&]+)",
            r"(?i)website\s+by\s+([\w\s&]+)",
            r"(?i)copyright\s+©?\s*\d{4}\s+([\w\s&]+)"
        ]
        
        # We look specifically in the footer or the whole body
        body_text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, body_text)
            if match:
                findings.append(f"Found in Text: {match.group(0).strip()}")

        if not findings:
            return "Could not find explicit 'Made by' info in the HTML. It might be hidden in an image logo or not listed."
        
        return f"Potential Author Information for {url}:\n" + "\n".join(findings)

    except Exception as e:
        return f"[get_website_author error] {e}"