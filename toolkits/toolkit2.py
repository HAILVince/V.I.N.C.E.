"""
BlackFox Consolidated Toolkit
─────────────────────────────────────────────────────────────────
Combines tools from:
  • insta_modules.py    — Instagram profile analysis
  • Black_Widow.py      — OSINT recon (domain / IP / email / username)
  • BlackRaven.py       — Classical & modern cipher tools
  • BlackEagle.py       — Network scanning & monitoring
  • BlackCrocodile.py   — Log analysis & intrusion detection

Usage: Drop into toolkits/ or load via Sidebar → 📦 Load Toolkit
─────────────────────────────────────────────────────────────────

REQUIREMENTS (install as needed):
  pip install requests dnspython instaloader scapy netifaces
─────────────────────────────────────────────────────────────────
"""

from tools import register_tool


# ══════════════════════════════════════════════════════════════════
#  INSTAGRAM ANALYSIS  (from insta_modules.py)
# ══════════════════════════════════════════════════════════════════

@register_tool(
    "instagram_analyze",
    "Analyze a public Instagram profile: followers, bio, contact info, "
    "hashtags, mentions, and recent post statistics. "
    "Requires: pip install instaloader",
    {"username": "string — Instagram username (with or without @)"},
)
def instagram_analyze(username: str) -> str:
    try:
        import re
        import instaloader
        from datetime import datetime

        username = username.replace("@", "").strip()
        if not username:
            return "[instagram_analyze error] No username provided."

        L = instaloader.Instaloader()

        try:
            profile = instaloader.Profile.from_username(L.context, username)
        except instaloader.exceptions.ProfileNotExistsException:
            return f"[instagram_analyze] Profile '{username}' does not exist."
        except instaloader.exceptions.LoginRequiredException:
            return f"[instagram_analyze] Profile '{username}' is private (login required)."
        except Exception as e:
            return f"[instagram_analyze error] {e}"

        bio = profile.biography or ""

        # Extract contact info from bio
        emails = list(set(re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,63}', bio)))
        phones = list(set(re.findall(r'\+?\d[\d\s\-().]{7,}\d', bio)))
        hashtags = list(set(re.findall(r'#(\w+)', bio)))
        mentions = list(set(re.findall(r'@(\w+)', bio)))

        lines = [
            f"=== Instagram Profile: @{profile.username} ===",
            f"Full Name      : {profile.full_name}",
            f"User ID        : {profile.userid}",
            f"Followers      : {profile.followers:,}",
            f"Following      : {profile.followees:,}",
            f"Posts          : {profile.mediacount:,}",
            f"Private        : {profile.is_private}",
            f"Verified       : {profile.is_verified}",
            f"Business       : {profile.is_business_account}",
            f"Bio            : {bio[:200]}{'...' if len(bio) > 200 else ''}",
            f"External URL   : {profile.external_url or 'None'}",
            "",
            f"--- Contact Info in Bio ---",
            f"Emails         : {', '.join(emails) if emails else 'None'}",
            f"Phones         : {', '.join(phones) if phones else 'None'}",
            f"Hashtags       : {', '.join(hashtags) if hashtags else 'None'}",
            f"Mentions       : {', '.join(mentions) if mentions else 'None'}",
        ]

        # Recent post stats (public profiles only)
        if not profile.is_private:
            try:
                total_likes = total_comments = post_count = 0
                for post in profile.get_posts():
                    if post_count >= 10:
                        break
                    total_likes += post.likes
                    total_comments += post.comments
                    post_count += 1

                if post_count > 0:
                    lines += [
                        "",
                        f"--- Recent Posts (last {post_count}) ---",
                        f"Avg Likes      : {total_likes / post_count:.1f}",
                        f"Avg Comments   : {total_comments / post_count:.1f}",
                    ]
            except Exception as e:
                lines.append(f"[post stats error] {e}")

        return "\n".join(lines)

    except ImportError:
        return "[instagram_analyze] Install instaloader: pip install instaloader"
    except Exception as e:
        return f"[instagram_analyze error] {e}"


# ══════════════════════════════════════════════════════════════════
#  OSINT RECON TOOLS  (from Black_Widow.py)
# ══════════════════════════════════════════════════════════════════

@register_tool(
    "detect_target_type",
    "Auto-detect whether a target string is a domain, IP address, email, "
    "or username.",
    {"target": "string — the target to classify"},
)
def detect_target_type(target: str) -> str:
    try:
        import re

        target = str(target).strip().lower()

        ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
        if re.match(ipv4_pattern, target):
            return f"Type: ip\nNormalized: {target}"

        if ':' in target and '.' not in target:
            return f"Type: ip (IPv6)\nNormalized: {target}"

        email_pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, target):
            return f"Type: email\nNormalized: {target}"

        clean = target.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
        domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        if re.match(domain_pattern, clean):
            return f"Type: domain\nNormalized: {clean}"

        username_pattern = r'^[a-zA-Z0-9_\-\.]+$'
        if re.match(username_pattern, target) and 3 <= len(target) <= 50:
            return f"Type: username\nNormalized: {target}"

        return f"Type: unknown\nNormalized: {target}"

    except Exception as e:
        return f"[detect_target_type error] {e}"


@register_tool(
    "whois_lookup",
    "Perform a WHOIS lookup for a domain — returns registration info sources.",
    {"domain": "string — the domain name to look up"},
)
def whois_lookup(domain: str) -> str:
    try:
        import requests

        domain = domain.strip().lower().replace('http://', '').replace('https://', '').split('/')[0]
        sources = [
            f"https://www.whois.com/whois/{domain}",
            f"https://who.is/whois/{domain}",
            f"https://rdap.org/domain/{domain}",
        ]

        lines = [f"=== WHOIS Lookup: {domain} ==="]
        for url in sources:
            try:
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
                status = "✓ reachable" if r.status_code == 200 else f"HTTP {r.status_code}"
            except Exception as e:
                status = f"✗ {e}"
            lines.append(f"{url}  [{status}]")

        lines.append("\nOpen any of the above URLs in a browser for full WHOIS data.")
        return "\n".join(lines)

    except ImportError:
        return "[whois_lookup] Install requests: pip install requests"
    except Exception as e:
        return f"[whois_lookup error] {e}"


