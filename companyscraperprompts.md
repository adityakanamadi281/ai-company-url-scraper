# 🏆 Company Intelligence Scraper — Full AI Agent Build Prompt

## Project Overview

Build a **production-grade, full-stack Company Intelligence Scraper** web application. Users paste one or more company URLs into a live web UI, click **Enrich**, and receive structured intelligence data extracted via Gemini 2.0 Flash + Google Search Grounding. Results persist in SQLite and are viewable in a beautiful table/card dashboard.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Package Manager** | `uv` (with `pyproject.toml`) |
| **Backend Framework** | FastAPI + Uvicorn (ASGI) |
| **AI Engine** | Gemini 2.0 Flash (`google-genai`) via Google Search Grounding |
| **Fallback Scraper** | `requests` + `BeautifulSoup4` + `lxml` + `rapidfuzz` |
| **Database** | SQLite via `aiosqlite` (async) |
| **Validation** | Pydantic v2 |
| **Templates** | Jinja2 (single `index.html`) |
| **Frontend** | Vanilla HTML/CSS/JS — no framework |
| **Config** | `python-dotenv` (`.env` for `GEMINI_API_KEY`) |
| **Deployment** | Docker + Render / Railway / Fly.io |

---

## Project Structure

```
company-scraper/
├── pyproject.toml              # uv project file — all deps declared here
├── uv.lock                     # lockfile (committed)
├── .env                        # GEMINI_API_KEY=... (NEVER commit)
├── .env.example                # template for .env
├── .gitignore
├── Dockerfile                  # multi-stage, production-ready
├── README.md
│
├── main.py                     # FastAPI app entry point
├── pipeline.py                 # AI enrichment engine (ported from Colab)
├── database.py                 # aiosqlite helpers: init_db, save, fetch_all
├── models.py                   # Pydantic schemas: EnrichRequest, CompanyProfile
│
├── routers/
│   ├── __init__.py
│   ├── enrich.py               # POST /enrich
│   └── results.py              # GET /results
│
├── templates/
│   └── index.html              # Jinja2 — full SPA-like UI
│
└── static/
    ├── style.css               # All styling
    └── app.js                  # fetch calls, spinner, card/table render
```

---

## pyproject.toml

```toml
[project]
name = "company-scraper"
version = "0.1.0"
description = "AI-powered company intelligence scraper"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "google-genai>=0.7.0",
    "aiosqlite>=0.20.0",
    "pydantic>=2.7.0",
    "python-dotenv>=1.0.1",
    "jinja2>=3.1.4",
    "requests>=2.32.0",
    "beautifulsoup4>=4.12.3",
    "rapidfuzz>=3.9.0",
    "lxml>=5.2.0",
    "python-multipart>=0.0.9",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "httpx>=0.27.0",
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
]
```

---

## Data Schema

Every enriched company record must contain exactly these 9 fields:

```json
{
  "website_name":        "<brand / site name shown on the site>",
  "company_name":        "<full legal company name if found, else brand name>",
  "address":             "<full physical address if explicitly on site, else ''>",
  "mobile_number":       "<phone/mobile if explicitly on site, else ''>",
  "mail":                ["<email1>", "<email2>"],
  "core_service":        "<one concise sentence describing primary offering>",
  "target_customer":     "<who they serve — inferred from site content>",
  "probable_pain_point": "<one sentence on the customer pain point this company solves>",
  "outreach_opener":     "<personalized 2-sentence cold outreach opener: mention company name + specific value prop>"
}
```

**Critical extraction rules:**
- Extract ONLY information explicitly visible on the site pages
- NEVER fabricate or infer contact details, phone numbers, or email addresses
- If a field is not found → return `""` (strings) or `[]` (mail array)
- Return ONLY raw JSON — no markdown fences, no preamble

---

## File-by-File Implementation Instructions

