from __future__ import annotations
import json
import aiosqlite

DB_PATH = "companies.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS companies (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    url              TEXT UNIQUE NOT NULL,
    website_name     TEXT DEFAULT '',
    company_name     TEXT DEFAULT '',
    address          TEXT DEFAULT '',
    mobile_number    TEXT DEFAULT '',
    mail             TEXT DEFAULT '[]',
    core_service     TEXT DEFAULT '',
    target_customer  TEXT DEFAULT '',
    probable_pain_point TEXT DEFAULT '',
    outreach_opener  TEXT DEFAULT '',
    created_at       TEXT DEFAULT (datetime('now'))
)
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()


async def save_company(url: str, data: dict) -> int:
    mail_json = json.dumps(data.get("mail", []))
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO companies
                (url, website_name, company_name, address, mobile_number,
                 mail, core_service, target_customer, probable_pain_point, outreach_opener)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                website_name     = excluded.website_name,
                company_name     = excluded.company_name,
                address          = excluded.address,
                mobile_number    = excluded.mobile_number,
                mail             = excluded.mail,
                core_service     = excluded.core_service,
                target_customer  = excluded.target_customer,
                probable_pain_point = excluded.probable_pain_point,
                outreach_opener  = excluded.outreach_opener,
                created_at       = datetime('now')
            """,
            (
                url,
                data.get("website_name", ""),
                data.get("company_name", ""),
                data.get("address", ""),
                data.get("mobile_number", ""),
                mail_json,
                data.get("core_service", ""),
                data.get("target_customer", ""),
                data.get("probable_pain_point", ""),
                data.get("outreach_opener", ""),
            ),
        )
        await db.commit()
        return cursor.lastrowid or 0


async def fetch_all_companies() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM companies ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()

    result = []
    for row in rows:
        d = dict(row)
        try:
            d["mail"] = json.loads(d.get("mail") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["mail"] = []
        result.append(d)
    return result
