# AGENTS.md

## Current project

Projenk is an automated business reporting portfolio, rebuilt from the former todo app at the user's request. All business inputs are synthetic. The active application is the standard-library Python reporting CLI plus a static GitHub Pages portfolio.

## Stack and structure

- Python 3.11+ standard library only; `Decimal` for currency and `unittest` for tests.
- `reporting/`: synthetic generation, validation, metrics, HTML reports, email and CLI.
- `main.py`: localhost-only HTTP server; `/api/run` executes the real synthetic pipeline.
- `data/synthetic_orders.csv`: deterministic source (seed 42, July–September 2026).
- `docs/`: public HTML/CSS/JS, generated report artifacts and demo media.
- `scripts/build_site.py`: regenerates data and all public monthly reports.
- `.github/workflows/`: validation and Pages deployment plus scheduled reporting.

## Commands

- `make serve`: rebuild and serve at http://127.0.0.1:8000.
- `make demo`: rebuild public sample artifacts.
- `make test`: run Python tests and optional Node syntax check.
- `python3 -m reporting run --month 2026-09`: generate report and email preview.
- `python3 -m reporting run --month 2026-09 --send`: explicitly deliver using SMTP environment.

## Invariants

- Never represent synthetic results as real business performance.
- Browser code presents generated metrics; Python owns calculations.
- GitHub Pages cannot execute Python or SMTP. Public replay must remain labeled as a replay.
- Default runs prepare email only. Keep mail credentials and real recipient artifacts out of public source and Pages.
- Do not remove a delivery lock after an uncertain SMTP failure without checking provider delivery state.
- Treat source/audit counts as all-month counts; metrics as selected-month counts.
- Keep public URLs relative so project Pages paths work.
- Keep the UI monochrome with flat Material-style components, restrained rounding, no shadows or gradients, and accessible text contrast.
- Regenerate artifacts after changes to Python logic, seed data or report markup.
- Run meaningful pipeline tests for calculation, validation or delivery changes.
- Preserve screenshot evidence without altering its content. Refresh screenshots and tour if the UI changes materially.

## Naming

Use snake_case Python functions/files, uppercase constants and resource names that describe their outputs. Keep the zero-dependency design unless a clear requirement justifies a dependency.