@register_tool(
    "server_info",
    "Fetch HTTP/HTTPS server headers and basic response info for a domain.",
    {"domain": "string — domain name or URL"},
)
def server_info(domain: str) -> str:
    try:
        import requests, warnings
        warnings.filterwarnings("ignore")

        domain = domain.strip().replace('http://', '').replace('https://', '').split('/')[0]
        headers_of_interest = ['server', 'x-powered-by', 'x-frame-options',
                                'content-security-policy', 'strict-transport-security',
                                'x-content-type-options', 'x-xss-protection']

        lines = [f"=== Server Info: {domain} ==="]
        for protocol in ['https', 'http']:
            url = f"{protocol}://{domain}"
            try:
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'},
                                 timeout=10, verify=False, allow_redirects=True)
                lines.append(f"\n[{protocol.upper()}] Status: {r.status_code}")
                lines.append(f"Final URL   : {r.url}")
                for h in headers_of_interest:
                    if h in r.headers:
                        lines.append(f"{h.capitalize():32}: {r.headers[h]}")
                break
            except Exception as e:
                lines.append(f"[{protocol.upper()}] Error: {e}")

        return "\n".join(lines)

    except ImportError:
        return "[server_info] Install requests: pip install requests"
    except Exception as e:
        return f"[server_info error] {e}"


@register_tool(
    "subdomain_scan",
    "Probe common subdomain prefixes via DNS to find live subdomains.",
    {"domain": "string — the base domain name (e.g. example.com)"},
)
def subdomain_scan(domain: str) -> str:
    try:
        import socket

        domain = domain.strip().lower().replace('http://', '').replace('https://', '').split('/')[0]
        common_subs = [
            'www', 'mail', 'ftp', 'admin', 'blog', 'webmail',
            'test', 'dev', 'staging', 'api', 'secure', 'portal',
            'cpanel', 'whm', 'webdisk', 'ns1', 'ns2', 'smtp',
            'imap', 'pop', 'vpn', 'remote', 'cdn', 'static',
        ]

        found = []
        for sub in common_subs:
            fqdn = f"{sub}.{domain}"
            try:
                ip = socket.gethostbyname(fqdn)
                found.append(f"  {fqdn:<40} → {ip}")
            except socket.gaierror:
                pass

        if found:
            return f"=== Subdomain Scan: {domain} ===\nFound {len(found)} subdomains:\n" + "\n".join(found)
        return f"=== Subdomain Scan: {domain} ===\nNo common subdomains found."

    except Exception as e:
        return f"[subdomain_scan error] {e}"


