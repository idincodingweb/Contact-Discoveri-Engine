"""SQLite repository — single source of truth for persistence."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


SCHEMA_FILE = Path(__file__).parent / "schema.sql"


class Repository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    def init_schema(self) -> None:
        sql = SCHEMA_FILE.read_text(encoding="utf-8")
        with self.conn() as c:
            c.executescript(sql)

    # ---------- companies ----------
    def upsert_company(self, *, name: str | None, domain: str, website: str,
                       country: str = "", niche: str = "") -> int:
        with self.conn() as c:
            cur = c.execute(
                """INSERT INTO companies(name, domain, website, country, niche)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(domain) DO UPDATE SET
                       name=COALESCE(excluded.name, companies.name),
                       website=COALESCE(excluded.website, companies.website),
                       country=COALESCE(excluded.country, companies.country),
                       niche=COALESCE(excluded.niche, companies.niche)
                   RETURNING id;""",
                (name, domain, website, country, niche),
            )
            row = cur.fetchone()
            return int(row["id"])

    # ---------- contacts ----------
    def insert_contact(self, company_id: int, payload: dict[str, Any]) -> None:
        cols = ["company_id", "contact_name", "role", "role_priority",
                "email", "whatsapp", "telegram", "linkedin",
                "instagram", "facebook", "twitter", "tiktok",
                "youtube", "source_url"]
        values = [company_id] + [payload.get(c) for c in cols[1:]]
        placeholders = ",".join("?" * len(cols))
        with self.conn() as c:
            try:
                c.execute(
                    f"INSERT OR IGNORE INTO contacts({','.join(cols)}) VALUES({placeholders})",
                    values,
                )
            except sqlite3.IntegrityError:
                pass

    # ---------- discoveries ----------
    def add_discovery(self, company_id: int, kind: str, value: str,
                      source_url: str, confidence: float = 0.5) -> None:
        with self.conn() as c:
            c.execute(
                """INSERT OR IGNORE INTO discoveries(company_id, kind, value, source_url, confidence)
                   VALUES(?,?,?,?,?)""",
                (company_id, kind, value, source_url, confidence),
            )

    def get_discoveries(self, company_id: int) -> list[sqlite3.Row]:
        with self.conn() as c:
            return list(c.execute(
                "SELECT * FROM discoveries WHERE company_id=?", (company_id,)
            ))

    # ---------- crawl logs ----------
    def log_crawl(self, url: str, status: int, size: int, error: str = "") -> None:
        with self.conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO crawl_logs(url, status_code, bytes, error)
                   VALUES(?,?,?,?)""",
                (url, status, size, error),
            )

    def is_crawled(self, url: str) -> bool:
        with self.conn() as c:
            row = c.execute(
                "SELECT 1 FROM crawl_logs WHERE url=? AND status_code BETWEEN 200 AND 399",
                (url,),
            ).fetchone()
            return row is not None

    # ---------- export queries ----------
    def export_rows(self) -> list[dict]:
        sql = """
        SELECT
            co.name        AS company_name,
            co.website     AS website,
            ct.contact_name,
            ct.role,
            ct.email,
            ct.whatsapp,
            ct.telegram,
            ct.linkedin,
            ct.instagram,
            ct.facebook,
            ct.twitter,
            ct.tiktok,
            ct.youtube,
            ct.source_url
        FROM contacts ct
        JOIN companies co ON co.id = ct.company_id
        ORDER BY ct.role_priority ASC, co.name ASC
        """
        with self.conn() as c:
            return [dict(r) for r in c.execute(sql)]