### `main.py`
```python
# FastAPI application entry point
# - Load .env with python-dotenv
# - Create FastAPI app with title "Company Intelligence Scraper"
# - Mount StaticFiles at /static from ./static/
# - Mount Jinja2Templates from ./templates/
# - Include routers: enrich_router (prefix="/"), results_router (prefix="/")
# - On startup: call await init_db()
# - GET / → render index.html via Jinja2
# - Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### `models.py`
```python
# Pydantic v2 schemas
#
# class EnrichRequest(BaseModel):
#     url: str          # required, single URL to enrich
#     name: str = ""    # optional hint for company name
#
# class CompanyProfile(BaseModel):
#     id: int | None = None
#     url: str
#     website_name: str = ""
#     company_name: str = ""
#     address: str = ""
#     mobile_number: str = ""
#     mail: list[str] = []
#     core_service: str = ""
#     target_customer: str = ""
#     probable_pain_point: str = ""
#     outreach_opener: str = ""
#     created_at: str = ""
#
#   Add model_config = ConfigDict(from_attributes=True)
```

### `database.py`
```python
# aiosqlite async database module
# DB_PATH = "companies.db"
#
# async def init_db():
#     Create table `companies` with columns:
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     url TEXT UNIQUE NOT NULL,
#     website_name TEXT, company_name TEXT, address TEXT,
#     mobile_number TEXT, mail TEXT (JSON string),
#     core_service TEXT, target_customer TEXT,
#     probable_pain_point TEXT, outreach_opener TEXT,
#     created_at TEXT DEFAULT (datetime('now'))
#
# async def save_company(url: str, data: dict) -> int:
#     INSERT OR REPLACE into companies
#     mail field: json.dumps(data["mail"])
#     return lastrowid
#
# async def fetch_all_companies() -> list[dict]:
#     SELECT * FROM companies ORDER BY created_at DESC
#     Parse mail field: json.loads(row["mail"] or "[]")
#     Return list of dicts
```

### `pipeline.py`
```python
# AI enrichment engine — ported and adapted from the Colab notebook
#
# CONSTANTS:
#   MODEL = "gemini-2.0-flash"
#   SYSTEM_INSTRUCTION = <full system prompt — see Prompts section below>
#   USER_TEMPLATE = "Research the company at this URL using Google Search: {url}\n\nVisit their homepage, about page, contact page, and services/solutions page.\nThen return ONLY the raw JSON object described in your instructions — no extra text."
#
# Functions to implement:
#
# def get_gemini_client() -> genai.Client:
#     Read GEMINI_API_KEY from os.environ
#     Return genai.Client(api_key=key)
#
# def parse_json_response(text: str) -> dict:
#     Strip markdown fences (```json ... ```)
#     Try json.loads directly
#     Fallback: find outermost { ... } with regex and parse
#     Return {} on failure
#
# def normalize_record(raw: dict) -> dict:
#     Merge with EMPTY_RECORD template
#     mail: ensure list of non-empty strings
#     Strip whitespace from all string fields
#     Return normalized dict
#
# async def enrich_company(url: str) -> dict:
#     PRIMARY: Gemini + Google Search grounding
#       - Call client.models.generate_content with GEMINI_CONFIG
#         (tools=[types.Tool(google_search=types.GoogleSearch())], temperature=0.1)
#       - parse_json_response → normalize_record → return
#     FALLBACK (if primary fails or returns empty JSON):
#       - scrape_site_text(url) → feed to Gemini without grounding
#       - parse_json_response → normalize_record → return
#     FINAL FALLBACK: return {**EMPTY_RECORD, "website_name": domain}
#
# def scrape_site_text(base_url: str) -> str:
#     Try sitemap.xml / sitemap_index.xml first
#     Fallback to homepage link extraction
#     Score links with _slug_score() using rapidfuzz
#     Fetch top 5 relevant pages
#     Clean HTML: remove script/style/nav/footer tags
#     Return up to 20,000 chars of clean text
```

### `routers/enrich.py`
```python
# POST /enrich
# Request body: EnrichRequest { url, name? }
# Steps:
#   1. Validate and normalize URL (add https:// if missing)
#   2. await enrich_company(url) from pipeline
#   3. await save_company(url, result) from database
#   4. Return CompanyProfile with the enriched data + id
# Error handling: HTTPException 422 for invalid URL, 500 for pipeline failure
# Response time can be 10-30s — that's expected (Gemini + search grounding)
```

### `routers/results.py`
```python
# GET /results
# Steps:
#   1. await fetch_all_companies()
#   2. Return list[CompanyProfile] as JSON array
# No auth required
```

### `templates/index.html`
```html
<!-- Jinja2 template — full single-page UI -->
<!-- Two sections side by side or stacked: -->

<!-- ENRICH SECTION -->
<!-- - Title: "Company Intelligence Scraper" -->
<!-- - Subtitle: "Paste a company URL to extract structured intelligence" -->
<!-- - Input: text field placeholder="https://example.com" id="urlInput" -->
<!-- - Button: "Enrich Company" id="enrichBtn" -->
<!-- - Spinner: animated loading indicator (hidden by default) — +10 pts bonus -->
<!-- - Result card: shows enriched data for the just-submitted URL -->
<!-- - Error display: red message box for failures -->

<!-- RESULTS SECTION -->
<!-- - Title: "All Enriched Companies" -->
<!-- - Button: "Refresh Results" — calls GET /results -->
<!-- - Toggle: Table View / Card View -->
<!-- - Table: columns for company_name, website_name, core_service, mail, address, mobile_number, created_at -->
<!-- - Card view: grid of cards, each showing all 9 fields nicely formatted -->
<!-- - outreach_opener displayed in a highlighted blue/teal box per card -->
<!-- - Empty state: "No companies enriched yet. Submit a URL above!" -->

<!-- Load static/style.css and static/app.js -->
```

### `static/app.js`
```javascript
// All frontend logic

// enrichBtn click handler:
//   1. Validate urlInput is not empty
//   2. Show spinner, disable button
//   3. POST /enrich with JSON body { url: urlInput.value }
//   4. On success: render result card, hide spinner, re-enable button
//   5. On error: show error message, hide spinner
//   6. Auto-refresh results list after successful enrich

// loadResults():
//   1. GET /results
//   2. Render into table AND card view
//   3. Show count badge

