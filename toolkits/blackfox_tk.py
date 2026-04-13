"""
BlackFox Toolkit v2 — Structured Toolkit
─────────────────────────────────────────────────────────────────
All callable, safe tools from blackfoxv2.py restructured into the
standard toolkit format used by toolkit1.py.

Drop this file in the toolkits/ folder and it will be loaded
automatically on startup.

You can also load it at runtime via: Sidebar → 📦 Load Toolkit

RULES FOR TOOLKIT FILES:
  1. Import register_tool from tools (not from this file's path).
  2. Decorate your functions with @register_tool.
  3. Always return a string from your tool function.
  4. Handle exceptions — return an error string, never raise.
  5. Parameter dict keys must exactly match function argument names.
  6. Set dangerous=True for tools that modify system state.
─────────────────────────────────────────────────────────────────

Required pip packages (install as needed):
  pip install requests phonenumbers instaloader qrcode pillow
  pip install dnspython beautifulsoup4 tldextract pyfiglet
  pip install whois psutil opencv-python

EXCLUDED (non-safe) tools from the original blackfoxv2.py:
  - email_bomber      (mass email sending)
  - dos / send_request (DoS / flood attacks)
  - arp_spoof         (network attack)
  - metasploit        (exploit framework hook)
  - overwrite_system32_file (destructive system modification)
  - un_destroable_window    (screen-lock style harassment tool)
  - omegle_puller     (covert IP harvesting from video chat)
  - submit_form       (form flood / SQL injection driver)
  - insta_face_rec    (mass facial analysis of third-party profiles)
─────────────────────────────────────────────────────────────────
"""

import os
import platform
import subprocess
import socket
from tools import register_tool


# ── Tool 1: IP Geolocation ────────────────────────────────────────────────────
@register_tool(
    "get_ip_info",
    "Look up geolocation data for any IP address: city, region, country, coordinates, and a Google Maps link.",
    {"ip_address": "string — the IP address to look up (e.g., '8.8.8.8')"},
)
def get_ip_info(ip_address: str) -> str:
    try:
        import requests
        url = f"https://ipinfo.io/{ip_address}/json"
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        data = response.json()

        ip   = data.get("ip", "N/A")
        city = data.get("city", "N/A")
        region  = data.get("region", "N/A")
        country = data.get("country", "N/A")
        loc  = data.get("loc", "N/A")
        org  = data.get("org", "N/A")

        if loc != "N/A":
            lat, lon = loc.split(",")
            maps_link = f"https://www.google.com/maps?q={lat},{lon}"
        else:
            maps_link = "N/A"

        return (
            f"IP Address : {ip}\n"
            f"City       : {city}\n"
            f"Region     : {region}\n"
            f"Country    : {country}\n"
            f"Coordinates: {loc}\n"
            f"ISP / Org  : {org}\n"
            f"Google Maps: {maps_link}"
        )
    except ImportError:
        return "[get_ip_info error] Please run: pip install requests"
    except Exception as e:
        return f"[get_ip_info error] {e}"


# ── Tool 2: Get Your Own Public IP Info ───────────────────────────────────────
@register_tool(
    "get_public_ip_info",
    "Fetch your own public IP address along with city, region, country, and ISP information.",
    {},
)
def get_public_ip_info() -> str:
    try:
        import requests
        response = requests.get("https://ipinfo.io/json", timeout=8)
        response.raise_for_status()
        data = response.json()
        return (
            f"Public IP : {data.get('ip', 'N/A')}\n"
            f"City      : {data.get('city', 'N/A')}\n"
            f"Region    : {data.get('region', 'N/A')}\n"
            f"Country   : {data.get('country', 'N/A')}\n"
            f"ISP / Org : {data.get('org', 'N/A')}\n"
            f"ASN       : {data.get('asn', 'N/A')}"
        )
    except ImportError:
        return "[get_public_ip_info error] Please run: pip install requests"
    except Exception as e:
        return f"[get_public_ip_info error] {e}"


# ── Tool 3: Check if IP is Online ─────────────────────────────────────────────
@register_tool(
    "get_if_online",
    "Ping an IP address to check whether it is currently reachable (online) or not.",
    {"ip": "string — IP address to check (e.g., '192.168.1.1')"},
)
def get_if_online(ip: str) -> str:
    try:
        result = subprocess.run(
            ["ping", ip],
            capture_output=True, text=True, timeout=15
        )
        if "Received = 4" in result.stdout or "4 packets transmitted" in result.stdout:
            return f"{ip} is ONLINE"
        return f"{ip} is OFFLINE"
    except Exception as e:
        return f"[get_if_online error] {e}"


# ── Tool 4: Ping IP ────────────────────────────────────────────────────────────
@register_tool(
    "ping_ip",
    "Ping an IP address or hostname and return the full ping output including latency stats.",
    {"ip": "string — IP address or hostname to ping"},
)
def ping_ip(ip: str) -> str:
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        result = subprocess.run(
            ["ping", param, "4", ip],
            capture_output=True, text=True, timeout=20
        )
        return result.stdout or result.stderr or "No output returned."
    except Exception as e:
        return f"[ping_ip error] {e}"


# ── Tool 5: Traceroute ────────────────────────────────────────────────────────
@register_tool(
    "traceroute",
    "Run a traceroute (tracert on Windows) to an IP or hostname and return each hop.",
    {"ip": "string — IP address or hostname to trace"},
)
def traceroute(ip: str) -> str:
    try:
        cmd = "tracert" if platform.system().lower() == "windows" else "traceroute"
        result = subprocess.run(
            [cmd, ip],
            capture_output=True, text=True, timeout=60
        )
        lines = result.stdout.splitlines()
        return "\n".join(lines) if lines else "No output returned."
    except Exception as e:
        return f"[traceroute error] {e}"


