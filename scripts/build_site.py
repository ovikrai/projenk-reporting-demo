"""Build all public demo artifacts from the same Python pipeline as local runs."""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reporting.__main__ import run
from reporting.pipeline import write_json
from reporting.synthetic import generate


def build():
    source = ROOT / "data/synthetic_orders.csv"
    generate(source)
    (ROOT / "docs/data").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, ROOT / "docs/data/synthetic_orders.csv")
    periods = ["2026-09", "2026-08", "2026-07"]
    for period in periods:
        run(source, ROOT / "docs/reports" / period, period)
    write_json(ROOT / "docs/data/manifest.json", {
        "periods": periods, "default_period": periods[0], "dataset": "synthetic_orders.csv",
        "seed": 42, "currency": "USD", "synthetic": True,
        "repository": "https://github.com/ovikrai/projenk-reporting-demo"})
    (ROOT / "docs/.nojekyll").touch()
    print("Built GitHub Pages portfolio and three reproducible reports in docs/")


if __name__ == "__main__":
    build()