@register_tool(
    "ip_geolocation",
    "Get geographic location, ISP, and ASN info for an IP address or domain.",
    {"target": "string — IPv4 address or domain name"},
)
def ip_geolocation(target: str) -> str:
    try:
        import requests, socket, re

        target = target.strip()
        # Resolve domain to IP if needed
        ipv4 = r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
        if not re.match(ipv4, target):
            domain = target.replace('http://', '').replace('https://', '').split('/')[0]
            try:
                ip = socket.gethostbyname(domain)
            except Exception as e:
                return f"[ip_geolocation] Cannot resolve '{domain}': {e}"
        else:
            ip = target

        apis = [
            f"https://ipapi.co/{ip}/json/",
            f"http://ip-api.com/json/{ip}",
        ]

        for api_url in apis:
            try:
                r = requests.get(api_url, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    lines = [f"=== IP Geolocation: {ip} ==="]
                    for k in ('ip', 'city', 'region', 'country_name', 'country',
                              'org', 'isp', 'asn', 'timezone', 'latitude', 'longitude'):
                        val = data.get(k) or data.get(k.replace('_name', ''))
                        if val:
                            lines.append(f"{k.replace('_', ' ').capitalize():<16}: {val}")
                    return "\n".join(lines)
            except Exception:
                continue

        return f"[ip_geolocation] All geolocation APIs failed for {ip}."

    except ImportError:
        return "[ip_geolocation] Install requests: pip install requests"
    except Exception as e:
        return f"[ip_geolocation error] {e}"


@register_tool(
    "reverse_dns",
    "Perform a reverse DNS lookup to find the hostname(s) for an IP or domain.",
    {"target": "string — IPv4 address or domain name"},
)
def reverse_dns(target: str) -> str:
    try:
        import socket, re

        target = target.strip()
        ipv4 = r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
        if not re.match(ipv4, target):
            domain = target.replace('http://', '').replace('https://', '').split('/')[0]
            try:
                ip = socket.gethostbyname(domain)
            except Exception as e:
                return f"[reverse_dns] Cannot resolve '{domain}': {e}"
        else:
            ip = target

        try:
            hostname, aliases, addr_list = socket.gethostbyaddr(ip)
            lines = [
                f"=== Reverse DNS: {ip} ===",
                f"Primary Hostname : {hostname}",
                f"Aliases          : {', '.join(aliases) if aliases else 'None'}",
                f"IP Addresses     : {', '.join(addr_list)}",
            ]
            return "\n".join(lines)
        except socket.herror:
            return f"=== Reverse DNS: {ip} ===\nNo reverse DNS entry found."

    except Exception as e:
        return f"[reverse_dns error] {e}"


@register_tool(
    "port_scan",
    "Scan common TCP ports on a host and report which are open.",
    {
        "target": "string — IP address or domain name",
        "timeout": "float — connection timeout per port in seconds (default: 1.0)",
    },
)
def port_scan(target: str, timeout: float = 1.0) -> str:
    try:
        import socket, re

        target = target.strip()
        ipv4 = r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
        if not re.match(ipv4, target):
            domain = target.replace('http://', '').replace('https://', '').split('/')[0]
            try:
                ip = socket.gethostbyname(domain)
            except Exception as e:
                return f"[port_scan] Cannot resolve '{domain}': {e}"
        else:
            ip = target

        common_ports = {
            21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
            53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
            443: "HTTPS", 445: "SMB", 3306: "MySQL", 3389: "RDP",
            5432: "PostgreSQL", 5900: "VNC", 8080: "HTTP-Alt", 8443: "HTTPS-Alt",
        }

        open_ports = []
        for port, service in common_ports.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(float(timeout))
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:
                    open_ports.append(f"  {port:<6} {service}")
            except Exception:
                pass

        header = f"=== Port Scan: {ip} (timeout={timeout}s) ==="
        if open_ports:
            return header + f"\nOpen ports ({len(open_ports)}/{len(common_ports)} checked):\n" + "\n".join(open_ports)
        return header + "\nNo open ports found among the checked set."

    except Exception as e:
        return f"[port_scan error] {e}"


@register_tool(
    "email_validate",
    "Validate email syntax, check for disposable domains, and look up MX records.",
    {"email": "string — the email address to validate"},
)
def email_validate(email: str) -> str:
    try:
        import re

        email = email.strip().lower()
        email_pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        valid_syntax = bool(re.match(email_pattern, email))

        lines = [
            f"=== Email Validation: {email} ===",
            f"Valid Syntax    : {valid_syntax}",
        ]

        if valid_syntax:
            domain = email.split('@')[1]
            lines.append(f"Domain          : {domain}")

            disposable = ['tempmail.com', 'mailinator.com', 'guerrillamail.com',
                          '10minutemail.com', 'throwawaymail.com', 'yopmail.com',
                          'maildrop.cc', 'sharklasers.com', 'trashmail.com']
            is_disposable = any(d in domain for d in disposable)
            lines.append(f"Disposable      : {is_disposable}")

            try:
                import dns.resolver
                mx_records = dns.resolver.resolve(domain, 'MX')
                mx_list = sorted([str(r.exchange) for r in mx_records])
                lines.append(f"MX Records      : {', '.join(mx_list)}")
            except ImportError:
                lines.append("MX Records      : (install dnspython: pip install dnspython)")
            except Exception as e:
                lines.append(f"MX Records      : lookup failed — {e}")

        return "\n".join(lines)

    except Exception as e:
        return f"[email_validate error] {e}"


@register_tool(
    "email_breach_info",
    "Return the API endpoint and instructions for checking an email in the "
    "HaveIBeenPwned breach database (API key required).",
    {"email": "string — the email address to check"},
)
def email_breach_info(email: str) -> str:
    return (
        f"=== Email Breach Check: {email} ===\n"
        "Use the HaveIBeenPwned API:\n"
        f"  Endpoint : https://haveibeenpwned.com/api/v3/breachedaccount/{email}\n"
        "  Header   : hibp-api-key: <YOUR_API_KEY>\n"
        "  Docs     : https://haveibeenpwned.com/API/v3\n"
        "\n"
        "Get an API key at: https://haveibeenpwned.com/API/Key"
    )


@register_tool(
    "username_search",
    "Generate direct profile URLs for a username across major platforms "
    "and check which respond with HTTP 200.",
    {"username": "string — the username to search"},
)
def username_search(username: str) -> str:
    try:
        import requests

        username = username.strip()
        platforms = {
            "GitHub":    f"https://github.com/{username}",
            "Twitter":   f"https://twitter.com/{username}",
            "Instagram": f"https://instagram.com/{username}",
            "Reddit":    f"https://reddit.com/user/{username}",
            "YouTube":   f"https://youtube.com/@{username}",
            "Facebook":  f"https://facebook.com/{username}",
            "TikTok":    f"https://tiktok.com/@{username}",
            "Twitch":    f"https://twitch.tv/{username}",
            "Pinterest": f"https://pinterest.com/{username}",
            "LinkedIn":  f"https://linkedin.com/in/{username}",
        }

        lines = [f"=== Username Search: {username} ==="]
        for platform, url in platforms.items():
            try:
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'},
                                 timeout=6, allow_redirects=True)
                status = "✓ likely exists" if r.status_code == 200 else f"HTTP {r.status_code}"
            except Exception as e:
                status = f"✗ {e}"
            lines.append(f"  {platform:<12} {status:<22} {url}")

        return "\n".join(lines)

    except ImportError:
        return "[username_search] Install requests: pip install requests"
    except Exception as e:
        return f"[username_search error] {e}"


@register_tool(
    "social_media_links",
    "Generate social media profile URL list for a given username.",
    {"username": "string — the username to generate links for"},
)
def social_media_links(username: str) -> str:
    username = username.strip()
    platforms = {
        "GitHub":    f"https://github.com/{username}",
        "Twitter":   f"https://twitter.com/{username}",
        "Instagram": f"https://instagram.com/{username}",
        "LinkedIn":  f"https://linkedin.com/in/{username}",
        "Facebook":  f"https://facebook.com/{username}",
        "TikTok":    f"https://tiktok.com/@{username}",
        "Twitch":    f"https://twitch.tv/{username}",
        "Pinterest": f"https://pinterest.com/{username}",
        "YouTube":   f"https://youtube.com/@{username}",
        "Reddit":    f"https://reddit.com/user/{username}",
        "Snapchat":  f"https://snapchat.com/add/{username}",
        "Telegram":  f"https://t.me/{username}",
    }
    lines = [f"=== Social Media Links: {username} ==="]
    for platform, url in platforms.items():
        lines.append(f"  {platform:<12} {url}")
    return "\n".join(lines)


