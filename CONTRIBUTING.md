# Contributing

Issues and pull requests are welcome.

- `pip install -e ".[dev]"`, then `ruff check . && mypy && pytest` must pass. Coverage
  below 100% fails the run.
- Money stays `Decimal`, masses stay whole kilograms. A new rule in `rules.json` comes with a test that makes it fire and one that keeps it quiet.
- A new kind of check is a function in `engine.py` plus its entry in `CHECKS`.
