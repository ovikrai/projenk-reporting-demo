"""CSV validation and business calculations. Currency arithmetic uses Decimal."""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from .synthetic import CATEGORIES, CHANNELS, FIELDS, REGIONS, STATUSES

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def numeric(value: str) -> Decimal:
    value = value.strip()
    if not re.fullmatch(r"\$?(?:-?\d+(?:\.\d+)?|-?\d{1,3}(?:,\d{3})+(?:\.\d+)?)", value):
        raise ValueError("invalid numeric value")
    try:
        number = Decimal(value.replace("$", "").replace(",", ""))
    except InvalidOperation as error:
        raise ValueError("invalid numeric value") from error
    if not number.is_finite():
        raise ValueError("non-finite numeric value")
    return number


def clean_csv(path: Path):
    accepted, rejected, changes = [], [], []
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError("CSV header must exactly match: " + ",".join(FIELDS))
        for line, original in enumerate(reader, start=2):
            if None in original or any(value is None for value in original.values()):
                rejected.append({"line": line, "order_id": original.get("order_id", ""), "reason": "wrong column count"})
                continue
            row = {key: value.strip() for key, value in original.items()}
            for field in ("category", "region", "channel"):
                row[field] = row[field].title()
            row["status"] = row["status"].lower()
            try:
                if not row["order_id"]:
                    raise ValueError("missing order_id")
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", row["order_id"]):
                    raise ValueError("invalid order_id")
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["order_date"]):
                    raise ValueError("invalid ISO order_date")
                date.fromisoformat(row["order_date"])
                for field, allowed in [("category", CATEGORIES), ("region", REGIONS),
                                       ("channel", CHANNELS), ("status", STATUSES)]:
                    if row[field] not in allowed:
                        raise ValueError("invalid " + field)
                quantity = numeric(row["quantity"])
                if quantity != quantity.to_integral_value() or not 1 <= quantity <= 10000:
                    raise ValueError("quantity must be an integer from 1 to 10000")
                row["quantity"] = str(int(quantity))
                for field in ("unit_price", "unit_cost", "discount_pct"):
                    number = numeric(row[field])
                    if number < 0:
                        raise ValueError(field + " must be nonnegative")
                    if field == "discount_pct" and number > 100:
                        raise ValueError("discount_pct must be between 0 and 100")
                    if field != "discount_pct" and (number > 1000000 or money(number) != number):
                        raise ValueError(field + " must have at most 2 decimal places and be <= 1000000")
                    row[field] = str(money(number)) if field != "discount_pct" else format(number.normalize(), "f")
                if row["order_id"] in seen:
                    raise ValueError("duplicate order_id (first valid row retained)")
            except (ValueError, InvalidOperation) as error:
                rejected.append({"line": line, "order_id": row["order_id"], "reason": str(error)})
                continue
            seen.add(row["order_id"])
            changed = [key for key in FIELDS if row[key] != original[key]]
            if changed:
                changes.append({"line": line, "order_id": row["order_id"], "fields": changed})
            accepted.append(row)
    raw_count = len(accepted) + len(rejected)
    if not accepted:
        raise ValueError("No valid records remain after validation")
    audit = {"raw_rows": raw_count, "accepted_rows": len(accepted),
             "rejected_rows": len(rejected), "normalized_rows": len(changes),
             "acceptance_rate": round(len(accepted) / raw_count * 100, 2),
             "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
             "reasons": dict(Counter(item["reason"] for item in rejected)),
             "rejected": rejected, "changes": changes}
    return accepted, audit


def summarize(rows):
    completed = [row for row in rows if row["status"] == "completed"]
    revenue = Decimal(0)
    costs = Decimal(0)
    groups = {"categories": defaultdict(lambda: {"revenue": Decimal(0), "orders": 0}),
              "channels": defaultdict(lambda: {"revenue": Decimal(0), "orders": 0}),
              "daily": defaultdict(lambda: {"revenue": Decimal(0), "orders": 0})}
    for row in completed:
        net = money(Decimal(row["quantity"]) * Decimal(row["unit_price"]) *
                    (1 - Decimal(row["discount_pct"]) / 100))
        cost = Decimal(row["quantity"]) * Decimal(row["unit_cost"])
        revenue += net
        costs += cost
        for group, key in [("categories", "category"), ("channels", "channel"), ("daily", "order_date")]:
            groups[group][row[key]]["revenue"] += net
            groups[group][row[key]]["orders"] += 1
    refunded = sum(row["status"] == "refunded" for row in rows)
    fulfilled = len(completed) + refunded
    result = {"revenue": float(revenue), "orders": len(completed), "cogs": float(costs),
              "gross_profit": float(revenue - costs),
              "margin": round(float((revenue - costs) / revenue * 100), 2) if revenue else 0,
              "aov": float(money(revenue / len(completed))) if completed else 0,
              "refund_rate": round(refunded / fulfilled * 100, 2) if fulfilled else 0,
              "refunded_orders": refunded,
              "cancelled_orders": sum(row["status"] == "cancelled" for row in rows),
              "valid_rows": len(rows)}
    for name, grouped in groups.items():
        result[name] = [{"name": key, "revenue": float(value["revenue"]), "orders": value["orders"]}
                        for key, value in sorted(grouped.items(),
                            key=lambda item: item[0] if name == "daily" else -item[1]["revenue"])]
    return result


def calculate(rows, month: str):
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError("month must use YYYY-MM format")
    first = date.fromisoformat(month + "-01")
    previous = date(first.year - 1, 12, 1) if first.month == 1 else date(first.year, first.month - 1, 1)
    selected = [row for row in rows if row["order_date"].startswith(month)]
    if not selected:
        raise ValueError("No valid records for " + month)
    prior = [row for row in rows if row["order_date"].startswith(previous.strftime("%Y-%m"))]
    current = summarize(selected)
    comparison = summarize(prior) if prior else None
    current["previous"] = comparison
    current["deltas"] = {key: round((current[key] - comparison[key]) / comparison[key] * 100, 2)
                         if comparison and comparison[key] else None
                         for key in ("revenue", "orders", "aov")}
    current["deltas"]["margin"] = round(current["margin"] - comparison["margin"], 2) if comparison else None
    return current


def write_csv(path: Path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