@register_tool(
    "basic_info",
    "Auto-detect target type (domain/IP/email/username) and return basic information.",
    {"target": "string — domain, IP, email, or username"},
)
def basic_info(target: str) -> str:
    try:
        import re, socket
        from datetime import datetime

        target = str(target).strip().lower()

        ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
        email_pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'

        if re.match(ipv4_pattern, target):
            t_type = "ip"
            normalized = target
        elif re.match(email_pattern, target):
            t_type = "email"
            normalized = target
        else:
            clean = target.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
            if re.match(domain_pattern, clean):
                t_type = "domain"
                normalized = clean
            else:
                t_type = "username"
                normalized = target

        lines = [
            f"=== Basic Info ===",
            f"Original Target : {target}",
            f"Normalized      : {normalized}",
            f"Type            : {t_type}",
            f"Timestamp       : {datetime.now().isoformat()}",
        ]

        if t_type == "domain":
            try:
                ip = socket.gethostbyname(normalized)
                lines.append(f"Resolved IP     : {ip}")
            except Exception:
                lines.append("Resolved IP     : (could not resolve)")
        elif t_type == "ip":
            lines.append(f"IP Address      : {normalized}")
        elif t_type == "email":
            lines.append(f"Domain Part     : {normalized.split('@')[1]}")
        elif t_type == "username":
            lines.append("Note            : Use username_search for detailed lookup.")

        return "\n".join(lines)

    except Exception as e:
        return f"[basic_info error] {e}"


@register_tool(
    "google_dorks",
    "Generate targeted Google search dork queries for a domain, email, or username.",
    {"target": "string — domain, email, or username"},
)
def google_dorks(target: str) -> str:
    try:
        import re

        target = target.strip().lower()
        email_pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'

        clean = target.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]

        if re.match(email_pattern, target):
            dorks = [
                f'"{target}"',
                f'"{target.split("@")[0]}"',
                f'site:linkedin.com "{target}"',
                f'site:github.com "{target}"',
            ]
            label = "email"
        elif re.match(domain_pattern, clean):
            dorks = [
                f"site:{clean}",
                f'site:{clean} filetype:pdf',
                f'site:{clean} inurl:admin',
                f'site:{clean} inurl:login',
                f'site:{clean} intitle:"index of"',
                f'site:{clean} ext:sql OR ext:bak OR ext:env',
                f'site:{clean} intext:password',
            ]
            label = "domain"
        else:
            dorks = [
                f'"{target}"',
                f'"{target}" site:twitter.com',
                f'"{target}" site:github.com',
                f'"{target}" site:reddit.com',
                f'"{target}" site:linkedin.com',
            ]
            label = "username"

        lines = [f"=== Google Dorks ({label}): {target} ==="]
        for i, d in enumerate(dorks, 1):
            lines.append(f"  {i}. {d}")
        lines.append("\nSearch on: https://www.google.com/search?q=<dork>")
        return "\n".join(lines)

    except Exception as e:
        return f"[google_dorks error] {e}"


# ══════════════════════════════════════════════════════════════════
#  CIPHER & ENCRYPTION TOOLS  (from BlackRaven.py)
# ══════════════════════════════════════════════════════════════════

@register_tool(
    "caesar_cipher",
    "Encrypt or decrypt text with the Caesar (shift) cipher.",
    {
        "text":    "string — the text to process",
        "shift":   "int — number of positions to shift (default: 3)",
        "mode":    "string — 'encrypt' or 'decrypt' (default: encrypt)",
    },
)
def caesar_cipher(text: str, shift: int = 3, mode: str = "encrypt") -> str:
    try:
        shift = int(shift)
        if mode.lower() == "decrypt":
            shift = -shift

        result = []
        for ch in text:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                result.append(chr((ord(ch) - base + shift) % 26 + base))
            else:
                result.append(ch)
        return "".join(result)

    except Exception as e:
        return f"[caesar_cipher error] {e}"


@register_tool(
    "atbash_cipher",
    "Encode or decode text with the Atbash cipher (A↔Z, B↔Y, etc.).",
    {"text": "string — the text to process"},
)
def atbash_cipher(text: str) -> str:
    try:
        result = []
        for ch in text:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                result.append(chr(base + 25 - (ord(ch) - base)))
            else:
                result.append(ch)
        return "".join(result)
    except Exception as e:
        return f"[atbash_cipher error] {e}"


@register_tool(
    "vigenere_cipher",
    "Encrypt or decrypt text using the Vigenère cipher with a keyword.",
    {
        "text":    "string — the text to process",
        "key":     "string — the keyword (letters only)",
        "mode":    "string — 'encrypt' or 'decrypt' (default: encrypt)",
    },
)
def vigenere_cipher(text: str, key: str, mode: str = "encrypt") -> str:
    try:
        key = ''.join(c for c in key.lower() if c.isalpha())
        if not key:
            return "[vigenere_cipher error] Key must contain at least one letter."

        result = []
        k_index = 0
        decrypt = mode.lower() == "decrypt"

        for ch in text:
            if ch.isalpha():
                shift = ord(key[k_index % len(key)]) - ord('a')
                if decrypt:
                    shift = -shift
                base = ord('A') if ch.isupper() else ord('a')
                result.append(chr((ord(ch) - base + shift) % 26 + base))
                k_index += 1
            else:
                result.append(ch)

        return "".join(result)

    except Exception as e:
        return f"[vigenere_cipher error] {e}"


@register_tool(
    "rot13",
    "Apply ROT13 encoding/decoding to a text string (symmetric).",
    {"text": "string — the text to ROT13"},
)
def rot13(text: str) -> str:
    try:
        import codecs
        return codecs.encode(text, 'rot_13')
    except Exception as e:
        return f"[rot13 error] {e}"


