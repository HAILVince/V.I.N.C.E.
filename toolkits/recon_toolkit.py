"""
VINCE Recon Toolkit — OSINT & Network Reconnaissance Tools
Adds DNS enumeration, SSL cert inspection, reverse IP, ASN lookup, CVE search, URL scan, etc.
"""

from tools import register_tool
import socket
import re
import json
from typing import Optional

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# Helper for API calls
def _api_get(url: str, timeout=10) -> Optional[dict]:
    if not REQUESTS_OK:
        return None
    try:
        r = requests.get(url, timeout=timeout, headers={'User-Agent': 'VINCE-Recon/1.0'})
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


@register_tool(
    "dns_enum",
    "Retrieve DNS records (A, AAAA, MX, NS, TXT, CNAME) for a domain.",
    {"domain": "string — domain name to query"},
)
def dns_enum(domain: str) -> str:
    try:
        import dns.resolver
        records = {}
        types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME']
        for typ in types:
            try:
                answers = dns.resolver.resolve(domain, typ)
                records[typ] = [str(r) for r in answers]
            except Exception:
                records[typ] = []
        lines = [f"DNS Records for {domain}:"]
        for typ, values in records.items():
            if values:
                lines.append(f"  {typ}: {', '.join(values)}")
        if not any(records.values()):
            return f"No DNS records found for {domain}."
        return "\n".join(lines)
    except ImportError:
        return "[dns_enum] Install dnspython: pip install dnspython"
    except Exception as e:
        return f"[dns_enum error] {e}"


@register_tool(
    "reverse_ip_lookup",
    "Find domains hosted on the same IP address (using hackertarget.com API).",
    {"ip": "string — IPv4 address"},
)
def reverse_ip_lookup(ip: str) -> str:
    if not REQUESTS_OK:
        return "[reverse_ip_lookup] Install requests: pip install requests"
    try:
        url = f"https://api.hackertarget.com/reverseiplookup/?q={ip}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            domains = r.text.strip().splitlines()
            if domains and domains[0].startswith("Error"):
                return f"API error: {domains[0]}"
            if len(domains) == 1 and domains[0] == "":
                return f"No domains found for IP {ip}."
            return f"Domains on {ip}:\n" + "\n".join(domains[:20])
        return f"API returned HTTP {r.status_code}"
    except Exception as e:
        return f"[reverse_ip_lookup error] {e}"


@register_tool(
    "ssl_cert_info",
    "Fetch SSL/TLS certificate details (issuer, subject, expiry, SANs) for a domain.",
    {"domain": "string — domain name (e.g. example.com)"},
)
def ssl_cert_info(domain: str) -> str:
    try:
        import ssl
        import datetime
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
            s.settimeout(5)
            s.connect((domain, 443))
            cert = s.getpeercert()
        subject = dict(x[0] for x in cert['subject'])
        issuer = dict(x[0] for x in cert['issuer'])
        san = cert.get('subjectAltName', [])
        san_list = [x[1] for x in san if x[0] == 'DNS']
        expiry = datetime.datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
        now = datetime.datetime.utcnow()
        days_left = (expiry - now).days
        return (f"SSL Certificate for {domain}:\n"
                f"  Subject CN: {subject.get('commonName', 'N/A')}\n"
                f"  Issuer CN: {issuer.get('commonName', 'N/A')}\n"
                f"  Expires: {expiry} ({days_left} days left)\n"
                f"  SANs: {', '.join(san_list) if san_list else 'None'}")
    except Exception as e:
        return f"[ssl_cert_info error] {e}"


@register_tool(
    "asn_lookup",
    "Get ASN (Autonomous System) information for an IP address using ipinfo.io.",
    {"ip": "string — IPv4 address"},
)
def asn_lookup(ip: str) -> str:
    if not REQUESTS_OK:
        return "[asn_lookup] Install requests: pip install requests"
    try:
        data = _api_get(f"https://ipinfo.io/{ip}/json")
        if not data:
            return "ASN lookup failed."
        asn = data.get('org', 'N/A')
        return f"IP: {ip}\nASN/ISP: {asn}\nCity: {data.get('city', 'N/A')}\nCountry: {data.get('country', 'N/A')}"
    except Exception as e:
        return f"[asn_lookup error] {e}"


