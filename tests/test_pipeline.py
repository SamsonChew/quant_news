from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from quant_intel.config import load_report_config, load_scoring_config
from quant_intel.pipeline.classify import classify_item
from quant_intel.pipeline.score import score_item
from quant_intel.pipeline.summarize import summarize_item, summary_from_llm_payload
from quant_intel.reports import build_daily_report, build_home_dashboard
from quant_intel.reports import build_html_dashboard
from quant_intel.sources import SampleSource
from quant_intel.storage import Database


class PipelineTest(unittest.TestCase):
    def test_sample_items_generate_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db = Database(tmp_path / "test.sqlite")
            db.init_schema()
            today = date.today()

            for item in SampleSource().fetch():
                item = classify_item(item)
                score = score_item(item, load_scoring_config(), today=today)
                summary = summarize_item(item, score)
                db.upsert_item(item)
                db.upsert_score(score)
                db.upsert_summary(summary)

            rows = db.fetch_report_rows(today.isoformat())
            report = build_daily_report(
                rows,
                today.isoformat(),
                tmp_path,
                load_report_config(),
                db.source_stats(today.isoformat()),
            )
            dashboard = build_html_dashboard(
                rows,
                today.isoformat(),
                tmp_path,
                load_report_config(),
                db.source_stats(today.isoformat()),
            )
            home = build_home_dashboard(
                rows,
                today.isoformat(),
                7,
                tmp_path,
                load_report_config(),
                db.source_stats(today.isoformat()),
            )

            self.assertGreaterEqual(len(rows), 6)
            self.assertTrue(report.exists())
            report_text = report.read_text()
            self.assertIn("每日量化情报报告", report_text)
            self.assertIn("深度学习量化未来", report_text)
            self.assertIn("这篇文章的太长不读", report_text)
            self.assertIn("核心价值，对我量化的工作能够提供什么样的帮助", report_text)
            self.assertIn("关键核心点 / 论文或帖子摘要", report_text)
            self.assertTrue(dashboard.exists())
            dashboard_text = dashboard.read_text()
            self.assertIn("量化情报台", dashboard_text)
            self.assertIn("深度学习量化未来", dashboard_text)
            self.assertIn("原文链接", dashboard_text)
            self.assertTrue(home.exists())
            home_text = home.read_text()
            self.assertIn("量化情报首页", home_text)
            self.assertIn("深度学习量化未来", home_text)
            self.assertIn("这篇文章的太长不读", home_text)
            self.assertIn("原文链接", home_text)
            db.close()

    def test_llm_summary_payload_uses_fallbacks(self) -> None:
        item = classify_item(SampleSource().fetch()[0])
        score = score_item(item, load_scoring_config(), today=date.today())
        summary = summary_from_llm_payload(
            item=item,
            score=score,
            payload={
                "one_line_summary": "大模型摘要",
                "technical_summary": "",
                "key_points": ["第一点"],
                "read_priority": "urgent",
            },
            model_name="deepseek:deepseek-chat",
        )

        self.assertEqual(summary.one_line_summary, "大模型摘要")
        self.assertEqual(summary.model_name, "deepseek:deepseek-chat")
        self.assertEqual(len(summary.key_points), 3)
        self.assertIn(summary.read_priority, {"高", "中", "低"})


if __name__ == "__main__":
    unittest.main()