# ── Tool 6: VPN / Proxy Detection via Traceroute Hop Count ────────────────────
@register_tool(
    "detect_vpn_by_hops",
    "Estimate whether an IP is behind a VPN or proxy by counting traceroute hops. More than 15 hops is a strong indicator.",
    {"ip": "string — IP address to analyse"},
)
def detect_vpn_by_hops(ip: str) -> str:
    try:
        cmd = "tracert" if platform.system().lower() == "windows" else "traceroute"
        counter = 0
        with os.popen(f"{cmd} -h 16 {ip}") as process:
            for line in process:
                counter += 1
        if counter > 15:
            return f"{ip}: Likely behind a VPN or proxy ({counter} hops detected)."
        return f"{ip}: Probably NOT behind a VPN ({counter} hops detected)."
    except Exception as e:
        return f"[detect_vpn_by_hops error] {e}"


# ── Tool 7: DNS Resolution ────────────────────────────────────────────────────
@register_tool(
    "resolve_dns",
    "Resolve a domain name to its IP address using standard DNS lookup.",
    {"hostname": "string — domain name to resolve (e.g., 'example.com')"},
)
def resolve_dns(hostname: str) -> str:
    try:
        ip = socket.gethostbyname(hostname)
        return f"Domain: {hostname}  →  IP: {ip}"
    except socket.gaierror as e:
        return f"[resolve_dns error] Could not resolve {hostname}: {e}"
    except Exception as e:
        return f"[resolve_dns error] {e}"


# ── Tool 8: Reverse DNS (Shared-Host Finder) ──────────────────────────────────
@register_tool(
    "reverse_dns_lookup",
    "Perform a reverse DNS (PTR) lookup on an IP address to find the hostnames it resolves to.",
    {"ip_address": "string — IP address to reverse-lookup (e.g., '93.184.216.34')"},
)
def reverse_dns_lookup(ip_address: str) -> str:
    try:
        hostname, aliases, _ = socket.gethostbyaddr(ip_address)
        domains = list({hostname} | set(aliases))
        if domains:
            return f"Reverse DNS for {ip_address}:\n" + "\n".join(f"  • {d}" for d in domains)
        return f"No PTR records found for {ip_address}."
    except socket.herror:
        return f"No reverse DNS record found for {ip_address}."
    except Exception as e:
        return f"[reverse_dns_lookup error] {e}"


# ── Tool 9: WHOIS Lookup ──────────────────────────────────────────────────────
@register_tool(
    "whois_lookup",
    "Perform a WHOIS lookup on a domain name to retrieve registrar, creation date, expiration date, name servers, and contact info.",
    {"domain": "string — domain name to look up (e.g., 'example.com')"},
)
def whois_lookup(domain: str) -> str:
    try:
        import whois
        from datetime import datetime
        w = whois.whois(domain)

        def fmt_date(d):
            if isinstance(d, datetime):
                return d.strftime("%Y-%m-%d %H:%M:%S")
            return str(d) if d else "N/A"

        lines = [
            f"Domain              : {w.domain_name or 'N/A'}",
            f"Registrar           : {w.registrar or 'N/A'}",
            f"Registrar URL       : {w.registrar_url or 'N/A'}",
            f"WHOIS Server        : {w.whois_server or 'N/A'}",
            f"Updated Date        : {fmt_date(w.updated_date)}",
            f"Creation Date       : {fmt_date(w.creation_date)}",
            f"Expiration Date     : {fmt_date(w.expiration_date)}",
            f"Name Servers        : {', '.join(w.name_servers) if w.name_servers else 'N/A'}",
            f"Status              : {', '.join(w.status) if isinstance(w.status, list) else str(w.status or 'N/A')}",
            f"Emails              : {', '.join(w.emails) if isinstance(w.emails, list) else str(w.emails or 'N/A')}",
            f"Registrant Name     : {w.registrant_name or 'N/A'}",
            f"Registrant Org      : {w.registrant_organization or 'N/A'}",
            f"Registrant Country  : {w.registrant_country or 'N/A'}",
        ]
        return "\n".join(lines)
    except ImportError:
        return "[whois_lookup error] Please run: pip install python-whois"
    except Exception as e:
        return f"[whois_lookup error] {e}"


# ── Tool 10: Open Port Scanner ────────────────────────────────────────────────
@register_tool(
    "scan_open_ports",
    "Scan an IP address for open TCP ports up to a specified maximum port number using multi-threading.",
    {
        "ip": "string — IP address to scan (e.g., '192.168.1.1')",
        "max_port": "string — highest port number to scan, e.g. '1024' or '9000' (default '1024')",
    },
)
def scan_open_ports(ip: str, max_port: str = "1024") -> str:
    try:
        from concurrent.futures import ThreadPoolExecutor

        max_port_int = int(max_port)

        def scan_single(port):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                result = s.connect_ex((ip, port))
                s.close()
                return port if result == 0 else None
            except Exception:
                return None

        ports_to_check = [(ip, p) for p in range(1, max_port_int + 1)]
        open_ports = []
        with ThreadPoolExecutor(max_workers=500) as executor:
            for port in executor.map(lambda args: scan_single(args[1]), ports_to_check):
                if port is not None:
                    open_ports.append(port)

        if open_ports:
            return f"Open ports on {ip} (up to {max_port_int}):\n" + "\n".join(
                f"  Port {p}" for p in sorted(open_ports)
            )
        return f"No open ports found on {ip} up to port {max_port_int}."
    except Exception as e:
        return f"[scan_open_ports error] {e}"


