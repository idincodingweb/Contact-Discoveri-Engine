"""Export to CSV / JSON / XLSX."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from database.repo import Repository

log = logging.getLogger(__name__)


class Exporter:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def export_all(self, prefix: str = "outputs/results") -> None:
        rows = self.repo.export_rows()
        if not rows:
            log.warning("No rows to export.")
            Path(prefix + ".csv").write_text("", encoding="utf-8")
            return

        df = pd.DataFrame(rows)

        # Friendly column order
        column_order = [
            "company_name", "website", "contact_name", "role",
            "email", "whatsapp", "telegram", "linkedin",
            "instagram", "facebook", "twitter", "tiktok", "youtube",
            "source_url",
        ]
        for c in column_order:
            if c not in df.columns:
                df[c] = None
        df = df[column_order]

        Path(prefix).parent.mkdir(parents=True, exist_ok=True)

        # CSV
        csv_path = f"{prefix}.csv"
        df.to_csv(csv_path, index=False)
        log.info("CSV  → %s (%d rows)", csv_path, len(df))

        # JSON
        json_path = f"{prefix}.json"
        Path(json_path).write_text(
            json.dumps(rows, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log.info("JSON → %s", json_path)

        # XLSX
        xlsx_path = f"{prefix}.xlsx"
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="contacts")
        log.info("XLSX → %s", xlsx_path)