@register_tool(
    "affine_cipher",
    "Encrypt or decrypt text using the Affine cipher (y = ax + b mod 26).",
    {
        "text": "string — the text to process",
        "a":    "int — multiplicative key (must be coprime with 26; e.g. 5)",
        "b":    "int — additive key (e.g. 8)",
        "mode": "string — 'encrypt' or 'decrypt' (default: encrypt)",
    },
)
def affine_cipher(text: str, a: int = 5, b: int = 8, mode: str = "encrypt") -> str:
    try:
        a, b = int(a), int(b)
        from math import gcd
        if gcd(a, 26) != 1:
            return f"[affine_cipher error] 'a' ({a}) must be coprime with 26."

        def mod_inv(n, m):
            for i in range(1, m):
                if (n * i) % m == 1:
                    return i
            return None

        result = []
        decrypt = mode.lower() == "decrypt"
        a_inv = mod_inv(a, 26) if decrypt else None

        for ch in text:
            if ch.isalpha():
                base = ord('A') if ch.isupper() else ord('a')
                x = ord(ch) - base
                if decrypt:
                    c = (a_inv * (x - b)) % 26
                else:
                    c = (a * x + b) % 26
                result.append(chr(c + base))
            else:
                result.append(ch)

        return "".join(result)

    except Exception as e:
        return f"[affine_cipher error] {e}"


@register_tool(
    "substitution_cipher",
    "Encrypt or decrypt using a simple substitution cipher with a custom alphabet key.",
    {
        "text":       "string — the text to process",
        "key_alpha":  "string — 26-letter substitution alphabet (e.g. 'QWERTYUIOPASDFGHJKLZXCVBNM')",
        "mode":       "string — 'encrypt' or 'decrypt' (default: encrypt)",
    },
)
def substitution_cipher(text: str, key_alpha: str, mode: str = "encrypt") -> str:
    try:
        key_alpha = ''.join(c for c in key_alpha.upper() if c.isalpha())
        if len(key_alpha) != 26 or len(set(key_alpha)) != 26:
            return "[substitution_cipher error] Key must be exactly 26 unique letters."

        standard = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if mode.lower() == "decrypt":
            table = str.maketrans(key_alpha, standard)
        else:
            table = str.maketrans(standard, key_alpha)

        upper = text.upper().translate(table)
        # Restore original case
        result = []
        for orig, enc in zip(text, upper):
            result.append(enc if orig.isupper() else enc.lower() if orig.isalpha() else orig)
        return "".join(result)

    except Exception as e:
        return f"[substitution_cipher error] {e}"


@register_tool(
    "columnar_transposition",
    "Encrypt or decrypt text using the Columnar Transposition cipher.",
    {
        "text": "string — the text to process",
        "key":  "string — the keyword that defines column order",
        "mode": "string — 'encrypt' or 'decrypt' (default: encrypt)",
    },
)
def columnar_transposition(text: str, key: str, mode: str = "encrypt") -> str:
    try:
        key = key.upper()
        n_cols = len(key)
        order = sorted(range(n_cols), key=lambda i: key[i])

        if mode.lower() == "encrypt":
            pad = (-len(text)) % n_cols
            text = text + 'X' * pad
            n_rows = len(text) // n_cols
            grid = [text[i * n_cols:(i + 1) * n_cols] for i in range(n_rows)]
            return "".join("".join(row[c] for row in grid) for c in order)
        else:
            n_rows = len(text) // n_cols
            col_lengths = [n_rows] * n_cols
            cols = {}
            idx = 0
            for c in order:
                cols[c] = list(text[idx:idx + col_lengths[c]])
                idx += col_lengths[c]
            return "".join(cols[c].pop(0) for _ in range(n_rows) for c in range(n_cols))

    except Exception as e:
        return f"[columnar_transposition error] {e}"


@register_tool(
    "xor_cipher",
    "XOR-encrypt or decrypt bytes using a repeating key. "
    "Input/output in hex string.",
    {
        "hex_text": "string — hex-encoded bytes to process",
        "key":      "string — key string (repeated as needed)",
    },
)
def xor_cipher(hex_text: str, key: str) -> str:
    try:
        data = bytes.fromhex(hex_text.strip())
        key_bytes = key.encode()
        result = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))
        return result.hex()
    except Exception as e:
        return f"[xor_cipher error] {e}"


@register_tool(
    "base64_encode",
    "Encode a plain text string to Base64.",
    {"text": "string — the text to encode"},
)
def base64_encode(text: str) -> str:
    try:
        import base64
        return base64.b64encode(text.encode()).decode()
    except Exception as e:
        return f"[base64_encode error] {e}"


@register_tool(
    "base64_decode",
    "Decode a Base64 string back to plain text.",
    {"b64_text": "string — the Base64-encoded text to decode"},
)
def base64_decode(b64_text: str) -> str:
    try:
        import base64
        return base64.b64decode(b64_text.strip()).decode(errors='replace')
    except Exception as e:
        return f"[base64_decode error] {e}"


@register_tool(
    "hex_encode",
    "Encode a plain text string to hexadecimal.",
    {"text": "string — the text to encode"},
)
def hex_encode(text: str) -> str:
    try:
        return text.encode().hex()
    except Exception as e:
        return f"[hex_encode error] {e}"


@register_tool(
    "hex_decode",
    "Decode a hexadecimal string back to plain text.",
    {"hex_text": "string — the hex-encoded string to decode"},
)
def hex_decode(hex_text: str) -> str:
    try:
        return bytes.fromhex(hex_text.strip()).decode(errors='replace')
    except Exception as e:
        return f"[hex_decode error] {e}"


