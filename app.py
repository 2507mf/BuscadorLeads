"""
🌞 Vibe Prospector — Interface Web (Streamlit)
Gerador de leads pelo Google Maps — simples, rápido, sem configuração.
"""

import re
import time
import io
import json
import requests
import streamlit as st
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse

# ── optional Google Sheets ──────────────────────────────────
try:
    import gspread
    from google.oauth2.service_account import Credentials
    SHEETS_OK = True
except ImportError:
    SHEETS_OK = False

# ═══════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════
DEFAULT_API_KEY = "AIzaSyAsUm3zE7M33f_9D_Zqif51OpoY4QzVPqE"

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAIL_URL = "https://places.googleapis.com/v1/places/{place_id}"
FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.nationalPhoneNumber,places.internationalPhoneNumber,"
    "places.websiteUri,places.googleMapsUri"
)
DETAIL_FIELD_MASK = (
    "id,displayName,formattedAddress,"
    "nationalPhoneNumber,internationalPhoneNumber,websiteUri"
)
SHEET_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
SKIP_DOMAINS = {
    "sentry.io", "example.com", "yourdomain", "wixpress.com",
    "squarespace.com", "domain.com", "email.com",
}

# ═══════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Vibe Prospector 🌞",
    page_icon="🌞",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
[data-testid="collapsedControl"] { display: none; }

.hero {
    background: linear-gradient(135deg, #f97316 0%, #ef4444 100%);
    border-radius: 20px;
    padding: 2.5rem 2rem 2rem;
    text-align: center;
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 8px 32px rgba(239,68,68,0.25);
}
.hero h1 { font-size: 2.6rem; margin: 0; font-weight: 800; letter-spacing: -1px; }
.hero p  { font-size: 1.1rem; margin: 0.5rem 0 0; opacity: 0.9; }

div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #f97316, #ef4444) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.85rem 2rem !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    width: 100% !important;
    box-shadow: 0 4px 15px rgba(239,68,68,0.3) !important;
    margin-top: 0.5rem !important;
}
div[data-testid="stButton"] > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(239,68,68,0.45) !important;
}
div[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #10b981, #059669) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.85rem 2rem !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    width: 100% !important;
    box-shadow: 0 4px 15px rgba(16,185,129,0.3) !important;
}

.metric-row { display: flex; gap: 1rem; margin: 1.5rem 0; }
.metric-box {
    flex: 1; background: #1e293b;
    border: 1px solid #334155; border-radius: 14px;
    padding: 1.2rem; text-align: center;
}
.metric-box .num { font-size: 2rem; font-weight: 800; color: #f97316; }
.metric-box .lbl { font-size: 0.8rem; color: #94a3b8; margin-top: 2px; }

.tip-box {
    background: #0f172a; border-left: 4px solid #f97316;
    border-radius: 8px; padding: 0.9rem 1.2rem;
    margin: 1rem 0; font-size: 0.9rem; color: #cbd5e1;
}

.step {
    display: flex; align-items: flex-start; gap: 1rem;
    background: #ffffff06; border-radius: 12px;
    padding: 1rem 1.2rem; margin-bottom: 0.7rem;
    border: 1px solid #ffffff10;
}
.step-num {
    background: linear-gradient(135deg, #f97316, #ef4444);
    color: white; border-radius: 50%;
    width: 32px; height: 32px; min-width: 32px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 0.95rem;
}
.step-text { padding-top: 4px; }
.step-text b { display: block; margin-bottom: 2px; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  FUNÇÕES
# ═══════════════════════════════════════════════════════════
def extract_emails(html):
    found = EMAIL_RE.findall(html)
    clean = set()
    for e in found:
        e = e.lower().strip(".")
        domain = e.split("@")[1]
        if any(s in domain for s in SKIP_DOMAINS):
            continue
        if re.match(r".*\.(png|jpg|gif|svg|css|js)$", e):
            continue
        clean.add(e)
    return sorted(clean)

def scrape_email(url):
    if not url:
        return ""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LeadBot/1.0)"}
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    for path in ["", "/contact", "/contact-us", "/about", "/contacto"]:
        try:
            r = requests.get(base + path, headers=headers, timeout=6, allow_redirects=True)
            if r.status_code == 200:
                emails = extract_emails(r.text)
                if emails:
                    return emails[0]
        except Exception:
            pass
    return ""

def search_places(query, api_key, max_results):
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
            st.error(f"❌ Erro na API: {err.get('error', {}).get('message', resp.text)}")
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

def get_details(place_id, api_key):
    url = PLACES_DETAIL_URL.format(place_id=place_id)
    headers = {"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": DETAIL_FIELD_MASK}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}

def write_to_sheets(rows, sheet_id, creds_dict, tab):
    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=SHEET_SCOPES)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        try:
            ws = sh.worksheet(tab)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=tab, rows="1000", cols="10")
        if not ws.get_all_values():
            ws.append_row(["Nome", "Telefone", "Endereço", "Website", "Email", "Data/Hora", "Busca"])
        for r in rows:
            ws.append_row([r["name"], r["phone"], r["address"],
                           r["website"], r["email"], r["scraped_at"], r["query"]])
        return True, len(rows)
    except Exception as e:
        return False, str(e)