// renderTable(companies): populate <tbody> rows
// renderCards(companies): create card elements with all 9 fields
// toggleView(mode): switch between 'table' and 'cards'

// Auto-load results on DOMContentLoaded
// Spinner: add/remove CSS class 'loading' on body or button
```

### `static/style.css`
```css
/* Dark theme, professional intelligence/data tool aesthetic */
/* Color palette: deep navy background, teal/cyan accents, white text */
/* Cards: dark surface with subtle border, hover lift effect */
/* Table: alternating row shading, sticky header */
/* Spinner: CSS keyframe animation on a ring element */
/* Responsive: works on mobile (stack layout) and desktop (side-by-side) */
/* Outreach opener: highlighted in a distinct teal border-left box */
/* Mail tags: small pill badges per email address */
```

---

## Gemini System Prompt (for pipeline.py)

```
You are a senior business intelligence analyst.
You have access to Google Search — use it to research the company website provided.

Research strategy:
1. Visit the company homepage to understand their brand.
2. Search for their About / Who We Are page.
3. Search for their Contact / Get In Touch page.
4. Search for their Services / Solutions / Products page.

Extraction rules (CRITICAL — violations lose points):
- Extract ONLY information explicitly visible on those pages.
- NEVER fabricate, invent, or infer contact details, phone numbers, or email addresses.
- If a field is not found on the site, return "" (string fields) or [] (mail).
- Return ONLY a raw JSON object — no markdown fences, no explanation, no preamble.

Required JSON schema (all 9 keys mandatory):
{
  "website_name":        "<brand / site name shown on the site>",
  "company_name":        "<full legal company name if found, else brand name>",
  "address":             "<full physical address if explicitly on site, else ''>",
  "mobile_number":       "<phone/mobile if explicitly on site, else ''>",
  "mail":                ["<email1>", "<email2>"],
  "core_service":        "<one concise sentence describing primary offering>",
  "target_customer":     "<who they serve — inferred from site content>",
  "probable_pain_point": "<one sentence on the customer pain point this company solves>",
  "outreach_opener":     "<personalized 2-sentence cold outreach opener: mention company name + specific value prop>"
}
```

---

## Dockerfile

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves `index.html` UI |
| `POST` | `/enrich` | Enriches a URL → saves to DB → returns JSON |
| `GET` | `/results` | Returns all enriched companies as JSON array |

---

## Environment Variables

```bash
# .env (never commit)
GEMINI_API_KEY=your_gemini_api_key_here
```

```bash
# .env.example (commit this)
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## Development Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project and sync deps
uv sync

# Add .env with your Gemini key
cp .env.example .env
# Edit .env and add GEMINI_API_KEY

# Run dev server
uv run uvicorn main:app --reload --port 8000
```

---

## Deployment (Render free tier)

1. Push to GitHub
2. New Web Service on Render
3. Build command: `pip install uv && uv sync --frozen`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env var: `GEMINI_API_KEY`

---

## Key Implementation Notes for AI Agents

1. **Async everywhere**: `database.py` uses `aiosqlite` — all DB functions are `async def`. The pipeline's `enrich_company` must also be `async def` (use `asyncio.to_thread` for the sync Gemini client call).

2. **Spinner is mandatory**: The Gemini + search grounding call takes 10–30 seconds. The spinner must be visible the entire time. Use `fetch` with the button disabled and a CSS animation running.

3. **URL normalization**: Always strip trailing slashes and prepend `https://` if no scheme.

4. **Mail as JSON string in DB**: Store `mail` as `json.dumps(list)` in SQLite; parse back on fetch.

5. **EMPTY_RECORD fallback**: Always return a complete 9-field dict even on total failure. Never return `None` or raise from `enrich_company`.

6. **No CORS issues**: Frontend calls the same FastAPI origin — no CORS config needed.

7. **Rate limiting**: Add `await asyncio.sleep(1.5)` between batch calls if ever processing multiple URLs.

8. **Error display**: Show a red banner with the error message in the UI. Do not just silently fail.

9. **Table + Cards toggle**: Both views must be rendered from the same data. Use CSS `display: none` to toggle.

10. **outreach_opener styling**: Display this field in a visually distinct way (teal left-border box, italic text) — it's the highest-value output.

---

## Features Checklist

- [ ] Single URL enrichment via POST /enrich
- [ ] Animated spinner during enrichment (10–30s wait)
- [ ] All 9 fields extracted and displayed
- [ ] Results persisted to SQLite
- [ ] GET /results returns all historical results
- [ ] Table view with sortable columns
- [ ] Card view with full field display
- [ ] Toggle between table and card view
- [ ] Error handling with user-friendly messages
- [ ] Responsive design (mobile + desktop)
- [ ] Docker + deployment-ready
- [ ] uv + pyproject.toml environment management
- [ ] Gemini primary + raw scrape fallback pipeline
- [ ] outreach_opener in highlighted visual box
- [ ] Mail displayed as pill badges
- [ ] Auto-refresh results after enrich

---

*Generated for hackathon submission. Build with uv, FastAPI, Gemini 2.0 Flash.*
