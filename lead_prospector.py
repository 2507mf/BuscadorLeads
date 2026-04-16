#!/usr/bin/env python3
"""
=============================================================
  VIBE PROSPECTOR  —  Google Maps Lead Generator
  Solar company edition: run any time, any target, any city.
=============================================================
Usage:
    python lead_prospector.py

You will be prompted for:
  - Business type  (e.g. bakeries, schools, auto repair shops)
  - Location       (e.g. Miami FL USA, São Paulo Brazil)
  - Max results    (default 20)
  - Google Sheet ID (optional — leave blank to skip)

Requirements:  pip install -r requirements.txt
API key:       set GOOGLE_MAPS_API_KEY in your environment,
               or paste it when prompted.
"""

import os
import re
import sys
import csv
import time
import json
import requests
from datetime import datetime
from urllib.parse import urljoin, urlparse

# ── API Key do Google Maps ──────────────────────────────────
# ⚠️  Nunca suba esta chave para repositórios públicos (git, GitHub, etc.)
DEFAULT_MAPS_API_KEY = "AIzaSyAsUm3zE7M33f_9D_Zqif51OpoY4QzVPqE"

# ── optional Google Sheets support ─────────────────────────
try:
    import gspread
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials as OAuthCredentials
    from google.auth.transport.requests import Request as GoogleRequest
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False

# Caminho padrão para o client_secret OAuth2 (já existente na pasta)
DEFAULT_CLIENT_SECRET = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "client_secret_264415761526-20sghffgmoi6gehsimmfonjim909klvl.apps.googleusercontent.com.json"
)
OAUTH_TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")

# ── colour helpers (graceful fallback on Windows) ───────────
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    G = Fore.GREEN; Y = Fore.YELLOW; R = Fore.RED
    C = Fore.CYAN;  B = Fore.BLUE;   W = Style.RESET_ALL
except ImportError:
    G = Y = R = C = B = W = ""

BANNER = f"""
{C}╔══════════════════════════════════════════════╗
║        🌞  VIBE PROSPECTOR  v1.0  🌞         ║
║   Google Maps Lead Extractor for Solar Co.   ║
╚══════════════════════════════════════════════╝{W}
"""

# ── email scraper ───────────────────────────────────────────
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)
SKIP_DOMAINS = {"sentry.io", "example.com", "yourdomain", "email.com",
                "domain.com", "wixpress.com", "squarespace.com"}

def extract_emails_from_html(html: str) -> list[str]:
    found = EMAIL_RE.findall(html)
    clean = set()
    for e in found:
        e = e.lower().strip(".")
        domain = e.split("@")[1]
        if any(skip in domain for skip in SKIP_DOMAINS):
            continue
        if re.match(r".*\.(png|jpg|gif|svg|css|js)$", e):
            continue
        clean.add(e)
    return sorted(clean)

def scrape_email(website_url: str, timeout: int = 8) -> str:
    """Try homepage then /contact page for email addresses."""
    if not website_url:
        return ""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LeadBot/1.0)"}
    urls_to_try = [website_url]
    # also try /contact and /about
    base = f"{urlparse(website_url).scheme}://{urlparse(website_url).netloc}"
    for path in ["/contact", "/contact-us", "/about", "/contacto"]:
        urls_to_try.append(base + path)

    for url in urls_to_try:
        try:
            r = requests.get(url, headers=headers, timeout=timeout,
                             allow_redirects=True)
            if r.status_code == 200:
                emails = extract_emails_from_html(r.text)
                if emails:
                    return emails[0]          # return first real email
        except Exception:
            pass
    return ""

# ── Google Maps Places API (New) ────────────────────────────
PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAIL_URL = "https://places.googleapis.com/v1/places/{place_id}"
FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.nationalPhoneNumber,places.internationalPhoneNumber,"
    "places.websiteUri,places.googleMapsUri"
)
DETAIL_FIELD_MASK = (
    "id,displayName,formattedAddress,"
    "nationalPhoneNumber,internationalPhoneNumber,"
    "websiteUri,googleMapsUri"
)