# ── Tool 11: Subdomain Finder ─────────────────────────────────────────────────
@register_tool(
    "find_subdomains",
    "Discover valid subdomains for a domain using a built-in wordlist and DNS resolution.",
    {"domain": "string — base domain to scan (e.g., 'example.com')"},
)
def find_subdomains(domain: str) -> str:
    try:
        import tldextract
        from urllib.parse import urlparse

        # Extract clean base domain
        parsed = urlparse(domain)
        netloc = parsed.netloc or parsed.path
        info = tldextract.extract(netloc)
        base_domain = f"{info.domain}.{info.suffix}"

        wordlist = [
            "www", "mail", "ftp", "blog", "test", "dev", "admin",
            "webmail", "smtp", "pop", "imap", "portal", "shop", "app",
            "api", "m", "mobile", "static", "cdn", "support", "forum",
            "node", "info", "contact", "news", "help", "about", "terms",
            "privacy", "faq", "careers", "press",
        ]

        found = []
        for sub in wordlist:
            target = f"{sub}.{base_domain}"
            try:
                socket.gethostbyname_ex(target)
                found.append(target)
            except socket.gaierror:
                pass
            except Exception:
                pass

        if found:
            return f"Found {len(found)} subdomain(s) for {base_domain}:\n" + "\n".join(
                f"  • {s}" for s in found
            )
        return f"No subdomains found for {base_domain} using the default wordlist."
    except ImportError:
        return "[find_subdomains error] Please run: pip install tldextract"
    except Exception as e:
        return f"[find_subdomains error] {e}"


# ── Tool 12: Admin / Common Page Finder ───────────────────────────────────────
@register_tool(
    "find_common_pages",
    "Probe a website for common admin and login pages (e.g. /admin, /login, /dashboard) and report their HTTP status.",
    {"domain": "string — full URL or domain to probe (e.g., 'https://example.com')"},
)
def find_common_pages(domain: str) -> str:
    try:
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from urllib.parse import urljoin

        if not domain.startswith(("http://", "https://")):
            domain = f"http://{domain}"

        common_paths = [
            "login", "admin", "dashboard", "signin", "signup",
            "admin/login", "admin/dashboard", "wp-admin", "cpanel",
            "portal", "account", "settings", "profile", "register",
            "forgot-password", "contact", "about", "help", "api",
            "docs", "status", "search", "store", "shop",
        ]

        found = []

        def check_path(path):
            url = urljoin(domain, path)
            try:
                r = requests.get(url, timeout=4, allow_redirects=True)
                if r.status_code == 200:
                    return f"[200 OK]       {url}"
                elif r.status_code in (401, 403):
                    return f"[{r.status_code} RESTRICTED] {url}"
                return None
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_path, p): p for p in common_paths}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found.append(result)

        if found:
            return f"Pages found on {domain}:\n" + "\n".join(sorted(found))
        return f"No interesting pages found on {domain}."
    except ImportError:
        return "[find_common_pages error] Please run: pip install requests"
    except Exception as e:
        return f"[find_common_pages error] {e}"


# ── Tool 13: WAF / Firewall Detection ────────────────────────────────────────
@register_tool(
    "detect_waf",
    "Detect whether a website is protected by a Web Application Firewall (WAF) or reverse proxy by analysing HTTP status codes and headers.",
    {"url": "string — full URL to check (e.g., 'https://example.com')"},
)
def detect_waf(url: str) -> str:
    try:
        import requests
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)

        indicators = []

        if response.status_code == 403:
            indicators.append("HTTP 403 Forbidden (common WAF block)")
        if response.status_code == 503:
            indicators.append("HTTP 503 Service Unavailable (possible WAF)")

        waf_headers = [
            "X-Security", "X-Content-Type-Options", "X-Frame-Options",
            "Server", "X-CF-Powered-By", "CF-RAY",
        ]
        for h in waf_headers:
            if h in response.headers:
                indicators.append(f"Header present: {h}: {response.headers[h]}")

        body_lower = response.text.lower()
        if "challenge" in body_lower or "captcha" in body_lower:
            indicators.append("JavaScript challenge / CAPTCHA detected in page body")

        if indicators:
            return f"WAF / firewall indicators found for {url}:\n" + "\n".join(
                f"  • {i}" for i in indicators
            )
        return f"No obvious WAF indicators found for {url}."
    except ImportError:
        return "[detect_waf error] Please run: pip install requests"
    except Exception as e:
        return f"[detect_waf error] {e}"