# ═══════════════════════════════════════════════════════════
#  HERO
# ═══════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
  <h1>🌞 Vibe Prospector</h1>
  <p>Encontre clientes em qualquer cidade do mundo — em segundos.</p>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  FORMULÁRIO
# ═══════════════════════════════════════════════════════════
st.markdown("### 🔍 O que você quer prospectar?")

st.markdown("""
<div class="tip-box">
💡 <b>Dica:</b> Seja específico. Ex: <i>"empresas de energia solar"</i>,
<i>"clínicas odontológicas"</i>, <i>"construtoras"</i>, <i>"hotéis 4 estrelas"</i>
</div>
""", unsafe_allow_html=True)

# Exemplos rápidos
st.markdown("**⚡ Exemplos rápidos:**")
ex_cols = st.columns(4)
examples = [
    ("☀️ Solar SP",    "empresas de energia solar", "São Paulo, Brasil"),
    ("🏥 Clínicas RJ", "clínicas médicas",          "Rio de Janeiro, Brasil"),
    ("🏨 Hotéis Miami","hotéis",                    "Miami FL USA"),
    ("🏗️ Construtoras","construtoras",              "Belo Horizonte, Brasil"),
]
for col, (label, biz, loc) in zip(ex_cols, examples):
    with col:
        if st.button(label, use_container_width=True, key=f"ex_{label}"):
            st.session_state["_biz"] = biz
            st.session_state["_loc"] = loc
            st.rerun()

col1, col2 = st.columns(2)
with col1:
    biz_type = st.text_input(
        "🏢 Tipo de negócio",
        value=st.session_state.get("_biz", ""),
        placeholder="ex: empresas de energia solar",
    )
with col2:
    location = st.text_input(
        "📍 Cidade / Estado / País",
        value=st.session_state.get("_loc", ""),
        placeholder="ex: São Paulo, Brasil",
    )

max_results = st.select_slider(
    "📊 Quantos leads quer buscar?",
    options=[10, 20, 30, 40, 60],
    value=20,
)

# Sheets (colapsado)
with st.expander("📊 Exportar para Google Sheets (opcional)"):
    st.markdown("""
    <div class="tip-box">
    Para usar o Sheets você precisa de um <b>Service Account JSON</b> do Google Cloud.
    <a href="https://console.cloud.google.com/iam-admin/serviceaccounts"
    target="_blank" style="color:#f97316">Criar credencial aqui →</a>
    </div>
    """, unsafe_allow_html=True)
    sheet_id   = st.text_input("ID da Planilha Google", placeholder="Cole o ID da URL da planilha")
    creds_file = st.file_uploader("Arquivo service_account.json", type=["json"])
    creds_json = json.load(creds_file) if creds_file else None
    use_sheets = bool(sheet_id and creds_json)
    if creds_json:
        st.success("✅ Credenciais carregadas!")

run_btn = st.button("🚀  Buscar Leads Agora", use_container_width=True)


