"""The 'ultimate test case' — a heavily-abstracted DRF fixture with labeled ground truth, run to
prove the extractor neither HALLUCINATES (invents facts absent from the code) nor SKIPS (misses
facts truly present). See tests/fixtures/torture/{views.py,check.py}. Fixture = tests/fixtures/torture,
which SKIP_DIRS would prune if the repo root were analyzed, so the checker analyzes that dir directly.
"""
import importlib.util
import os

# load THIS fixture's check.py under a unique module name — both torture and megashop ship a check.py,
# and a plain `import check` would collide in sys.modules (whichever test runs first wins).
_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "torture", "check.py")
_spec = importlib.util.spec_from_file_location("torture_check", _p)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def test_no_hallucinations_and_no_skips():
    halluc, skips, blindspots, rows = check.evaluate()
    assert rows, "no endpoints discovered — fixture wiring broken"
    assert halluc == [], "extractor HALLUCINATED facts absent from the code:\n" + "\n".join(halluc)
    assert skips == [], "extractor SKIPPED facts truly in the code:\n" + "\n".join(skips)


def test_no_documented_blindspots_remain():
    """The three original accepted misses (dynamic-model param, custom-manager body, SDK verb) were
    all fixed — the fixture now expects full resolution, so there should be ZERO accepted misses. If
    this regresses, a fix was lost."""
    _, _, blindspots, _ = check.evaluate()
    assert blindspots == [], "a blindspot reappeared (a fix regressed):\n" + "\n".join(blindspots)
