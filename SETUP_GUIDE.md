# 🌞 Vibe Prospector — Setup Guide

A lead generation tool for your solar company. Each run lets you pick any business type and any city.

---

## STEP 1 — Install Python (if you don't have it)

Download from https://python.org (version 3.10 or higher).

---

## STEP 2 — Install dependencies

Open a terminal (Command Prompt on Windows, Terminal on Mac), go to the folder where you saved the files, and run:

```
pip install -r requirements.txt
```

---

## STEP 3 — Get a Google Maps API Key (FREE tier is enough)

1. Go to https://console.cloud.google.com/
2. Create a new project (e.g. "Vibe Prospector")
3. Go to **APIs & Services → Enable APIs**
4. Enable **"Places API"**
5. Go to **APIs & Services → Credentials → Create Credentials → API Key**
6. Copy your API key

> **Cost:** Google gives $200/month free credit. Each lead search costs ~$0.032. So you can do ~6,000 results per month for free.

---

## STEP 4 — Set your API Key (two options)

**Option A — Environment variable (recommended):**
```bash
# Mac/Linux
export GOOGLE_MAPS_API_KEY="your_key_here"

# Windows Command Prompt
set GOOGLE_MAPS_API_KEY=your_key_here
```

**Option B — Just paste it when the script asks you.**

---

## STEP 5 — Run the prospector

```bash
python lead_prospector.py
```

The script will ask you:

| Prompt | Example |
|--------|---------|
| Business type | `bakeries` |
| Location | `Miami FL USA` |
| Max results | `20` |
| Google Sheet ID | *(see below or leave blank)* |

---

## STEP 6 (Optional) — Connect Google Sheets

To auto-write leads directly into a Google Sheet:

### 6a. Create a Service Account
1. In Google Cloud Console → **IAM & Admin → Service Accounts**
2. Click **Create Service Account**, give it a name
3. Click on the service account → **Keys → Add Key → JSON**
4. Download the JSON file, rename it `service_account.json`, put it in the same folder as the script

### 6b. Share your Google Sheet with the service account
1. Open your Google Sheet
2. Click **Share**
3. Add the service account email (it looks like `xxx@your-project.iam.gserviceaccount.com`) with **Editor** access

### 6c. Get your Sheet ID
The Sheet ID is in the URL:
`https://docs.google.com/spreadsheets/d/`**THIS_PART_IS_THE_ID**`/edit`

Enter that ID when the script asks.

---

## How it works

```
Your input  →  Google Maps Places API  →  Business details
                                          (name, phone, address, website)
                         ↓
                  Website scraper  →  Email extraction
                         ↓
               CSV file  +  Google Sheets (optional)
```

Each search creates a new **timestamped CSV file** (e.g. `leads_bakeries_Miami_20260415_1430.csv`).

If using Google Sheets, each search creates a **new tab** inside the same sheet.

---

## Example searches

| Business Type | Location |
|---------------|----------|
| `bakeries` | `Miami FL USA` |
| `private schools` | `Austin Texas USA` |
| `auto repair shops` | `São Paulo Brazil` |
| `hotels` | `Cancun Mexico` |
| `car dealerships` | `Phoenix Arizona USA` |
| `commercial buildings` | `Dallas TX` |
| `warehouses` | `Los Angeles CA` |

---

## Troubleshooting

**"REQUEST_DENIED"** → Your API key is wrong or Places API isn't enabled.

**No emails found** → Many businesses don't list emails publicly. The script checks homepage, /contact, /about pages.

**"gspread not found"** → Run `pip install gspread google-auth` again.

**Rate limit errors** → Reduce max results or add a pause between runs.

---

## Output columns

| Column | Description |
|--------|-------------|
| name | Business name |
| phone | Phone number |
| address | Full street address |
| website | Website URL |
| email | Best email found (scraped from website) |
| scraped_at | Date/time of the run |
| query | The exact search used |