def search_places(query: str, api_key: str, max_results: int = 20) -> list[dict]:
    """Paginate through Places Text Search (New API) results."""
    results = []
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body = {"textQuery": query, "pageSize": min(max_results, 20)}
    while len(results) < max_results:
        resp = requests.post(PLACES_SEARCH_URL, json=body, headers=headers, timeout=15)
        if resp.status_code != 200:
            err = resp.json()
            print(f"{R}[Maps API Error] {resp.status_code} — {err.get('error', {}).get('message', resp.text)}{W}")
            break
        data = resp.json()
        batch = data.get("places", [])
        results.extend(batch)
        token = data.get("nextPageToken")
        if not token or len(results) >= max_results or not batch:
            break
        time.sleep(2)
        body = {"textQuery": query, "pageSize": min(max_results - len(results), 20), "pageToken": token}
    return results[:max_results]

def get_place_details(place_id: str, api_key: str) -> dict:
    """Retorna detalhes de um lugar usando a Places API (New)."""
    url = PLACES_DETAIL_URL.format(place_id=place_id)
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": DETAIL_FIELD_MASK,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"{Y}[Detail Error] {e}{W}")
    return {}

# ── Google Sheets writer ────────────────────────────────────
SHEET_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def _get_oauth_creds(client_secret_path: str) -> "OAuthCredentials":
    """Obtém ou renova credenciais OAuth2 para o Google Sheets."""
    creds = None
    if os.path.exists(OAUTH_TOKEN_FILE):
        creds = OAuthCredentials.from_authorized_user_file(OAUTH_TOKEN_FILE, SHEET_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SHEET_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(OAUTH_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds

def write_to_sheet(rows: list[dict], sheet_id: str, client_secret_path: str, tab_name: str):
    """Append rows to a Google Sheet tab (creates tab if missing)."""
    if not SHEETS_AVAILABLE:
        print(f"{Y}[Sheets] gspread/google-auth-oauthlib não instalado — pulando export.{W}")
        return
    try:
        creds = _get_oauth_creds(client_secret_path)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        try:
            ws = sh.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=tab_name, rows="1000", cols="10")
        # Write header if sheet is empty
        if ws.row_count == 0 or not ws.get_all_values():
            ws.append_row(["Name", "Phone", "Address", "Website", "Email",
                           "Scraped At", "Search Query"])
        for row in rows:
            ws.append_row([
                row.get("name", ""),
                row.get("phone", ""),
                row.get("address", ""),
                row.get("website", ""),
                row.get("email", ""),
                row.get("scraped_at", ""),
                row.get("query", ""),
            ])
        print(f"{G}[Sheets] ✓ {len(rows)} linhas escritas na aba '{tab_name}'{W}")
    except Exception as e:
        print(f"{R}[Sheets Error] {e}{W}")

# ── CSV writer ──────────────────────────────────────────────
def save_csv(rows: list[dict], filepath: str):
    fieldnames = ["name", "phone", "address", "website", "email",
                  "scraped_at", "query"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{G}[CSV] ✓ Saved {len(rows)} leads → {filepath}{W}")

# ── main interactive flow ───────────────────────────────────
def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{C}{label}{suffix}: {W}").strip()
    return val if val else default

def main():
    print(BANNER)

    # ── gather API key ──────────────────────────────────────
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key or api_key == DEFAULT_MAPS_API_KEY:
        api_key = DEFAULT_MAPS_API_KEY
    # Se ainda for o placeholder, pede ao usuário
    if "PLACEHOLDER" in api_key or not api_key:
        api_key = prompt("Google Maps API Key (ou defina GOOGLE_MAPS_API_KEY no ambiente)")
    if not api_key:
        print(f"{R}Nenhuma API key fornecida. Encerrando.{W}")
        sys.exit(1)

    print()
    print(f"{B}─────────────────────────────────────────{W}")
    print(f"{Y}  SEARCH CONFIGURATION{W}")
    print(f"{B}─────────────────────────────────────────{W}")

    biz_type  = prompt("Business type  (e.g. bakeries, schools, auto dealers)")
    location  = prompt("Location       (e.g. Miami FL USA, São Paulo Brazil)")
    max_r     = int(prompt("Max results    ", default="20"))
    print()

    query = f"{biz_type} in {location}"
    print(f"{G}▶ Searching: \"{query}\"{W}\n")

    # ── Google Sheets config (optional) ────────────────────
    use_sheets = False
    sheet_id   = ""
    client_secret_path = DEFAULT_CLIENT_SECRET
    if SHEETS_AVAILABLE:
        sheet_id = prompt("Google Sheet ID (deixe em branco para pular o export)", "")
        if sheet_id:
            csp = prompt("Caminho para o client_secret JSON",
                         default=DEFAULT_CLIENT_SECRET)
            client_secret_path = csp if csp else DEFAULT_CLIENT_SECRET
            use_sheets = True
    else:
        print(f"{Y}[Dica] Instale gspread + google-auth-oauthlib para exportar para o Google Sheets.{W}\n")

    # ── search ─────────────────────────────────────────────
    print(f"{C}[1/3] Fetching places from Google Maps...{W}")
    places = search_places(query, api_key, max_results=max_r)
    print(f"      Found {len(places)} places\n")

    if not places:
        print(f"{R}No results. Try a different search term or location.{W}")
        sys.exit(0)

    # ── enrich ─────────────────────────────────────────────
    print(f"{C}[2/3] Fetching details + scraping emails...{W}")
    rows = []
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")

    for i, place in enumerate(places, 1):
        place_id = place.get("id", "")
        details  = get_place_details(place_id, api_key) if place_id else place

        name    = (details.get("displayName") or {}).get("text") or \
                  (place.get("displayName") or {}).get("text", "")
        phone   = details.get("nationalPhoneNumber") or \
                  details.get("internationalPhoneNumber", "")
        address = details.get("formattedAddress") or place.get("formattedAddress", "")
        website = details.get("websiteUri", "") or place.get("websiteUri", "")

        print(f"  [{i:02d}/{len(places):02d}] {name[:45]:<45}", end=" ", flush=True)

        email = ""
        if website:
            email = scrape_email(website)
            print(f"{'✓ ' + email if email else '— no email'}", flush=True)
        else:
            print("— no website", flush=True)

        rows.append({
            "name":       name,
            "phone":      phone,
            "address":    address,
            "website":    website,
            "email":      email,
            "scraped_at": now,
            "query":      query,
        })
        time.sleep(0.3)     # be polite to websites

    # ── save ───────────────────────────────────────────────
    print(f"\n{C}[3/3] Saving results...{W}")
    safe_query = re.sub(r"[^\w\- ]", "", query).replace(" ", "_")[:50]
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = f"leads_{safe_query}_{ts}.csv"
    save_csv(rows, csv_path)

    if use_sheets and sheet_id:
        tab_name = f"{biz_type[:20]} – {location[:20]}"
        write_to_sheet(rows, sheet_id, client_secret_path, tab_name)

    # ── summary ────────────────────────────────────────────
    with_email   = sum(1 for r in rows if r["email"])
    with_phone   = sum(1 for r in rows if r["phone"])
    with_website = sum(1 for r in rows if r["website"])

    print(f"""
{G}╔══════════════════════════════════╗
║         PROSPECTING DONE!        ║
╠══════════════════════════════════╣
║  Total leads   : {len(rows):<16}║
║  With phone    : {with_phone:<16}║
║  With website  : {with_website:<16}║
║  With email    : {with_email:<16}║
╚══════════════════════════════════╝{W}
    """)
    print(f"  📁 CSV file : {G}{csv_path}{W}")
    if use_sheets:
        print(f"  📊 Google Sheet updated ✓")
    print()

if __name__ == "__main__":
    main()
