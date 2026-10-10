"""Generate repeatable, deliberately imperfect order data. No real customer data."""
import csv
import random
from calendar import monthrange
from pathlib import Path

FIELDS = ["order_id", "order_date", "category", "region", "channel", "quantity",
          "unit_price", "unit_cost", "discount_pct", "status"]
CATEGORIES = {"Home & Living": (89, 36), "Electronics": (179, 108),
              "Apparel": (64, 24), "Accessories": (39, 12)}
REGIONS = ("North", "South", "East", "West")
CHANNELS = ("Online", "Retail", "Wholesale")
STATUSES = ("completed", "refunded", "cancelled")


def generate(path: Path, seed: int = 42) -> None:
    rng = random.Random(seed)
    rows = []
    for month, count in [(7, 230), (8, 265), (9, 310)]:
        for i in range(count):
            category = rng.choices(list(CATEGORIES), weights=[35, 28, 24, 13])[0]
            price, cost = CATEGORIES[category]
            row = dict(zip(FIELDS, [f"PJ-{month:02d}-{i+1:04d}",
                f"2026-{month:02d}-{rng.randint(1, monthrange(2026, month)[1]):02d}",
                category, rng.choice(REGIONS),
                rng.choices(CHANNELS, weights=[58, 30, 12])[0],
                rng.choices([1, 2, 3, 4], weights=[50, 28, 17, 5])[0],
                f"{price * rng.choice([1, 1, 1.15, .9]):.2f}", f"{cost:.2f}",
                rng.choice([0, 0, 0, 5, 10, 15]),
                rng.choices(STATUSES, weights=[91, 6, 3])[0]]))
            if i % 31 == 0:
                row["channel"] = " " + row["channel"].lower() + " "
            if i % 43 == 0:
                row["status"] = row["status"].upper()
            if i % 57 == 0:
                row["unit_price"] = "$" + row["unit_price"]
            rows.append(row)
            if i in (20, 85, 150):
                rows.append(row.copy())
        for j, (field, value) in enumerate([
            ("order_date", "2026-09-31"), ("quantity", "-2"),
            ("unit_price", "not-a-number"), ("category", ""),
            ("discount_pct", "150"), ("status", "pending")
        ]):
            bad = dict(row, order_id=f"BAD-{month}-{j}", **{field: value})
            rows.append(bad)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
