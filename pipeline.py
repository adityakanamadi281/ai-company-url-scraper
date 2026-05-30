from __future__ import annotations
import asyncio
import json
import os
import random
import re
import time
import warnings
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
from google import genai
from google.genai import types

warnings.filterwarnings("ignore")

# ── Constants ────────────────────────────────────────────────────────────────

MODEL = "gemma-4-31b-it" 

EMPTY_RECORD: dict = {
    "website_name": "",
    "company_name": "",
    "address": "",
    "mobile_number": "",
    "mail": [],
    "core_service": "",
    "target_customer": "",
    "probable_pain_point": "",
    "outreach_opener": "",
}

SYSTEM_INSTRUCTION = """\
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
}"""

USER_TEMPLATE = """\
Research the company at this URL using Google Search: {url}

Visit their homepage, about page, contact page, and services/solutions page.
Then return ONLY the raw JSON object described in your instructions — no extra text."""

GEMINI_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_INSTRUCTION,
    tools=[types.Tool(google_search=types.GoogleSearch())],
    temperature=0.1,
    max_output_tokens=2048,
)

FALLBACK_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_INSTRUCTION,
    temperature=0.1,
    max_output_tokens=2048,
)

# ── Gemini client (lazy singleton) ───────────────────────────────────────────

_client: genai.Client | None = None


def get_gemini_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        _client = genai.Client(api_key=api_key)
    return _client


# ── JSON helpers ─────────────────────────────────────────────────────────────

def parse_json_response(text: str) -> dict:
    if not text:
        return {}
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def normalize_record(raw: dict) -> dict:
    out = {**EMPTY_RECORD, **raw}
    if isinstance(out["mail"], str):
        out["mail"] = [out["mail"].strip()] if out["mail"].strip() else []
    elif isinstance(out["mail"], list):
        out["mail"] = [
            m.strip() for m in out["mail"]
            if isinstance(m, str) and m.strip()
        ]
    else:
        out["mail"] = []
    for k, v in out.items():
        if isinstance(v, str):
            out[k] = v.strip()
    return out


# ── Scrape helpers (fallback) ─────────────────────────────────────────────────

SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

BOILERPLATE_TAGS = {
    "script", "style", "noscript", "svg", "iframe",
    "nav", "footer", "header", "aside", "form",
}

TARGET_SLUGS = [
    "about", "about-us", "company", "who-we-are",
    "contact", "contact-us", "reach-us",
    "services", "solutions", "what-we-do", "products",
]


def _slug_score(url: str) -> int:
    slug = urlparse(url).path.lower().strip("/").split("/")[-1]
    slug = slug.replace("-", " ").replace("_", " ")
    return max((fuzz.partial_ratio(slug, kw) for kw in TARGET_SLUGS), default=0)


def _safe_get(url: str, timeout: int = 10) -> requests.Response | None:
    for _ in range(2):
        try:
            time.sleep(random.uniform(0.6, 1.4))
            r = requests.get(url, headers=SCRAPE_HEADERS, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                return r
        except Exception:
            pass
    return None


def _clean_html(html: str, max_chars: int = 6000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(BOILERPLATE_TAGS):
        tag.decompose()
    meta = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
    meta_text = f"[META]: {meta['content'].strip()}\n" if meta and meta.get("content") else ""
    lines = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li", "td", "span", "a"]):
        t = tag.get_text(" ", strip=True)
        if len(t) > 25:
            lines.append(t)
    return (meta_text + "\n".join(dict.fromkeys(lines)))[:max_chars]


def scrape_site_text(base_url: str) -> str:
    origin = base_url.rstrip("/")
    found: dict[str, int] = {origin + "/": 100}

    for path in ["/sitemap.xml", "/sitemap_index.xml"]:
        resp = _safe_get(origin + path)
        if not resp:
            continue
        try:
            root = ElementTree.fromstring(resp.content)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            for loc in [e.text for e in root.findall(".//sm:loc", ns) if e.text]:
                if urlparse(loc).netloc == urlparse(origin).netloc:
                    s = _slug_score(loc)
                    if s >= 55:
                        found[loc] = s
        except Exception:
            pass
        if len(found) > 1:
            break

    if len(found) <= 1:
        resp = _safe_get(origin)
        if resp:
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = urljoin(origin, a["href"])
                if urlparse(href).netloc == urlparse(origin).netloc:
                    s = _slug_score(href)
                    if s >= 55:
                        found[href] = s

    pages = [u for u, _ in sorted(found.items(), key=lambda x: x[1], reverse=True)[:5]]
    chunks = []
    for page in pages:
        resp = _safe_get(page)
        if resp:
            text = _clean_html(resp.text)
            if text:
                chunks.append(f"=== {urlparse(page).path or '/'} ===\n{text}")

    return "\n\n".join(chunks)[:20_000]


# ── Main enrichment pipeline ──────────────────────────────────────────────────

async def enrich_company(url: str) -> dict:
    domain = urlparse(url).netloc or url

    # PRIMARY: Gemini + Google Search grounding
    try:
        client = get_gemini_client()
        prompt = USER_TEMPLATE.format(url=url)

        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=prompt,
            config=GEMINI_CONFIG,
        )
        raw_text = response.text or ""
        parsed = parse_json_response(raw_text)
        if parsed:
            result = normalize_record(parsed)
            if not result["website_name"]:
                result["website_name"] = domain
            return result
    except Exception as e:
        print(f"[pipeline] Gemini grounding error: {e} — trying fallback")

    # FALLBACK: raw scrape → Gemini without grounding
    try:
        site_text = await asyncio.to_thread(scrape_site_text, url)
        if not site_text:
            return {**EMPTY_RECORD, "website_name": domain}

        fallback_prompt = (
            f"Website URL: {url}\n\n"
            f"Website content:\n{site_text}\n\n"
            "Extract the 9-field JSON from this content. "
            "Return ONLY the raw JSON object."
        )

        client = get_gemini_client()
        response2 = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=fallback_prompt,
            config=FALLBACK_CONFIG,
        )
        raw_text2 = response2.text or ""
        parsed2 = parse_json_response(raw_text2)
        if parsed2:
            result2 = normalize_record(parsed2)
            if not result2["website_name"]:
                result2["website_name"] = domain
            return result2
    except Exception as e:
        print(f"[pipeline] Fallback error: {e}")

    return {**EMPTY_RECORD, "website_name": domain}