# ── Tool 14: Hosting Provider Detection ──────────────────────────────────────
@register_tool(
    "detect_hosting_provider",
    "Identify the hosting/CDN provider of a website (e.g. Cloudflare, AWS, or private host) by analysing IP ranges and HTTP headers.",
    {"url": "string — full URL to analyse (e.g., 'https://example.com')"},
)
def detect_hosting_provider(url: str) -> str:
    try:
        import requests
        import ipaddress as ipmod

        if url.startswith("http://"):
            hostname = url.replace("http://", "").split("/")[0]
        elif url.startswith("https://"):
            hostname = url.replace("https://", "").split("/")[0]
        else:
            hostname = url.split("/")[0]

        ip_address = socket.gethostbyname(hostname)
        response = requests.get(url, timeout=5)
        resp_headers = response.headers

        if "CF-RAY" in resp_headers or "cloudflare" in resp_headers.get("Server", "").lower():
            return f"Provider: Cloudflare  (IP: {ip_address})"

        cloudflare_ranges = [
            "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22",
            "103.31.4.0/22", "141.101.64.0/18", "108.162.192.0/18",
        ]
        ip_obj = ipmod.ip_address(ip_address)
        for cf_range in cloudflare_ranges:
            if ip_obj in ipmod.ip_network(cf_range):
                return f"Provider: Cloudflare  (IP: {ip_address})"

        if (
            "amazonaws" in resp_headers.get("Server", "").lower()
            or "x-amz" in resp_headers
            or "aws" in resp_headers.get("Via", "").lower()
        ):
            return f"Provider: Amazon AWS  (IP: {ip_address})"

        try:
            dns_info = socket.gethostbyaddr(ip_address)
            return f"Provider: Private / Unknown  (IP: {ip_address}, rDNS: {dns_info[0]})"
        except Exception:
            return f"Provider: Private / Unknown  (IP: {ip_address})"

    except ImportError:
        return "[detect_hosting_provider error] Please run: pip install requests"
    except Exception as e:
        return f"[detect_hosting_provider error] {e}"


# ── Tool 15: URL Redirect Checker ────────────────────────────────────────────
@register_tool(
    "check_url_redirect",
    "Check whether a URL redirects and return the final destination URL along with the HTTP status code.",
    {"url": "string — URL to check (e.g., 'http://bit.ly/abc123')"},
)
def check_url_redirect(url: str) -> str:
    try:
        import requests
        response = requests.head(url, allow_redirects=True, timeout=8)
        final_url = response.url

        if final_url == url:
            return f"No redirect detected. URL stays at:\n  {url}\n  Status: {response.status_code}"

        hops = [r.url for r in response.history]
        hop_str = "\n".join(f"  {i+1}. {u}" for i, u in enumerate(hops))
        return (
            f"Redirect chain for {url}:\n"
            f"{hop_str}\n"
            f"  → Final URL: {final_url}\n"
            f"  Final status: {response.status_code}"
        )
    except ImportError:
        return "[check_url_redirect error] Please run: pip install requests"
    except Exception as e:
        return f"[check_url_redirect error] {e}"


# ── Tool 16: Scrape Emails from URL ──────────────────────────────────────────
@register_tool(
    "scrape_emails_from_url",
    "Scrape and return all email addresses found in a web page's HTML source.",
    {"url": "string — full URL to scan (e.g., 'https://example.com/contact')"},
)
def scrape_emails_from_url(url: str) -> str:
    try:
        import requests
        import re

        response = requests.get(url, timeout=10)
        emails = list(
            set(re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", response.text))
        )

        if emails:
            return f"Emails found on {url}:\n" + "\n".join(f"  • {e}" for e in sorted(emails))
        return f"No email addresses found on {url}."
    except ImportError:
        return "[scrape_emails_from_url error] Please run: pip install requests"
    except Exception as e:
        return f"[scrape_emails_from_url error] {e}"


# ── Tool 17: Extract Emails from Text ────────────────────────────────────────
@register_tool(
    "extract_emails_from_text",
    "Extract all email addresses found within a given block of text.",
    {"text": "string — the text content to search for email addresses"},
)
def extract_emails_from_text(text: str) -> str:
    try:
        import re
        emails = list(
            set(re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text, re.IGNORECASE))
        )
        if emails:
            return "Emails found:\n" + "\n".join(f"  • {e}" for e in sorted(emails))
        return "No email addresses found in the provided text."
    except Exception as e:
        return f"[extract_emails_from_text error] {e}"


# ── Tool 18: Get Text Input Elements from URL ─────────────────────────────────
@register_tool(
    "get_page_input_elements",
    "Analyse a web page and list all text input fields (input, textarea, select) including their IDs, names, and types. Useful for security auditing.",
    {"url": "string — full URL of the page to analyse"},
)
def get_page_input_elements(url: str) -> str:
    try:
        import requests
        from bs4 import BeautifulSoup

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        text_types = {"text", "email", "password", "search", "tel", "url"}
        inputs = soup.find_all("input", type=lambda t: t in text_types)
        textareas = soup.find_all("textarea")
        selects = soup.find_all("select")
        elements = inputs + textareas + selects

        if not elements:
            return f"No text input elements found on {url}."

        lines = [f"Input elements found on {url}:"]
        for i, el in enumerate(elements, 1):
            tag = el.name
            el_type = el.get("type", tag)
            el_id   = el.get("id", "—")
            el_name = el.get("name", "—")
            lines.append(f"  [{i}] <{tag}> type={el_type}  id={el_id}  name={el_name}")

        return "\n".join(lines)
    except ImportError:
        return "[get_page_input_elements error] Please run: pip install requests beautifulsoup4"
    except Exception as e:
        return f"[get_page_input_elements error] {e}"