@register_tool(
    "morse_encode",
    "Encode plain text to Morse code.",
    {"text": "string — the text to convert to Morse"},
)
def morse_encode(text: str) -> str:
    try:
        morse_table = {
            'A': '.-',   'B': '-...', 'C': '-.-.',  'D': '-..',
            'E': '.',    'F': '..-.', 'G': '--.',    'H': '....',
            'I': '..',   'J': '.---', 'K': '-.-',   'L': '.-..',
            'M': '--',   'N': '-.',   'O': '---',    'P': '.--.',
            'Q': '--.-', 'R': '.-.',  'S': '...',    'T': '-',
            'U': '..-',  'V': '...-', 'W': '.--',    'X': '-..-',
            'Y': '-.--', 'Z': '--..',
            '0': '-----','1': '.----','2': '..---',  '3': '...--',
            '4': '....-','5': '.....','6': '-....',  '7': '--...',
            '8': '---..','9': '----.',
            '.': '.-.-.-',',': '--..--','?': '..--..',
            "'": '.----.','/': '-..-.', '(': '-.--.', ')': '-.--.-',
            '&': '.-...',':': '---...',';': '-.-.-.','=': '-...-',
            '+': '.-.-.','-': '-....-','_': '..--.-','"': '.-..-.',
            '$': '...-..-','!': '-.-.--','@': '.--.-.',
        }
        words = text.upper().split()
        encoded_words = []
        for word in words:
            encoded_words.append(" ".join(morse_table.get(ch, '?') for ch in word))
        return " / ".join(encoded_words)
    except Exception as e:
        return f"[morse_encode error] {e}"


@register_tool(
    "morse_decode",
    "Decode Morse code back to plain text. Use space between letters, ' / ' between words.",
    {"morse": "string — Morse code string to decode"},
)
def morse_decode(morse: str) -> str:
    try:
        morse_table = {
            '.-': 'A',   '-...': 'B',  '-.-.': 'C',  '-..': 'D',
            '.': 'E',    '..-.': 'F',  '--.': 'G',   '....': 'H',
            '..': 'I',   '.---': 'J',  '-.-': 'K',   '.-..': 'L',
            '--': 'M',   '-.': 'N',    '---': 'O',   '.--.': 'P',
            '--.-': 'Q', '.-.': 'R',   '...': 'S',   '-': 'T',
            '..-': 'U',  '...-': 'V',  '.--': 'W',   '-..-': 'X',
            '-.--': 'Y', '--..': 'Z',
            '-----': '0','----.' : '1',  '..---': '2','...--': '3',
            '....-': '4','.....' : '5',  '-....': '6','--...': '7',
            '---..': '8','----.': '9',
            '.-.-.-': '.','--..--': ',','..--..' : '?',
            '.----.': "'", '-..-.': '/', '-.--.': '(', '-.--.-': ')',
        }
        words = morse.strip().split(' / ')
        result = []
        for word in words:
            result.append("".join(morse_table.get(code, '?') for code in word.split()))
        return " ".join(result)
    except Exception as e:
        return f"[morse_decode error] {e}"


@register_tool(
    "reverse_text",
    "Reverse a text string (character-level).",
    {"text": "string — the text to reverse"},
)
def reverse_text(text: str) -> str:
    return text[::-1]


@register_tool(
    "bacon_cipher",
    "Encode or decode text using Francis Bacon's bilateral cipher (A/B alphabet).",
    {
        "text": "string — the text to process",
        "mode": "string — 'encode' or 'decode' (default: encode)",
    },
)
def bacon_cipher(text: str, mode: str = "encode") -> str:
    try:
        bacon_table = {
            'A': 'AAAAA', 'B': 'AAAAB', 'C': 'AAABA', 'D': 'AAABB',
            'E': 'AABAA', 'F': 'AABAB', 'G': 'AABBA', 'H': 'AABBB',
            'I': 'ABAAA', 'J': 'ABAAB', 'K': 'ABABA', 'L': 'ABABB',
            'M': 'ABBAA', 'N': 'ABBAB', 'O': 'ABBBA', 'P': 'ABBBB',
            'Q': 'BAAAA', 'R': 'BAAAB', 'S': 'BAABA', 'T': 'BAABB',
            'U': 'BABAA', 'V': 'BABAB', 'W': 'BABBA', 'X': 'BABBB',
            'Y': 'BAAAA', 'Z': 'BAAAB',
        }
        reverse = {v: k for k, v in bacon_table.items()}

        if mode.lower() == "encode":
            result = []
            for ch in text.upper():
                if ch in bacon_table:
                    result.append(bacon_table[ch])
                elif ch == ' ':
                    result.append(' ')
            return " ".join(result)
        else:
            tokens = text.upper().replace("  ", " / ").split()
            result = []
            buf = []
            for t in tokens:
                if t == '/':
                    result.append(' ')
                    continue
                buf.append(t)
                if len(buf) == 1 and len(buf[0]) == 5:
                    result.append(reverse.get(buf[0], '?'))
                    buf = []
            return "".join(result)

    except Exception as e:
        return f"[bacon_cipher error] {e}"


# ══════════════════════════════════════════════════════════════════
#  NETWORK SCANNING  (from BlackEagle.py)
# ══════════════════════════════════════════════════════════════════

@register_tool(
    "arp_network_scan",
    "Send ARP requests across a subnet and list responding devices (IP + MAC). "
    "Requires root/admin privileges and scapy: pip install scapy",
    {"ip_range": "string — CIDR range to scan, e.g. '192.168.1.0/24'"},
)
def arp_network_scan(ip_range: str) -> str:
    try:
        from scapy.all import ARP, Ether, srp

        arp = ARP(pdst=ip_range.strip())
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether / arp

        result = srp(packet, timeout=3, verbose=0)[0]
        if not result:
            return f"[arp_network_scan] No devices responded in range {ip_range}."

        lines = [f"=== ARP Scan: {ip_range} ===",
                 f"{'IP Address':<18} {'MAC Address':<20}"]
        for _, received in result:
            lines.append(f"{received.psrc:<18} {received.hwsrc:<20}")
        lines.append(f"\nTotal devices found: {len(result)}")
        return "\n".join(lines)

    except ImportError:
        return "[arp_network_scan] Install scapy: pip install scapy"
    except PermissionError:
        return "[arp_network_scan] Root/admin privileges required."
    except Exception as e:
        return f"[arp_network_scan error] {e}"


