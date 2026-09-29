"""Megashop — the most complex fixture (6 apps, 3 frameworks, 2 ORMs, 29 endpoints). Enforces that
the reviewer reproduces GROUND_TRUTH.md across all 7 edges with no hallucinations or skips."""
import importlib.util
import os

# load under a unique name — torture also ships a check.py (see the note in test_torture.py).
_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "megashop", "check.py")
_spec = importlib.util.spec_from_file_location("megashop_check", _p)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def test_megashop_7_edges_no_hallucinations_no_skips():
    halluc, skips, rows = check.evaluate()
    assert rows, "no endpoints discovered — fixture wiring broken"
    assert halluc == [], "reviewer HALLUCINATED facts:\n" + "\n".join(halluc)
    assert skips == [], "reviewer SKIPPED facts or mismatched an edge:\n" + "\n".join(skips)


def test_megashop_spans_three_frameworks():
    from extractor.analyzer import analyze_repo
    routes = {e.route for e in analyze_repo(check.HERE)}
    assert any(r.startswith("orders/") for r in routes)       # Django DRF (urls.py)
    assert any(r.startswith("/analytics/") for r in routes)    # Flask blueprint
    assert any(r.startswith("/gw/") for r in routes)           # FastAPI router