# ── Tool 19: Domain Owner Lookup ──────────────────────────────────────────────
@register_tool(
    "get_domain_owner",
    "Attempt to identify the owner or company behind a URL using WHOIS data and HTML meta/title scraping.",
    {"url": "string — full URL or domain (e.g., 'https://example.com')"},
)
def get_domain_owner(url: str) -> str:
    try:
        import requests
        import whois
        import re
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url)
        domain = parsed.netloc.lower().lstrip("www.")

        lines = [f"Domain: {domain}"]

        # WHOIS
        try:
            w = whois.whois(domain)
            lines.append(f"WHOIS Registrant Name : {w.get('registrant_name') or w.get('name') or 'N/A'}")
            lines.append(f"WHOIS Organization    : {w.get('registrant_organization') or w.get('org') or 'N/A'}")
        except Exception:
            lines.append("WHOIS: Could not retrieve data")

        # Page scraping
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=5)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            title = soup.title.string.strip() if soup.title else "N/A"
            lines.append(f"Page Title            : {title}")

            meta_author = soup.find("meta", {"name": re.compile("author", re.I)})
            if meta_author:
                lines.append(f"Meta Author           : {meta_author.get('content', 'N/A')}")
        except Exception:
            lines.append("Page scraping: Could not retrieve data")

        return "\n".join(lines)
    except ImportError:
        return "[get_domain_owner error] Please run: pip install requests python-whois beautifulsoup4"
    except Exception as e:
        return f"[get_domain_owner error] {e}"


# ── Tool 20: Username Tracker ─────────────────────────────────────────────────
@register_tool(
    "check_username_across_platforms",
    "Check whether a username exists on major social media platforms including Twitter, Instagram, GitHub, Reddit, TikTok, and more.",
    {"username": "string — the username to search for (e.g., 'johndoe')"},
)
def check_username_across_platforms(username: str) -> str:
    try:
        import requests

        username = username.strip().replace(" ", "_")
        platforms = {
            "Twitter"   : f"https://twitter.com/{username}",
            "Instagram" : f"https://www.instagram.com/{username}",
            "GitHub"    : f"https://github.com/{username}",
            "Reddit"    : f"https://www.reddit.com/user/{username}",
            "TikTok"    : f"https://www.tiktok.com/@{username}",
            "Pinterest" : f"https://www.pinterest.com/{username}",
            "LinkedIn"  : f"https://www.linkedin.com/in/{username}",
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }

        lines = [f"Username check for '{username}':"]
        for platform, check_url in platforms.items():
            try:
                r = requests.get(check_url, headers=headers, timeout=6)
                if r.status_code == 200:
                    lines.append(f"  ✓ {platform}: Found  →  {check_url}")
                elif r.status_code == 404:
                    lines.append(f"  ✗ {platform}: Not found")
                elif r.status_code in (403, 429):
                    lines.append(f"  ? {platform}: Access restricted or rate-limited")
                else:
                    lines.append(f"  ? {platform}: HTTP {r.status_code}")
            except Exception as ex:
                lines.append(f"  ! {platform}: Error — {ex}")

        return "\n".join(lines)
    except ImportError:
        return "[check_username_across_platforms error] Please run: pip install requests"
    except Exception as e:
        return f"[check_username_across_platforms error] {e}"


# ── Tool 21: Instagram Profile Scraper ───────────────────────────────────────
@register_tool(
    "get_instagram_profile",
    "Fetch public information from an Instagram profile: follower count, bio, post count, and emails found in the bio.",
    {"username": "string — Instagram username without the @ symbol"},
)
def get_instagram_profile(username: str) -> str:
    try:
        import instaloader
        import re

        L = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(L.context, username.strip())

        bio = profile.biography or ""
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", bio, re.IGNORECASE)

        return (
            f"Username     : {profile.username}\n"
            f"Full Name    : {profile.full_name}\n"
            f"User ID      : {profile.userid}\n"
            f"Followers    : {profile.followers}\n"
            f"Following    : {profile.followees}\n"
            f"Posts        : {profile.mediacount}\n"
            f"Bio          : {bio}\n"
            f"Emails in bio: {', '.join(emails) if emails else 'None found'}\n"
            f"External URL : {profile.external_url or 'None'}\n"
            f"Private      : {profile.is_private}\n"
            f"Verified     : {profile.is_verified}\n"
            f"Profile Pic  : {profile.profile_pic_url}"
        )
    except ImportError:
        return "[get_instagram_profile error] Please run: pip install instaloader"
    except Exception as e:
        return f"[get_instagram_profile error] {e}"


# ── Tool 22: Phone Number Analyser ────────────────────────────────────────────
@register_tool(
    "analyse_phone_number",
    "Analyse a phone number to determine its country, carrier, number type (mobile/landline/VoIP), time zone, and validity.",
    {
        "phone_number": "string — phone number in E.164 or local format (e.g., '+12025550123' or '06201234567')",
        "region": "string — optional 2-letter region code to aid parsing if no country code is present (e.g., 'HU', 'US')",
    },
)
def analyse_phone_number(phone_number: str, region: str = "") -> str:
    try:
        import phonenumbers
        from phonenumbers import geocoder, carrier, timezone as tz_mod
        from phonenumbers.phonenumberutil import NumberParseException

        parsed = phonenumbers.parse(phone_number, region.upper() if region else None)
        is_valid    = phonenumbers.is_valid_number(parsed)
        is_possible = phonenumbers.is_possible_number(parsed)

        number_type_map = {
            phonenumbers.PhoneNumberType.FIXED_LINE            : "Fixed Line",
            phonenumbers.PhoneNumberType.MOBILE                : "Mobile",
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE  : "Fixed Line or Mobile",
            phonenumbers.PhoneNumberType.TOLL_FREE             : "Toll-Free",
            phonenumbers.PhoneNumberType.PREMIUM_RATE          : "Premium Rate",
            phonenumbers.PhoneNumberType.VOIP                  : "VoIP",
            phonenumbers.PhoneNumberType.UNKNOWN               : "Unknown",
        }
        num_type = number_type_map.get(phonenumbers.number_type(parsed), "Unknown")

        return (
            f"Phone Number    : {phone_number}\n"
            f"Valid           : {is_valid}\n"
            f"Possible        : {is_possible}\n"
            f"Country Code    : +{parsed.country_code}\n"
            f"National Number : {parsed.national_number}\n"
            f"International   : {phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)}\n"
            f"E.164 Format    : {phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)}\n"
            f"Location        : {geocoder.description_for_number(parsed, 'en')}\n"
            f"Carrier         : {carrier.name_for_number(parsed, 'en') or 'Unknown'}\n"
            f"Time Zone(s)    : {', '.join(tz_mod.time_zones_for_number(parsed)) or 'Unknown'}\n"
            f"Number Type     : {num_type}"
        )
    except ImportError:
        return "[analyse_phone_number error] Please run: pip install phonenumbers"
    except Exception as e:
        return f"[analyse_phone_number error] {e}"