@register_tool(
    "tcp_port_scan",
    "Perform a TCP connect scan on a range or list of ports.",
    {
        "target":   "string — IP address to scan",
        "ports":    "string — port range '1-1024' or comma list '22,80,443' (default: common ports)",
        "timeout":  "float — timeout per port in seconds (default: 0.5)",
    },
)
def tcp_port_scan(target: str, ports: str = "21,22,23,25,53,80,110,143,443,445,3306,3389,5432,8080",
                  timeout: float = 0.5) -> str:
    try:
        import socket

        target = target.strip()
        port_list = []
        if '-' in ports:
            start, end = ports.split('-', 1)
            port_list = list(range(int(start), int(end) + 1))
        else:
            port_list = [int(p.strip()) for p in ports.split(',')]
        port_list = port_list[:500]  # Safety cap

        open_ports = []
        for port in port_list:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(float(timeout))
                if sock.connect_ex((target, port)) == 0:
                    open_ports.append(port)
                sock.close()
            except Exception:
                pass

        common = {21:"FTP",22:"SSH",23:"Telnet",25:"SMTP",53:"DNS",80:"HTTP",
                  110:"POP3",143:"IMAP",443:"HTTPS",445:"SMB",3306:"MySQL",
                  3389:"RDP",5432:"PostgreSQL",5900:"VNC",8080:"HTTP-Alt"}

        lines = [f"=== TCP Port Scan: {target} ===",
                 f"Checked: {len(port_list)} ports | Open: {len(open_ports)}"]
        for p in open_ports:
            lines.append(f"  {p:<6} {common.get(p, 'unknown')}")
        if not open_ports:
            lines.append("  (none found)")
        return "\n".join(lines)

    except Exception as e:
        return f"[tcp_port_scan error] {e}"


@register_tool(
    "mac_vendor_lookup",
    "Look up the hardware vendor for a MAC address using the IEEE OUI database online.",
    {"mac": "string — MAC address in any common format (e.g. 00:1A:2B:3C:4D:5E)"},
)
def mac_vendor_lookup(mac: str) -> str:
    try:
        import requests

        mac_clean = mac.strip().upper().replace('-', ':').replace('.', ':')
        oui = mac_clean[:8]  # First 3 octets

        try:
            r = requests.get(f"https://api.macvendors.com/{oui}", timeout=6)
            if r.status_code == 200:
                return f"MAC: {mac_clean}\nVendor: {r.text.strip()}"
            elif r.status_code == 404:
                return f"MAC: {mac_clean}\nVendor: Unknown (not in database)"
            else:
                return f"MAC: {mac_clean}\nAPI returned HTTP {r.status_code}"
        except Exception as e:
            return f"[mac_vendor_lookup] API failed: {e}"

    except ImportError:
        return "[mac_vendor_lookup] Install requests: pip install requests"
    except Exception as e:
        return f"[mac_vendor_lookup error] {e}"


@register_tool(
    "hostname_lookup",
    "Resolve a hostname to IP address(es) or perform reverse lookup for an IP.",
    {"target": "string — hostname or IP address"},
)
def hostname_lookup(target: str) -> str:
    try:
        import socket, re

        target = target.strip()
        ipv4 = r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
        lines = [f"=== Hostname Lookup: {target} ==="]

        if re.match(ipv4, target):
            # Reverse lookup
            try:
                h, aliases, ips = socket.gethostbyaddr(target)
                lines.append(f"Hostname  : {h}")
                lines.append(f"Aliases   : {', '.join(aliases) or 'None'}")
            except socket.herror:
                lines.append("Reverse DNS: No PTR record found.")
        else:
            # Forward lookup
            try:
                ips = socket.gethostbyname_ex(target)
                lines.append(f"Canonical : {ips[0]}")
                lines.append(f"Aliases   : {', '.join(ips[1]) or 'None'}")
                lines.append(f"IPs       : {', '.join(ips[2])}")
            except socket.gaierror as e:
                lines.append(f"Could not resolve: {e}")

        return "\n".join(lines)

    except Exception as e:
        return f"[hostname_lookup error] {e}"


@register_tool(
    "icmp_ping_sweep",
    "Perform an ICMP-style connectivity check across hosts in a subnet. "
    "Uses socket connect rather than raw ICMP, so no root required.",
    {
        "ip_range": "string — CIDR range, e.g. '192.168.1.0/24'",
        "timeout":  "float — timeout per host in seconds (default: 0.5)",
    },
)
def icmp_ping_sweep(ip_range: str, timeout: float = 0.5) -> str:
    try:
        import socket, ipaddress
        from concurrent.futures import ThreadPoolExecutor

        network = ipaddress.ip_network(ip_range.strip(), strict=False)
        hosts = list(network.hosts())
        if len(hosts) > 256:
            return f"[icmp_ping_sweep] Range too large ({len(hosts)} hosts). Use /24 or smaller."

        def check_host(ip):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(float(timeout))
                sock.connect((str(ip), 80))
                sock.close()
                return str(ip)
            except Exception:
                return None

        live = []
        with ThreadPoolExecutor(max_workers=50) as executor:
            for result in executor.map(check_host, hosts):
                if result:
                    live.append(result)

        lines = [f"=== Ping Sweep: {ip_range} ===",
                 f"Checked: {len(hosts)} hosts | Responding: {len(live)}"]
        for ip in sorted(live):
            lines.append(f"  {ip}")
        if not live:
            lines.append("  (no hosts responded on port 80)")
        return "\n".join(lines)

    except Exception as e:
        return f"[icmp_ping_sweep error] {e}"


