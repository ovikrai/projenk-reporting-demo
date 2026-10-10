PYTHON ?= python3

.PHONY: demo serve test report send

demo:
	$(PYTHON) scripts/build_site.py

serve: demo
	$(PYTHON) main.py

test:
	$(PYTHON) -m unittest discover -s tests -v
	reporting_node=$$(command -v node); if [ -n "$$reporting_node" ]; then "$$reporting_node" --check docs/assets/app.js; fi

report:
	$(PYTHON) -m reporting run --month 2026-09

send:
	$(PYTHON) -m reporting run --month 2026-09 --send