# ── Tool 23: QR Code Generator ───────────────────────────────────────────────
@register_tool(
    "generate_qr_code",
    "Generate a QR code image from any text or URL and save it as 'qrcode_output.png' in the current directory.",
    {"data": "string — text, URL, or any content to encode in the QR code"},
)
def generate_qr_code(data: str) -> str:
    try:
        import qrcode as qrlib

        qr = qrlib.QRCode(
            error_correction=qrlib.constants.ERROR_CORRECT_Q,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        output_path = os.path.abspath("qrcode_output.png")
        img.save(output_path)
        return f"QR code saved to: {output_path}"
    except ImportError:
        return "[generate_qr_code error] Please run: pip install qrcode[pil]"
    except Exception as e:
        return f"[generate_qr_code error] {e}"


# ── Tool 24: ASCII Art Generator ─────────────────────────────────────────────
@register_tool(
    "generate_ascii_art",
    "Convert text to ASCII art using a pyfiglet font. Use 'list_ascii_fonts' tool to see available font names.",
    {
        "text": "string — the text to render as ASCII art",
        "font": "string — pyfiglet font name (e.g., 'slant', 'banner', 'block'). Default is 'standard'.",
    },
)
def generate_ascii_art(text: str, font: str = "standard") -> str:
    try:
        from pyfiglet import Figlet
        fig = Figlet(font=font)
        return fig.renderText(text)
    except ImportError:
        return "[generate_ascii_art error] Please run: pip install pyfiglet"
    except Exception as e:
        return f"[generate_ascii_art error] {e} — use 'list_ascii_fonts' to see valid font names."


# ── Tool 25: List ASCII Art Fonts ────────────────────────────────────────────
@register_tool(
    "list_ascii_fonts",
    "Return a list of all available pyfiglet font names that can be used with 'generate_ascii_art'.",
    {},
)
def list_ascii_fonts() -> str:
    try:
        from pyfiglet import FigletFont
        fonts = FigletFont.getFonts()
        return f"{len(fonts)} fonts available:\n" + ", ".join(sorted(fonts))
    except ImportError:
        return "[list_ascii_fonts error] Please run: pip install pyfiglet"
    except Exception as e:
        return f"[list_ascii_fonts error] {e}"


# ── Tool 26: Get Weather ─────────────────────────────────────────────────────
@register_tool(
    "get_weather",
    "Fetch current weather conditions for any city using the wttr.in service.",
    {"city": "string — city name (e.g., 'Budapest', 'London', 'New York')"},
)
def get_weather(city: str) -> str:
    try:
        import requests
        city = city.strip() or "London"
        response = requests.get(f"http://wttr.in/{city}?format=3", timeout=8)
        return response.text.strip() or f"Could not retrieve weather for {city}."
    except ImportError:
        return "[get_weather error] Please run: pip install requests"
    except Exception as e:
        return f"[get_weather error] {e}"


# ── Tool 27: Image to ASCII Art ──────────────────────────────────────────────
@register_tool(
    "image_to_ascii",
    "Convert a local image file to ASCII art rendered in the terminal.",
    {
        "image_path": "string — absolute or relative path to the image file (e.g., 'C:/photo.jpg')",
        "width": "string — output width in characters (default '75')",
    },
)
def image_to_ascii(image_path: str, width: str = "75") -> str:
    try:
        from PIL import Image

        ASCII_CHARS = " .:-=+*#%@"
        new_width = int(width)
        path = os.path.expandvars(os.path.expanduser(image_path))

        if not os.path.exists(path):
            return f"[image_to_ascii error] File not found: {path}"

        image = Image.open(path)
        w, h = image.size
        new_height = int(new_width * (h / w) * 0.55)
        image = image.resize((new_width, new_height)).convert("L")

        pixels = image.getdata()
        chars = "".join(ASCII_CHARS[px * len(ASCII_CHARS) // 256] for px in pixels)
        rows = [chars[i : i + new_width] for i in range(0, len(chars), new_width)]
        return "\n".join(rows)
    except ImportError:
        return "[image_to_ascii error] Please run: pip install Pillow"
    except Exception as e:
        return f"[image_to_ascii error] {e}"


# ── Tool 28: Extract EXIF Metadata from Image ─────────────────────────────────
@register_tool(
    "extract_exif_metadata",
    "Read and return all EXIF metadata embedded in a JPEG/TIFF image file (camera model, GPS coords, timestamps, etc.).",
    {"image_path": "string — absolute path to the image file"},
)
def extract_exif_metadata(image_path: str) -> str:
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        path = os.path.expandvars(os.path.expanduser(image_path))
        if not os.path.isfile(path):
            return f"[extract_exif_metadata error] File not found: {path}"

        image = Image.open(path)
        exif_data = image._getexif()

        if not exif_data:
            return f"No EXIF metadata found in: {path}"

        lines = [f"EXIF metadata for {path}:"]
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", errors="ignore")
                except Exception:
                    value = f"<binary {len(value)} bytes>"
            lines.append(f"  {tag_name}: {value}")
        return "\n".join(lines)
    except ImportError:
        return "[extract_exif_metadata error] Please run: pip install Pillow"
    except Exception as e:
        return f"[extract_exif_metadata error] {e}"


# ── Tool 29: Secure File Shredder ────────────────────────────────────────────
@register_tool(
    "shred_file",
    "Securely delete a file by overwriting its contents with random data 3 times before removing it. This makes recovery much harder.",
    {"file_path": "string — absolute path to the file to shred"},
    dangerous=True,
)
def shred_file(file_path: str) -> str:
    try:
        path = os.path.expandvars(os.path.expanduser(file_path))
        if not os.path.exists(path):
            return f"[shred_file error] File not found: {path}"

        with open(path, "ba+") as f:
            length = f.seek(0, 2)
            for _ in range(3):
                f.seek(0)
                f.write(os.urandom(length))

        os.remove(path)
        return f"File securely shredded and deleted: {path}"
    except Exception as e:
        return f"[shred_file error] {e}"


# ── Tool 30: System Resource Monitor ─────────────────────────────────────────
@register_tool(
    "get_system_resources",
    "Return current CPU usage, memory usage, and disk usage statistics for the local machine.",
    {},
)
def get_system_resources() -> str:
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return (
            f"CPU Usage         : {cpu}%\n"
            f"Memory Used       : {mem.percent}%  "
            f"({round(mem.used / 1024**3, 2)} GB / {round(mem.total / 1024**3, 2)} GB)\n"
            f"Disk Used         : {disk.percent}%  "
            f"({round(disk.used / 1024**3, 2)} GB / {round(disk.total / 1024**3, 2)} GB)"
        )
    except ImportError:
        return "[get_system_resources error] Please run: pip install psutil"
    except Exception as e:
        return f"[get_system_resources error] {e}"


# ── Tool 31: BTC Wallet Balance Checker ──────────────────────────────────────
@register_tool(
    "check_btc_wallet",
    "Look up the balance and basic transaction stats for a Bitcoin wallet address using the blockchain.info API.",
    {"wallet_address": "string — Bitcoin wallet address to query"},
)
def check_btc_wallet(wallet_address: str) -> str:
    try:
        import requests

        url = f"https://blockchain.info/rawaddr/{wallet_address.strip()}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        balance_btc = data["final_balance"] / 1e8
        total_received = data["total_received"] / 1e8
        total_sent = data["total_sent"] / 1e8
        tx_count = data["n_tx"]

        return (
            f"Bitcoin Wallet   : {wallet_address}\n"
            f"Balance          : {balance_btc:.8f} BTC\n"
            f"Total Received   : {total_received:.8f} BTC\n"
            f"Total Sent       : {total_sent:.8f} BTC\n"
            f"Total Tx Count   : {tx_count}"
        )
    except ImportError:
        return "[check_btc_wallet error] Please run: pip install requests"
    except Exception as e:
        return f"[check_btc_wallet error] {e}"


# ── Tool 32: BTC Wallet Detailed Info ────────────────────────────────────────
@register_tool(
    "get_btc_wallet_details",
    "Retrieve detailed Bitcoin wallet info including balance in USD, creation date, last transaction date, and up to 5 recent transactions via the Blockstream API.",
    {"wallet_address": "string — Bitcoin wallet address to query"},
)
def get_btc_wallet_details(wallet_address: str) -> str:
    try:
        import requests
        from datetime import datetime

        address = wallet_address.strip()
        base_url = "https://blockstream.info/api"

        # Price
        price_r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=8,
        )
        btc_price = price_r.json().get("bitcoin", {}).get("usd", 0)

        # Wallet stats
        wallet_r = requests.get(f"{base_url}/address/{address}", timeout=8)
        wallet_r.raise_for_status()
        d = wallet_r.json()

        balance_btc = (d["chain_stats"]["funded_txo_sum"] - d["chain_stats"]["spent_txo_sum"]) / 1e8
        value_usd = balance_btc * btc_price
        tx_count = d["chain_stats"]["tx_count"]

        lines = [
            f"Address          : {address}",
            f"Balance          : {balance_btc:.8f} BTC",
            f"Value (USD)      : ${value_usd:,.2f}",
            f"Total Tx Count   : {tx_count}",
        ]

        # Recent transactions
        if tx_count > 0:
            tx_r = requests.get(f"{base_url}/address/{address}/txs", timeout=8)
            txs = tx_r.json()
            lines.append("\nRecent Transactions (up to 5):")
            for tx in txs[:5]:
                ts = tx.get("status", {}).get("block_time")
                dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "unconfirmed"
                amount = sum(v["value"] for v in tx["vout"]) / 1e8
                lines.append(f"  {dt}  |  {amount:.8f} BTC  |  txid: {tx['txid'][:20]}…")

        return "\n".join(lines)
    except ImportError:
        return "[get_btc_wallet_details error] Please run: pip install requests"
    except Exception as e:
        return f"[get_btc_wallet_details error] {e}"


# ── Tool 33: MD5 Hash Cracker (Wordlist) ─────────────────────────────────────
@register_tool(
    "crack_md5_hash",
    "Attempt to crack an MD5 hash by comparing it against a wordlist file. The wordlist file must exist on disk.",
    {
        "hash_value": "string — the MD5 hash to crack (32 hex characters)",
        "wordlist_path": "string — path to a plaintext wordlist file, one word per line (e.g., 'passwords.txt')",
    },
)
def crack_md5_hash(hash_value: str, wordlist_path: str) -> str:
    try:
        import hashlib

        path = os.path.expandvars(os.path.expanduser(wordlist_path))
        if not os.path.isfile(path):
            return f"[crack_md5_hash error] Wordlist file not found: {path}"

        hash_value = hash_value.strip().lower()
        with open(path, "r", errors="ignore") as f:
            for line in f:
                word = line.rstrip("\n")
                if hashlib.md5(word.encode()).hexdigest() == hash_value:
                    return f"Hash cracked! '{hash_value}'  →  plaintext: '{word}'"

        return f"Hash not found in wordlist: {hash_value}"
    except Exception as e:
        return f"[crack_md5_hash error] {e}"


# ── Tool 34: Run JavaScript on a Web Page ────────────────────────────────────
@register_tool(
    "run_js_on_page",
    "Load a URL in a headless Chromium browser (via Playwright) and execute a JavaScript snippet, returning the result as JSON.",
    {
        "url": "string — the page URL to open",
        "js_code": "string — JavaScript expression to evaluate (e.g., '() => document.title')",
    },
)
def run_js_on_page(url: str, js_code: str) -> str:
    try:
        import json
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, timeout=15000)
            result = page.evaluate(js_code)
            browser.close()

        return json.dumps(result, indent=2, ensure_ascii=False)
    except ImportError:
        return "[run_js_on_page error] Please run: pip install playwright && playwright install chromium"
    except Exception as e:
        return f"[run_js_on_page error] {e}"


# ── Tool 35: Website Security Audit (via JS) ──────────────────────────────────
@register_tool(
    "audit_website_security",
    "Run a client-side security audit on a URL using a headless browser: checks HTTPS, missing security headers, cookie flags, potential XSS sinks, and exposed globals.",
    {"url": "string — the website URL to audit (e.g., 'https://example.com')"},
)
def audit_website_security(url: str) -> str:
    audit_js = """async () => {
  const issues = [];
  if (location.protocol !== "https:") {
    issues.push({ type: "transport", issue: "Site is not using HTTPS" });
  }
  try {
    const res = await fetch(location.href, { method: "HEAD" });
    const required = [
      "content-security-policy","x-frame-options",
      "x-content-type-options","referrer-policy","strict-transport-security"
    ];
    for (const h of required) {
      if (!res.headers.get(h)) {
        issues.push({ type: "header", issue: "Missing security header: " + h });
      }
    }
  } catch(e) {
    issues.push({ type: "header", issue: "Could not read headers (CORS)" });
  }
  const sinks = ["innerHTML","outerHTML","document.write","eval(","setTimeout(","setInterval("];
  const html = document.documentElement.innerHTML;
  sinks.forEach(s => {
    if (html.includes(s)) {
      issues.push({ type: "xss", issue: "Potential DOM XSS sink: " + s });
    }
  });
  const sensitiveNames = ["token","apikey","secret","password"];
  Object.keys(window).forEach(k => {
    sensitiveNames.forEach(n => {
      if (k.toLowerCase().includes(n)) {
        issues.push({ type: "exposure", issue: "Possible exposed global: window." + k });
      }
    });
  });
  return { url: location.href, issue_count: issues.length, issues };
}"""
    try:
        import json
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, timeout=15000)
            result = page.evaluate(audit_js)
            browser.close()

        count = result.get("issue_count", 0)
        issues = result.get("issues", [])

        if count == 0:
            return f"Security audit for {url}: No issues detected."

        lines = [f"Security audit for {url}: {count} issue(s) found:"]
        for issue in issues:
            lines.append(f"  [{issue['type'].upper()}] {issue['issue']}")
        return "\n".join(lines)
    except ImportError:
        return "[audit_website_security error] Please run: pip install playwright && playwright install chromium"
    except Exception as e:
        return f"[audit_website_security error] {e}"


# ── Tool 36: Webcam ASCII Stream (snapshot) ───────────────────────────────────
@register_tool(
    "capture_webcam_ascii_snapshot",
    "Capture a single frame from the default webcam and return it rendered as ASCII art.",
    {
        "width": "string — ASCII output width in characters (default '80')",
    },
)
def capture_webcam_ascii_snapshot(width: str = "80") -> str:
    try:
        import cv2
        from PIL import Image

        ASCII_CHARS = " .:-=+*#%@"
        new_width = int(width)

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "[capture_webcam_ascii_snapshot error] Cannot open webcam."
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return "[capture_webcam_ascii_snapshot error] Failed to grab frame."

        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        w, h = image.size
        new_height = int(new_width * (h / w) * 0.55)
        image = image.resize((new_width, new_height)).convert("L")

        pixels = image.getdata()
        chars = "".join(ASCII_CHARS[px * len(ASCII_CHARS) // 256] for px in pixels)
        rows = [chars[i : i + new_width] for i in range(0, len(chars), new_width)]
        return "\n".join(rows)
    except ImportError:
        return "[capture_webcam_ascii_snapshot error] Please run: pip install opencv-python Pillow"
    except Exception as e:
        return f"[capture_webcam_ascii_snapshot error] {e}"