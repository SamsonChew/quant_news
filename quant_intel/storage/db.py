from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from quant_intel.models import Item, Score, Summary


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        self.conn.executescript(schema_path.read_text(encoding="utf-8"))
        self.conn.commit()

    def upsert_item(self, item: Item) -> bool:
        before = self.conn.total_changes
        try:
            self.conn.execute(
                """
                INSERT INTO items (
                  id, source, source_type, title, url, authors, published_at,
                  collected_at, raw_text, abstract, content_hash, category, tags,
                  language, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  source = excluded.source,
                  source_type = excluded.source_type,
                  title = excluded.title,
                  url = excluded.url,
                  authors = excluded.authors,
                  published_at = excluded.published_at,
                  collected_at = excluded.collected_at,
                  raw_text = excluded.raw_text,
                  abstract = excluded.abstract,
                  category = excluded.category,
                  tags = excluded.tags,
                  language = excluded.language,
                  metadata = excluded.metadata
                """,
                (
                    item.id,
                    item.source,
                    item.source_type,
                    item.title,
                    item.url,
                    json.dumps(item.authors, ensure_ascii=False),
                    item.published_at,
                    item.collected_at,
                    item.raw_text,
                    item.abstract,
                    item.content_hash,
                    item.category,
                    json.dumps(item.tags, ensure_ascii=False),
                    item.language,
                    json.dumps(item.metadata, ensure_ascii=False),
                ),
            )
        except sqlite3.IntegrityError:
            return False
        self.conn.commit()
        return self.conn.total_changes > before

    def upsert_summary(self, summary: Summary) -> None:
        self.conn.execute(
            """
            INSERT INTO summaries (
              item_id, one_line_summary, technical_summary, key_points,
              quant_relevance, possible_use_case, limitations, read_priority,
              model_name, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
              one_line_summary = excluded.one_line_summary,
              technical_summary = excluded.technical_summary,
              key_points = excluded.key_points,
              quant_relevance = excluded.quant_relevance,
              possible_use_case = excluded.possible_use_case,
              limitations = excluded.limitations,
              read_priority = excluded.read_priority,
              model_name = excluded.model_name,
              created_at = excluded.created_at
            """,
            (
                summary.item_id,
                summary.one_line_summary,
                summary.technical_summary,
                json.dumps(summary.key_points, ensure_ascii=False),
                summary.quant_relevance,
                summary.possible_use_case,
                summary.limitations,
                summary.read_priority,
                summary.model_name,
                summary.created_at,
            ),
        )
        self.conn.commit()

    def upsert_score(self, score: Score) -> None:
        self.conn.execute(
            """
            INSERT INTO scores (
              item_id, relevance_score, novelty_score, academic_score,
              discussion_score, actionable_score, final_score, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
              relevance_score = excluded.relevance_score,
              novelty_score = excluded.novelty_score,
              academic_score = excluded.academic_score,
              discussion_score = excluded.discussion_score,
              actionable_score = excluded.actionable_score,
              final_score = excluded.final_score,
              created_at = excluded.created_at
            """,
            (
                score.item_id,
                score.relevance_score,
                score.novelty_score,
                score.academic_score,
                score.discussion_score,
                score.actionable_score,
                score.final_score,
                score.created_at,
            ),
        )
        self.conn.commit()

    def insert_report(
        self,
        report_date: str,
        report_path: str,
        generated_at: str,
        item_count: int,
        source_stats: dict[str, Any],
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO reports (
              report_date, report_path, generated_at, item_count, source_stats
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(report_date) DO UPDATE SET
              report_path = excluded.report_path,
              generated_at = excluded.generated_at,
              item_count = excluded.item_count,
              source_stats = excluded.source_stats
            """,
            (
                report_date,
                report_path,
                generated_at,
                item_count,
                json.dumps(source_stats, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def fetch_report_rows(self, report_date: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT
              i.*,
              s.one_line_summary,
              s.technical_summary,
              s.key_points,
              s.quant_relevance,
              s.possible_use_case,
              s.limitations,
              s.read_priority,
              sc.relevance_score,
              sc.novelty_score,
              sc.academic_score,
              sc.discussion_score,
              sc.actionable_score,
              sc.final_score
            FROM items i
            JOIN summaries s ON s.item_id = i.id
            JOIN scores sc ON sc.item_id = i.id
            WHERE substr(i.collected_at, 1, 10) = ?
            ORDER BY sc.final_score DESC
            """,
            (report_date,),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def fetch_report_rows_by_ids(self, item_ids: list[str]) -> list[dict[str, Any]]:
        if not item_ids:
            return []
        placeholders = ",".join("?" for _ in item_ids)
        rows = self.conn.execute(
            f"""
            SELECT
              i.*,
              s.one_line_summary,
              s.technical_summary,
              s.key_points,
              s.quant_relevance,
              s.possible_use_case,
              s.limitations,
              s.read_priority,
              sc.relevance_score,
              sc.novelty_score,
              sc.academic_score,
              sc.discussion_score,
              sc.actionable_score,
              sc.final_score
            FROM items i
            JOIN summaries s ON s.item_id = i.id
            JOIN scores sc ON sc.item_id = i.id
            WHERE i.id IN ({placeholders})
            ORDER BY sc.final_score DESC
            """,
            item_ids,
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def fetch_rows_between(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT
              i.*,
              s.one_line_summary,
              s.technical_summary,
              s.key_points,
              s.quant_relevance,
              s.possible_use_case,
              s.limitations,
              s.read_priority,
              sc.relevance_score,
              sc.novelty_score,
              sc.academic_score,
              sc.discussion_score,
              sc.actionable_score,
              sc.final_score
            FROM items i
            JOIN summaries s ON s.item_id = i.id
            JOIN scores sc ON sc.item_id = i.id
            WHERE substr(i.collected_at, 1, 10) BETWEEN ? AND ?
            ORDER BY substr(i.collected_at, 1, 10) DESC, sc.final_score DESC
            """,
            (start_date, end_date),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def source_stats(self, report_date: str) -> dict[str, int]:
        rows = self.conn.execute(
            """
            SELECT source, COUNT(*) AS count
            FROM items
            WHERE substr(collected_at, 1, 10) = ?
            GROUP BY source
            ORDER BY count DESC
            """,
            (report_date,),
        ).fetchall()
        return {str(row["source"]): int(row["count"]) for row in rows}

    def source_stats_by_ids(self, item_ids: list[str]) -> dict[str, int]:
        if not item_ids:
            return {}
        placeholders = ",".join("?" for _ in item_ids)
        rows = self.conn.execute(
            f"""
            SELECT source, COUNT(*) AS count
            FROM items
            WHERE id IN ({placeholders})
            GROUP BY source
            ORDER BY count DESC
            """,
            item_ids,
        ).fetchall()
        return {str(row["source"]): int(row["count"]) for row in rows}

    def source_stats_between(self, start_date: str, end_date: str) -> dict[str, int]:
        rows = self.conn.execute(
            """
            SELECT source, COUNT(*) AS count
            FROM items
            WHERE substr(collected_at, 1, 10) BETWEEN ? AND ?
            GROUP BY source
            ORDER BY count DESC
            """,
            (start_date, end_date),
        ).fetchall()
        return {str(row["source"]): int(row["count"]) for row in rows}

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        for field in ("authors", "tags", "metadata", "key_points"):
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except json.JSONDecodeError:
                    data[field] = []
        return data