@register_tool(
    "cve_search",
    "Search for CVEs by keyword (e.g. 'apache', 'nginx') using NVD API.",
    {"keyword": "string — software name or CVE ID (e.g. 'log4j' or 'CVE-2021-44228')"},
)
def cve_search(keyword: str) -> str:
    if not REQUESTS_OK:
        return "[cve_search] Install requests: pip install requests"
    try:
        # Simple NVD API query
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={keyword}&resultsPerPage=5"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return f"NVD API error: {r.status_code}"
        data = r.json()
        vulns = data.get('vulnerabilities', [])
        if not vulns:
            return f"No CVEs found for '{keyword}'."
        lines = [f"Top CVEs for '{keyword}':"]
        for v in vulns:
            cve = v['cve']
            desc = cve['descriptions'][0]['value'][:100]
            lines.append(f"  {cve['id']}: {desc}...")
        return "\n".join(lines)
    except Exception as e:
        return f"[cve_search error] {e}"


@register_tool(
    "url_scan",
    "Submit a URL to urlscan.io and return the scan report (public, no API key).",
    {"url": "string — full URL to scan (e.g. https://example.com)"},
)
def url_scan(url: str) -> str:
    if not REQUESTS_OK:
        return "[url_scan] Install requests: pip install requests"
    try:
        # Submit scan
        submit = requests.post('https://urlscan.io/api/v1/scan/', json={'url': url}, timeout=10)
        if submit.status_code != 200:
            return f"Submission failed: {submit.status_code}"
        result = submit.json()
        scan_uuid = result.get('uuid')
        if not scan_uuid:
            return "No UUID returned."
        # Wait and retrieve
        import time
        for _ in range(12):
            time.sleep(2)
            resp = requests.get(f'https://urlscan.io/api/v1/result/{scan_uuid}', timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                verdicts = data.get('verdicts', {})
                malicious = verdicts.get('overall', {}).get('malicious', False)
                stats = data.get('stats', {})
                return (f"URL Scan for {url}:\n"
                        f"  Malicious verdict: {malicious}\n"
                        f"  Total requests: {stats.get('total', 0)}\n"
                        f"  Secure requests: {stats.get('secure', 0)}\n"
                        f"  Report: https://urlscan.io/result/{scan_uuid}")
        return "Scan timed out, check later at https://urlscan.io/result/" + scan_uuid
    except Exception as e:
        return f"[url_scan error] {e}"


@register_tool(
    "email_breach_check",
    "Check if an email appears in known breaches (using 'Have I Been Pwned' API - requires API key).",
    {"email": "string — email address", "api_key": "string — HIBP API key (optional)"},
)
def email_breach_check(email: str, api_key: str = "") -> str:
    if not REQUESTS_OK:
        return "[email_breach_check] Install requests"
    if not api_key:
        return ("To check breaches, get a free API key from https://haveibeenpwned.com/API/Key\n"
                "Then call: email_breach_check(email='your@email.com', api_key='YOUR_KEY')")
    try:
        headers = {'hibp-api-key': api_key, 'User-Agent': 'VINCE-Recon'}
        r = requests.get(f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}', headers=headers, timeout=10)
        if r.status_code == 200:
            breaches = r.json()
            names = [b['Name'] for b in breaches]
            return f"Email {email} found in {len(breaches)} breaches: {', '.join(names)}"
        elif r.status_code == 404:
            return f"Email {email} not found in any known breaches."
        else:
            return f"HIBP error: {r.status_code}"
    except Exception as e:
        return f"[email_breach_check error] {e}"


@register_tool(
    "shodan_host", 
    "Query Shodan for host information (requires API key).",
    {"ip": "string — IPv4 address", "api_key": "string — Shodan API key"},
)
def shodan_host(ip: str, api_key: str) -> str:
    if not REQUESTS_OK:
        return "[shodan_host] Install requests"
    if not api_key:
        return "Shodan API key required. Get one at https://account.shodan.io/"
    try:
        url = f"https://api.shodan.io/shodan/host/{ip}?key={api_key}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            ports = data.get('ports', [])
            vulns = data.get('vulns', {})
            return (f"Shodan results for {ip}:\n"
                    f"  Open ports: {', '.join(map(str, ports[:10]))}\n"
                    f"  Vulnerabilities: {', '.join(vulns.keys()) if vulns else 'None'}\n"
                    f"  ISP: {data.get('isp', 'N/A')}")
        return f"Shodan error: {r.status_code}"
    except Exception as e:
        return f"[shodan_host error] {e}"