# ═══════════════════════════════════════════════════════════
#  EXECUÇÃO
# ═══════════════════════════════════════════════════════════
if run_btn:
    if not biz_type or not location:
        st.error("⚠️ Preencha o **tipo de negócio** e a **cidade** antes de buscar.")
        st.stop()

    query = f"{biz_type} em {location}"

    st.markdown(f"""
    <div style="background:#0f172a;border:1px solid #334155;border-radius:12px;
    padding:1rem 1.5rem;margin:1rem 0;">
    🔎 Buscando: <b style="color:#f97316">{query}</b>
    </div>
    """, unsafe_allow_html=True)

    with st.status("📡 Buscando no Google Maps...", expanded=True) as status:
        st.write("Consultando Places API...")
        places = search_places(query, DEFAULT_API_KEY, max_results)
        if not places:
            status.update(label="❌ Nenhum resultado encontrado.", state="error")
            st.warning("Tente mudar o tipo de negócio ou a cidade.")
            st.stop()
        st.write(f"✅ {len(places)} empresas encontradas! Coletando detalhes e emails...")

        progress = st.progress(0, text="Iniciando...")
        rows = []
        now  = datetime.now().strftime("%d/%m/%Y %H:%M")

        for i, place in enumerate(places):
            place_id = place.get("id", "")
            nm = (place.get("displayName") or {}).get("text", "")
            progress.progress((i + 1) / len(places), text=f"[{i+1}/{len(places)}] {nm[:45]}")
            details  = get_details(place_id, DEFAULT_API_KEY) if place_id else place

            name    = (details.get("displayName") or {}).get("text") or nm
            phone   = details.get("nationalPhoneNumber") or details.get("internationalPhoneNumber", "")
            address = details.get("formattedAddress") or place.get("formattedAddress", "")
            website = details.get("websiteUri", "") or place.get("websiteUri", "")
            email   = scrape_email(website) if website else ""
            maps_url = place.get("googleMapsUri", "")

            rows.append({"name": name, "phone": phone, "address": address,
                         "website": website, "email": email,
                         "maps_url": maps_url, "scraped_at": now, "query": query})
            time.sleep(0.2)

        progress.empty()
        status.update(label=f"✅ Pronto! {len(rows)} leads coletados.", state="complete")

    # Métricas
    total   = len(rows)
    c_phone = sum(1 for r in rows if r["phone"])
    c_site  = sum(1 for r in rows if r["website"])
    c_email = sum(1 for r in rows if r["email"])

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-box"><div class="num">{total}</div><div class="lbl">🏢 Leads</div></div>
      <div class="metric-box"><div class="num">{c_phone}</div><div class="lbl">📞 Telefones</div></div>
      <div class="metric-box"><div class="num">{c_site}</div><div class="lbl">🌐 Websites</div></div>
      <div class="metric-box"><div class="num">{c_email}</div><div class="lbl">📧 Emails</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Tabela
    st.markdown("### 📋 Seus leads")
    df_display = pd.DataFrame(rows)[["name", "phone", "address", "website", "email"]].copy()
    df_display.columns = ["🏢 Nome", "📞 Telefone", "📍 Endereço", "🌐 Website", "📧 Email"]
    df_display.index = df_display.index + 1
    st.dataframe(df_display, use_container_width=True, height=min(420, 56 + len(df_display) * 38))

    # Download
    st.markdown("### ⬇️ Baixar seus leads")
    df_csv = pd.DataFrame(rows)[["name","phone","address","website","email","maps_url","scraped_at"]]
    df_csv.columns = ["Nome","Telefone","Endereço","Website","Email","Link Google Maps","Coletado em"]
    safe = re.sub(r"[^\w\-]", "_", f"{biz_type}_{location}")[:40]
    ts   = datetime.now().strftime("%Y%m%d_%H%M")

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "⬇️ Baixar CSV",
            data=df_csv.to_csv(index=False).encode("utf-8"),
            file_name=f"leads_{safe}_{ts}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with dl2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_csv.to_excel(writer, index=False, sheet_name="Leads")
        st.download_button(
            "⬇️ Baixar Excel (.xlsx)",
            data=buf.getvalue(),
            file_name=f"leads_{safe}_{ts}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # Sheets
    if use_sheets:
        with st.spinner("📊 Exportando para Google Sheets..."):
            tab_name = f"{biz_type[:18]} – {location[:15]}"
            ok, result = write_to_sheets(rows, sheet_id, creds_json, tab_name)
        if ok:
            st.success(f"✅ {result} leads salvos na planilha (aba: *{tab_name}*)")
        else:
            st.error(f"Erro no Google Sheets: {result}")

    st.balloons()


# ═══════════════════════════════════════════════════════════
#  TELA INICIAL
# ═══════════════════════════════════════════════════════════
else:
    st.markdown("### 👆 Como funciona")
    steps = [
        ("1", "Escolha o tipo de negócio",
         "Ex: <i>empresas de energia solar, construtoras, clínicas odontológicas...</i>"),
        ("2", "Informe a cidade",
         "Ex: <i>São Paulo Brasil, Miami FL USA, Buenos Aires Argentina...</i>"),
        ("3", "Clique em Buscar Leads",
         "O sistema consulta o Google Maps e coleta telefone, site e email automaticamente."),
        ("4", "Baixe o arquivo",
         "Faça download em CSV ou Excel — pronto para usar no seu CRM ou WhatsApp."),
    ]
    for num, title, desc in steps:
        st.markdown(f"""
        <div class="step">
          <div class="step-num">{num}</div>
          <div class="step-text">
            <b>{title}</b>
            <span style="color:#94a3b8;font-size:0.88rem">{desc}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="tip-box" style="margin-top:1.5rem">
    ✅ <b>Sem cadastro</b> · Sem limite de buscas · Resultados salvos só no seu computador.
    </div>
    """, unsafe_allow_html=True)
