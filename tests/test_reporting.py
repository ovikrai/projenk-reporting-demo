import json
import os
import tempfile
import unittest
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from pathlib import Path
from unittest.mock import patch

from reporting.__main__ import run
from reporting.mail import compose, send
from reporting.pipeline import calculate, clean_csv, money, numeric, summarize, write_csv
from reporting.report import render_report
from reporting.synthetic import FIELDS, generate


def order(**changes):
    return {**dict(order_id="TEST-1", order_date="2026-09-01", category="Apparel",
                region="North", channel="Online", quantity="2", unit_price="100.00",
                unit_cost="40.00", discount_pct="10", status="completed"), **changes}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def clean(self, rows):
        source = self.root / "input.csv"
        write_csv(source, rows, FIELDS)
        return clean_csv(source)

    def test_currency_math_excludes_refunds_and_cancellations(self):
        rows = [order(), order(order_id="TEST-2", status="refunded"), order(order_id="TEST-3", status="cancelled")]
        result = summarize(rows)
        self.assertEqual(result["revenue"], 180)
        self.assertEqual(result["cogs"], 80)
        self.assertEqual(result["gross_profit"], 100)
        self.assertEqual(result["orders"], 1)
        self.assertEqual(result["aov"], 180)
        self.assertEqual(result["refund_rate"], 50)
        self.assertEqual(result["margin"], 55.56)

    def test_round_each_order_half_up(self):
        self.assertEqual(money(Decimal("0.045")), Decimal("0.05"))
        result = summarize([order(quantity="1", unit_price="0.05", unit_cost="0.00")])
        self.assertEqual(result["revenue"], 0.05)

    def test_normalization_and_cleaned_round_trip(self):
        rows, audit = self.clean([order(channel=" online ", status="COMPLETED", unit_price="$1,000.00")])
        self.assertEqual(rows[0]["unit_price"], "1000.00")
        self.assertEqual(rows[0]["channel"], "Online")
        self.assertEqual(rows[0]["discount_pct"], "10")
        self.assertEqual(audit["normalized_rows"], 1)
        again, audit2 = self.clean(rows)
        self.assertEqual(again, rows)
        self.assertEqual(audit2["normalized_rows"], 0)

    def test_reject_invalid_values_and_keep_line_numbers(self):
        for field, value in [("order_date", "2026-09-31"), ("quantity", "0"),
            ("quantity", "1.5"), ("quantity", "NaN"), ("unit_price", "Infinity"),
            ("unit_price", "-1"), ("unit_cost", "0.001"), ("discount_pct", "101"),
            ("category", ""), ("region", "Mars"), ("status", "pending"),
            ("order_id", "=SUM(1,1)")]:
            with self.subTest(field=field, value=value):
                rows, audit = self.clean([order(), order(order_id="BAD", **{field:value})] if field!="order_id" else [order(),order(order_id=value)])
                self.assertEqual(len(rows), 1)
                self.assertEqual(audit["rejected_rows"], 1)
                self.assertEqual(audit["rejected"][0]["line"], 3)

    def test_duplicate_retains_first_valid_occurrence(self):
        rows, audit = self.clean([order(quantity="-1"), order(), order(unit_price="900")])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["unit_price"], "100.00")
        self.assertEqual(audit["rejected_rows"], 2)

    def test_schema_fail_fast(self):
        source = self.root / "bad.csv"
        source.write_text("wrong,header\na,b\n")
        with self.assertRaisesRegex(ValueError, "header"):
            clean_csv(source)

    def test_extra_or_missing_columns(self):
        source = self.root / "ragged.csv"
        source.write_text(",".join(FIELDS)+"\n"+",".join(order().values())+"\nbad,too,few\n"+",".join(order(order_id="TOO-MANY").values())+",extra\n")
        rows, audit = clean_csv(source)
        self.assertEqual(len(rows), 1)
        self.assertEqual(audit["rejected_rows"], 2)
        self.assertEqual(audit["reasons"], {"wrong column count": 2})

    def test_empty_input_fails(self):
        with self.assertRaisesRegex(ValueError, "No valid records"):
            self.clean([])

    def test_no_baseline_is_null_not_zero_growth(self):
        result = calculate([order()], "2026-09")
        self.assertIsNone(result["previous"])
        self.assertIsNone(result["deltas"]["revenue"])

    def test_previous_month_and_year_boundary(self):
        result = calculate([order(order_date="2026-01-01"),
            order(order_id="PRIOR", order_date="2025-12-31", quantity="1")], "2026-01")
        self.assertEqual(result["deltas"]["revenue"], 100)
        self.assertEqual(result["previous"]["orders"], 1)

    def test_month_selection_and_invalid_month(self):
        with self.assertRaises(ValueError):
            calculate([order()], "2026-13")
        with self.assertRaisesRegex(ValueError, "No valid records"):
            calculate([order()], "2026-08")

    def test_no_completed_orders_handles_zero_denominators(self):
        result = calculate([order(status="cancelled")], "2026-09")
        self.assertEqual(result["aov"], 0)
        self.assertEqual(result["margin"], 0)
        self.assertEqual(result["refund_rate"], 0)

    def test_synthetic_data_and_artifacts_reproduce(self):
        source = self.root / "sample.csv"
        generate(source)
        first = source.read_bytes()
        generate(source)
        self.assertEqual(first, source.read_bytes())
        output = self.root / "artifacts"
        result = run(source, output, "2026-09")
        self.assertEqual((result["audit"]["raw_rows"], result["audit"]["accepted_rows"], result["audit"]["rejected_rows"]), (832,805,27))
        self.assertEqual(result["metrics"]["revenue"], 54335.43)
        self.assertEqual(result["metrics"]["orders"], 289)
        before = {p.name:p.read_bytes() for p in output.iterdir()}
        run(source, output, "2026-09")
        self.assertEqual(before, {p.name:p.read_bytes() for p in output.iterdir()})
        parsed = BytesParser(policy=policy.default).parsebytes((output / "report.eml").read_bytes())
        attachment = next(parsed.iter_attachments())
        self.assertEqual(attachment.get_filename(), "projenk-report-2026-09.html")
        self.assertEqual(attachment.get_payload(decode=True), (output / "report.html").read_bytes())
        self.assertEqual(parsed["To"], "operations@example.com")
        self.assertEqual(json.loads((output/"run.json").read_text())["email_status"], "prepared")

    def test_report_escapes_strings(self):
        metrics = calculate([order()], "2026-09")
        metrics["categories"][0]["name"] = "<script>alert(1)</script>"
        html = render_report("2026-09",metrics,{"raw_rows":1,"accepted_rows":1,"rejected_rows":0,"normalized_rows":0,"source_sha256":"abc"})
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_numeric_format_rejects_malformed_grouping(self):
        self.assertEqual(numeric("$1,200.50"), Decimal("1200.50"))
        for value in ["1,2", "NaN", "1e8", "1,000,00"]:
            with self.assertRaises(ValueError):
                numeric(value)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.output = Path(self.directory.name)
        self.message = compose("2026-09", summarize([order()]), "<html>synthetic report</html>", "owner@test.invalid")

    def tearDown(self):
        self.directory.cleanup()

    def test_preview_never_connects_to_smtp(self):
        with patch("reporting.mail.smtplib.SMTP") as smtp:
            compose("2026-09", summarize([order()]), "report")
            smtp.assert_not_called()

    def test_missing_config_does_not_send(self):
        with patch.dict(os.environ, {}, clear=True), patch("reporting.mail.smtplib.SMTP") as smtp:
            with self.assertRaisesRegex(ValueError, "SMTP_HOST"):
                send(self.message,self.output,"run")
            smtp.assert_not_called()

    def test_tls_delivery_and_receipt_prevent_duplicate_send(self):
        env={"SMTP_HOST":"mail.test.invalid","REPORT_EMAIL_FROM":"sender@test.invalid","SMTP_USER":"user","SMTP_PASSWORD":"secret"}
        with patch.dict(os.environ,env,clear=True), patch("reporting.mail.smtplib.SMTP") as smtp:
            client=smtp.return_value.__enter__.return_value
            client.send_message.return_value={}
            self.assertEqual(send(self.message,self.output,"run"), "sent")
            self.assertIn("already sent", send(self.message,self.output,"run"))
            smtp.assert_called_once()
            client.starttls.assert_called_once()
            client.login.assert_called_once_with("user","secret")
            client.send_message.assert_called_once()
            self.assertEqual(len(list(self.output.glob("delivery-*.json"))),1)

    def test_ambiguous_failure_keeps_lock_for_review(self):
        with patch.dict(os.environ,{"SMTP_HOST":"mail.test.invalid","REPORT_EMAIL_FROM":"sender@test.invalid"},clear=True), patch("reporting.mail.smtplib.SMTP") as smtp:
            client=smtp.return_value.__enter__.return_value
            client.send_message.side_effect=OSError("connection dropped")
            with self.assertRaises(OSError):
                send(self.message,self.output,"run")
            with self.assertRaisesRegex(ValueError,"Delivery lock"):
                send(self.message,self.output,"run")
            self.assertEqual(len(list(self.output.glob("*.lock"))),1)


if __name__ == "__main__":
    unittest.main()
