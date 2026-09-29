# lenscheck-extractor-tests

Ground-truth test suite for the [lenscheck extractor](https://github.com/AnkushSinghGandhi/lenscheck-semantic-reviewer).

The extractor statically analyses a Python backend and produces a facts graph — routes, auth, DB reads/writes, external calls, async dispatch, PII. This repo proves it neither hallucinates facts that aren't there nor misses facts that are.

## How it works

The extractor lives in the main repo (`lenscheck-semantic-reviewer/extractor/`). CI pulls it fresh on every run — no copy is committed here.

```
lenscheck-semantic-reviewer   ← extractor source (the thing being tested)
lenscheck-extractor-tests     ← fixtures + tests (this repo)
```

## Fixtures

| Fixture | Apps | Frameworks | ORMs | Endpoints |
|---------|------|-----------|------|-----------|
| `tests/fixtures/blog/` | 1 | Django DRF | Django ORM | ~5 |
| `tests/fixtures/torture/` | 4 (ads, subscriptions, portal, reporting) | Django DRF + Flask | Django ORM + SQLAlchemy | 24 |
| `tests/fixtures/megashop/` | 6 (accounts, catalog, orders, billing, analytics, gateway) | Django DRF + Flask + FastAPI | Django ORM + SQLAlchemy | 29 |

Each fixture ships a hand-authored `GROUND_TRUTH.md` and a `check.py` that compares extractor output against it. A mismatch is either a hallucination (invented fact) or a skip (missed fact) — both are hard failures.

## Running locally

```bash
# clone both repos side by side
git clone https://github.com/AnkushSinghGandhi/lenscheck-semantic-reviewer
git clone https://github.com/AnkushSinghGandhi/lenscheck-extractor-tests

# copy the extractor in
cp -r lenscheck-semantic-reviewer/extractor lenscheck-extractor-tests/extractor

# run
cd lenscheck-extractor-tests
pip install pytest
pytest
```

## CI

GitHub Actions runs on every push to `main` in both this repo and the main extractor repo. The workflow checks out the extractor from `lenscheck-semantic-reviewer`, copies it here, and runs `pytest`.
