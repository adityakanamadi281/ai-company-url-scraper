# ⬡ Company Intelligence Scraper

An AI-powered, high-fidelity business intelligence enrichment web application. It takes any company URL and extracts **9 structured business intelligence fields** in seconds, leveraging the power of **Gemini** with active **Google Search Grounding** and an automated scraper backup system.

---

## 🚀 Features

- **Dual-Pipeline Enrichment Workflow**:
  - **Primary (Search Grounding)**: Harnesses Gemini with real-time Google Search grounding to fetch the most up-to-date business details directly from search results.
  - **Fallback (Automated Scraper)**: When search grounding is unavailable, the pipeline falls back to an intelligent multi-page web crawler. It automatically scans sitemaps, discovers critical URLs (Homepage, About, Contact, Services/Solutions), fetches page content using `requests` + `BeautifulSoup`, filters boilerplate tags, and utilizes Gemini to parse raw HTML text into structured data.
- **Robust Field Extraction**: Automatically retrieves and structures exactly 9 corporate data fields, including target customers, pain points solved, and an AI-generated personalized outreach cold opener.
- **Local Persistence**: Async SQLite database interface powered by `aiosqlite` with built-in upsert (`ON CONFLICT`) capabilities on URL matching.
- **High-Fidelity UI**:
  - Gorgeous dark-mode dashboard styled with CSS-only glassmorphism.
  - Interactive grid card layout and dynamic compact table view.
  - Responsive layout built with CSS Grid and Flexbox.
  - Real-time live enrichment preview.
- **Modern Development Setup**: Managed by `uv`—the lightning-fast Python package manager—and fully containerized with Docker.

---

## 🛠️ Tech Stack

### Backend
- **Framework**: `FastAPI` — Async, high-performance web framework for Python.
- **ASGI Server**: `Uvicorn` — Lightning-fast ASGI web server implementation.
- **Database**: `SQLite` with `aiosqlite` for fully non-blocking database interactions.
- **LLM/AI Integration**: `Google GenAI Python SDK` accessing the robust `gemma-4-31b` models.
- **Web Crawling & Extraction**:
  - `BeautifulSoup4` & `lxml` — HTML scraping and parse tree traversal.
  - `RapidFuzz` — Fuzzy string matching for locating high-value URL slugs (about, contact, services).
  - `Requests` — Synchronous HTTP client executed inside async thread pools.
- **Environment Management**: `python-dotenv` for configuration injection.

### Frontend
- **Structure**: Semantic HTML5.
- **Styling**: Vanilla CSS3 featuring custom CSS variables, dark glassmorphism, responsive grid sheets, and custom micro-animations (e.g. input glow, loading spinner, button hover states).
- **Interactivity**: Pure modern ES6+ JavaScript handling client-side API requests, custom templating, and view-state toggles (Cards vs. Table views) without bulky library overhead.

### DevOps & Packaging
- **Package Manager**: [uv](https://github.com/astral-sh/uv) by Astral (fast, reproducible installations via `pyproject.toml` and `uv.lock`).
- **Containerization**: Production-ready multi-stage `Dockerfile`.

---

## ⚡ Setup and Installation

### 1. Clone the Repository
```bash
git clone https://github.com/adityakanamadi281/ai-company-scraper.git
cd ai-company-scraper
```

### 2. Sync Dependencies
```bash
# Sync all dependencies and setup the virtual environment using uv
uv sync
```

### 3. Configure API Key
Create a `.env` file from the example and add your Gemini API Key:
```bash
cp .env.example .env
```
Open `.env` in your editor and input your key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Run the Server
Launch the development server:
```bash
uv run uvicorn main:app --reload --port 8000
```
Open your browser and navigate to **[http://localhost:8000](http://localhost:8000)**.

---

## 📂 Project Structure

```text
company-scraper/
├── .env                  # Local environment configuration (contains GEMINI_API_KEY)
├── .env.example          # Sample environment configuration template
├── .gitignore            # Git exclusion rules
├── .venv/                # Local Python virtual environment
├── companies.db          # SQLite database (generated automatically at runtime)
├── database.py           # Async SQLite database interface (aiosqlite)
├── Dockerfile            # Container definition for production deployment
├── main.py               # Main application entry point & Lifespan setup
├── models.py             # Pydantic data schemas for requests and database profiles
├── pipeline.py           # Core enrichment logic: Gemini Search Grounding + Crawl Fallback
├── pyproject.toml        # Modern uv project dependency declaration
├── README.md             # This project guide
├── routers/              # Modular backend endpoint controllers
│   ├── __init__.py       # Package indicator
│   ├── enrich.py         # Enrichment controller (/enrich POST)
│   └── results.py        # Retrieves saved companies (/results GET)
├── static/               # Client-side static assets
│   ├── app.js            # Frontend interactivity, UI rendering, view toggles
│   └── style.css         # Modern, high-fidelity responsive styling rules
├── templates/            # HTML views
│   └── index.html        # App dashboard layout (glassmorphism/dark mode)
└── uv.lock               # Deterministic dependency locking file
```