# ══════════════════════════════════════════════════════════════════
#  INTRUSION DETECTION / LOG ANALYSIS  (from BlackCrocodile.py)
# ══════════════════════════════════════════════════════════════════

@register_tool(
    "analyze_auth_log",
    "Parse auth log text (e.g. /var/log/auth.log content) for brute-force "
    "SSH/login attempts. Reports IPs exceeding the threshold.",
    {
        "log_text":  "string — raw content of an auth log file",
        "threshold": "int — minimum failed attempts before flagging an IP (default: 5)",
    },
)
def analyze_auth_log(log_text: str, threshold: int = 5) -> str:
    try:
        import re
        from collections import Counter
        from datetime import datetime

        threshold = int(threshold)
        lines = log_text.split('\n')
        failed_attempts: Counter = Counter()
        ip_lines: dict = {}

        ip_pattern = re.compile(r'from\s+([\d.]+)')
        flag_patterns = ['Failed password', 'authentication failure',
                         'Invalid user', 'Connection closed by invalid user']

        for line in lines:
            if any(p in line for p in flag_patterns):
                m = ip_pattern.search(line)
                if m:
                    ip = m.group(1)
                    failed_attempts[ip] += 1
                    if ip not in ip_lines:
                        ip_lines[ip] = line.strip()

        flagged = {ip: count for ip, count in failed_attempts.items() if count >= threshold}

        result_lines = [
            f"=== Auth Log Analysis ===",
            f"Analyzed       : {len(lines)} lines",
            f"Unique IPs     : {len(failed_attempts)}",
            f"Flagged IPs    : {len(flagged)} (threshold >= {threshold})",
            "",
            f"{'IP Address':<18} {'Attempts':>8}  {'Sample Line'[:60]}",
            "-" * 90,
        ]

        for ip, count in sorted(flagged.items(), key=lambda x: -x[1]):
            sample = ip_lines.get(ip, '')[:60]
            result_lines.append(f"{ip:<18} {count:>8}  {sample}")

        if not flagged:
            result_lines.append("  No IPs exceeded the threshold.")

        return "\n".join(result_lines)

    except Exception as e:
        return f"[analyze_auth_log error] {e}"


@register_tool(
    "analyze_auth_log_file",
    "Read and analyze an auth log file on disk for brute-force attempts.",
    {
        "filepath":  "string — path to the log file (e.g. /var/log/auth.log)",
        "threshold": "int — minimum failed attempts to flag (default: 5)",
    },
)
def analyze_auth_log_file(filepath: str, threshold: int = 5) -> str:
    try:
        with open(filepath.strip(), 'r', errors='replace') as f:
            content = f.read()
        return analyze_auth_log(content, threshold)
    except FileNotFoundError:
        return f"[analyze_auth_log_file] File not found: {filepath}"
    except PermissionError:
        return f"[analyze_auth_log_file] Permission denied: {filepath}"
    except Exception as e:
        return f"[analyze_auth_log_file error] {e}"


@register_tool(
    "check_suspicious_payload",
    "Scan a payload/text snippet for common attack keywords "
    "(injection, command execution, etc.).",
    {"payload": "string — the text or packet payload to check"},
)
def check_suspicious_payload(payload: str) -> str:
    try:
        suspicious_keywords = {
            "Command Execution":    ['bash', 'wget', 'curl', 'exec', 'system(', 'popen', 'subprocess',
                                     '/bin/sh', '/bin/bash', 'cmd.exe', 'powershell'],
            "SQL Injection":        ['union select', 'drop table', 'insert into', "' or '1'='1",
                                     'xp_cmdshell', 'information_schema'],
            "XSS":                  ['<script', 'javascript:', 'onerror=', 'onload=', 'eval('],
            "Path Traversal":       ['../', '..\\', '/etc/passwd', '/etc/shadow', 'win.ini'],
            "Reverse Shell":        ['nc -e', 'netcat', '/dev/tcp', 'bash -i', 'python -c'],
        }

        payload_lower = payload.lower()
        hits = {}

        for category, keywords in suspicious_keywords.items():
            found = [kw for kw in keywords if kw.lower() in payload_lower]
            if found:
                hits[category] = found

        if hits:
            lines = ["=== Suspicious Payload Analysis ===",
                     f"Status: ⚠️  SUSPICIOUS — {len(hits)} categor{'y' if len(hits)==1 else 'ies'} triggered", ""]
            for cat, kws in hits.items():
                lines.append(f"[{cat}]")
                for kw in kws:
                    lines.append(f"  • '{kw}' found")
            return "\n".join(lines)
        else:
            return "=== Suspicious Payload Analysis ===\nStatus: ✓ Clean — no suspicious keywords detected."

    except Exception as e:
        return f"[check_suspicious_payload error] {e}"


@register_tool(
    "generate_block_command",
    "Generate the platform-appropriate firewall command to block an IP address.",
    {
        "ip":       "string — the IP address to block",
        "platform": "string — 'linux' (iptables) or 'windows' (netsh) — auto-detected if empty",
    },
)
def generate_block_command(ip: str, platform: str = "") -> str:
    try:
        import sys, re

        ip = ip.strip()
        ipv4 = r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
        if not re.match(ipv4, ip):
            return f"[generate_block_command] Invalid IP address: {ip}"

        if not platform:
            platform = 'windows' if sys.platform.startswith('win') else 'linux'

        if platform.lower() == 'windows':
            cmd = (f'netsh advfirewall firewall add rule '
                   f'name="Block {ip}" dir=in action=block remoteip={ip}')
        else:
            cmd = f'sudo iptables -A INPUT -s {ip} -j DROP'

        return (f"=== Block Command for {ip} ({platform}) ===\n"
                f"{cmd}\n\n"
                "⚠️  Run this command with appropriate privileges on your system.\n"
                "   This tool generates the command only; it does NOT execute it.")

    except Exception as e:
        return f"[generate_block_command error] {e}"