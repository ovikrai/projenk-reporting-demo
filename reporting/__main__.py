import argparse
import os
import sys
from pathlib import Path

from .mail import compose, send
from .pipeline import calculate, clean_csv, write_csv, write_json
from .report import insights, render_report
from .synthetic import FIELDS, generate


def run(source, output, month, recipient="operations@example.com", deliver=False):
    rows, audit = clean_csv(source)
    metrics = calculate(rows, month)
    output.mkdir(parents=True, exist_ok=True)
    report = render_report(month, metrics, audit)
    message = compose(month, metrics, report, recipient, os.environ.get("REPORT_EMAIL_FROM", "demo@example.com") if deliver else "demo@example.com")
    write_csv(output / "cleaned.csv", rows, FIELDS)
    write_csv(output / "rejected.csv", audit["rejected"], ["line", "order_id", "reason"])
    write_json(output / "audit.json", audit)
    write_json(output / "metrics.json", metrics)
    (output / "report.html").write_text(report, encoding="utf-8")
    (output / "report.eml").write_bytes(message.as_bytes())
    # Save artifacts before delivery; a failed send still leaves an inspectable run.
    result = {"month": month, "metrics": metrics, "audit": audit,
              "insights": insights(metrics), "preview_rows": rows[:8],
              "email_status": "prepared", "source": source.name}
    write_json(output / "run.json", result)
    if deliver:
        identity = month + ":" + audit["source_sha256"]
        result["email_status"] = send(message, output, identity)
        write_json(output / "run.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description="Projenk synthetic business reporting")
    commands = parser.add_subparsers(dest="command", required=True)
    sample = commands.add_parser("generate", help="generate the deterministic synthetic CSV")
    sample.add_argument("--output", type=Path, default=Path("data/synthetic_orders.csv"))
    sample.add_argument("--seed", type=int, default=42)
    report = commands.add_parser("run", help="validate, calculate, report and prepare email")
    report.add_argument("--input", type=Path, default=Path("data/synthetic_orders.csv"))
    report.add_argument("--output", type=Path, default=Path("output"))
    report.add_argument("--month", default="2026-09")
    report.add_argument("--to", default=os.environ.get("REPORT_EMAIL_TO", "operations@example.com"))
    report.add_argument("--send", action="store_true", help="deliver using configured SMTP")
    args = parser.parse_args()
    try:
        if args.command == "generate":
            generate(args.output, args.seed)
            print(f"Synthetic CSV generated: {args.output}")
        else:
            result = run(args.input, args.output, args.month, args.to, args.send)
            print(f"{result['audit']['accepted_rows']} accepted / {result['audit']['rejected_rows']} rejected")
            print(f"{args.month}: ${result['metrics']['revenue']:,.2f} revenue / {result['metrics']['orders']} completed orders")
            print(f"Report: {args.output / 'report.html'} | Email: {result['email_status']}")
    except (ValueError, OSError, KeyError) as error:
        print(f"Reporting failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
