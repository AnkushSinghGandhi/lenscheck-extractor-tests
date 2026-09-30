"""Interprocedural DB-read tracing: a read reached through a pass-through delegator must be found
(recall), and a call to a nested closure must not bind to a same-named module function elsewhere
(precision). Regression for the `clients/entity-search` case that missed nested reads."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "extractor"))
from analyzer import analyze_repo, to_dict  # noqa: E402


def _models_read(root):
    for ep in analyze_repo(root):
        d = to_dict(ep)
        if "/thing" in (d.get("route") or ""):
            return {i.split(":read")[0].split(":write")[0] for i in (d.get("e3_db_tables") or {}).get("items", [])}
    return set()


def _thing_ep(root):
    for ep in analyze_repo(root):
        if "/thing" in (ep.route or ""):
            return ep
    return None


def _deep_chain_repo(hops_read):
    """A handler → l1 → l2 → … chain where hop i runs `hops_read[i]`. Returns the temp repo dir."""
    d = tempfile.mkdtemp()
    body = ["from fastapi import FastAPI", "app = FastAPI()", "@app.get('/thing')",
            "def handler():", "    return l0()"]
    for i, stmt in enumerate(hops_read):
        nxt = f"    return l{i+1}()" if i + 1 < len(hops_read) else "    return 1"
        body += [f"def l{i}():", f"    {stmt}", nxt]
    with open(os.path.join(d, "app.py"), "w") as f:
        f.write("\n".join(body) + "\n")
    return d


def test_adaptive_depth_reaches_deep_new_facts():
    """5 fact-bearing hops, each reading a DISTINCT model. The old flat depth-3 cap stopped at the
    third — findings-driven follow keeps descending while every hop still reveals something new."""
    root = _deep_chain_repo([f"Model{c}.objects.all()" for c in "ABCDE"])
    models = _models_read(root)
    assert {"ModelA", "ModelB", "ModelC", "ModelD", "ModelE"} <= models, models  # D,E are depth 4,5
    ep = _thing_ep(root)
    assert ep.follow_depth >= 5                    # observability: reports how deep data actually went
    assert ep.follow_stop == "dried_out"           # natural, complete stop (never hit a cap)


def test_adaptive_depth_dries_out_and_still_reports_the_fact():
    """A chain that keeps re-reading the SAME model teaches nothing new past hop 1 → the branch
    brakes (dried_out) instead of walking to the ceiling; the one real read is still reported."""
    root = _deep_chain_repo(["Same.objects.all()"] * 6)
    models = _models_read(root)
    assert "Same" in models
    assert _thing_ep(root).follow_stop == "dried_out"


def test_adaptive_depth_ceiling_is_labelled_not_silently_complete():
    """A genuinely-productive chain deeper than DEPTH_CEILING is cut at the cap and MUST report
    'ceiling' (possibly-incomplete) — never a silent 'dried_out' that would imply completeness."""
    root = _deep_chain_repo([f"M{i}.objects.all()" for i in range(12)])   # 12 distinct models
    ep = _thing_ep(root)
    from analyzer import DEPTH_CEILING
    assert ep.follow_stop == "ceiling"                 # honest blindspot, not a false 'complete'
    assert ep.follow_depth == DEPTH_CEILING            # reached the cap while still learning


def test_custom_manager_method_is_followed():
    """`Model.objects.<custom>()` resolves the model's Manager class and follows its body, so a
    write hidden in the manager method is surfaced — not just the fallback read at the call site."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "app.py"), "w") as f:
        f.write("from fastapi import FastAPI\napp = FastAPI()\n"
                "@app.get('/thing')\ndef handler():\n    return Thing.objects.bulk_thing([])\n"
                "class ThingManager:\n"
                "    def bulk_thing(self, rows):\n        AuditRow.objects.create(x=1)\n"
                "class Thing:\n    objects = ThingManager()\n")
    assert "AuditRow" in _models_read(d)      # the write inside the manager body is found


def test_instance_variable_helper_method_is_followed():
    """`flow = mod.Helper(req); flow.run()` — a helper stored in a variable — is resolved to its class
    and followed into `Helper.run`, where controllers hide the real DB writes (example-backend)."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "helpers.py"), "w") as f:
        f.write("class ProfileFlow:\n"
                "    def __init__(self, req):\n        pass\n"
                "    def run(self):\n        User.objects.filter(id=1).update(name='x')\n")   # write hidden here
    with open(os.path.join(d, "app.py"), "w") as f:
        f.write("from fastapi import FastAPI\napp = FastAPI()\nimport helpers\n"
                "@app.get('/thing')\ndef handler(req):\n"
                "    flow = helpers.ProfileFlow(req)\n"        # instance = module.Helper(...)
                "    return flow.run()\n"                      # instance.method() → must follow
                "class User:\n    pass\n")
    facts = [i.split(" @ ")[0] for i in _thing_ep(d).e3_db_tables.items]
    assert any(f.startswith("User:write") for f in facts), facts   # the helper's write is surfaced


def test_manager_method_self_create_is_a_write():
    """`Model.objects.<custom>()` follows the Manager, and `self.create()` inside it is a WRITE to the
    managed model (not the fallback read the call site would guess). No spurious read is emitted."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "app.py"), "w") as f:
        f.write("from fastapi import FastAPI\napp = FastAPI()\n"
                "@app.get('/thing')\ndef handler():\n    return Thing.objects.bulk_thing([])\n"
                "class ThingManager:\n"
                "    def bulk_thing(self, rows):\n        self.create(x=1)\n"
                "class Thing:\n    objects = ThingManager()\n")
    ep = _thing_ep(d)
    facts = [i.split(" @ ")[0] for i in ep.e3_db_tables.items]
    assert any(f.startswith("Thing:write") for f in facts)       # self.create → managed model write
    assert not any(f.startswith("Thing:read") for f in facts)    # no spurious fallback read


def test_helper_param_binds_to_passed_model():
    """A helper `def f(model): model.objects.all()` called as `f(Widget)` resolves to Widget — the
    param is bound to the model passed at the call site, not left as an anonymous <instance>."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "app.py"), "w") as f:
        f.write("from fastapi import FastAPI\napp = FastAPI()\n"
                "@app.get('/thing')\ndef handler():\n    return fetch_all(Widget)\n"
                "def fetch_all(model):\n    return list(model.objects.all())\n"
                "class Widget:\n    pass\n")
    models = _models_read(d)
    assert "Widget" in models                 # bound to the passed model
    assert "model" not in models               # never the literal param name


def test_adaptive_depth_terminates_on_recursion():
    """Mutual recursion (a→b→a) and self-recursion must not hang or double-count — the `followed`
    set stops a callee being re-entered. Both real reads are still found exactly once."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "app.py"), "w") as f:
        f.write("from fastapi import FastAPI\napp = FastAPI()\n"
                "@app.get('/thing')\ndef handler():\n    return a()\n"
                "def a():\n    Ay.objects.all()\n    return b()\n"
                "def b():\n    Bee.objects.all()\n    return a()\n")   # b → a cycle
    models = _models_read(d)
    assert models == {"Ay", "Bee"}                     # both found, walk terminated (no hang)


def test_delegator_and_closure_collision():
    d = tempfile.mkdtemp()
    # handler → facade (pure delegator, no facts) → worker (reads ModelA) → deep (reads ModelB)
    with open(os.path.join(d, "app.py"), "w") as f:
        f.write(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            "@app.get('/thing')\n"
            "def handler():\n"
            "    return facade()\n"
            "def facade():\n"                       # delegator — should be a *free* hop
            "    return worker()\n"
            "def worker():\n"
            "    ModelA.objects.filter(id=1)\n"      # recovered only if the delegator was free
            "    def resolve():\n"                   # a LOCAL closure named like the global below
            "        return 1\n"
            "    resolve()\n"                        # must NOT bind to other.resolve()
            "    return deep()\n"
            "def deep():\n"
            "    ModelB.objects.all()\n"
        )
    # a same-named global in another module that reads a table we must NOT attribute to /thing
    with open(os.path.join(d, "other.py"), "w") as f:
        f.write("def resolve():\n    ModelC.objects.all()\n")

    models = _models_read(d)
    assert "ModelA" in models, f"delegator hop lost the read: {models}"   # recall (A)
    assert "ModelB" in models, f"deep read lost: {models}"                # recall (A, depth)
    assert "ModelC" not in models, f"closure bound to global resolve(): {models}"  # precision (B)


def test_same_name_facade_is_followed():
    """A facade method `Helper.load()` that delegates to a module `load()` of the *same* name must
    still be followed — the root fn's own name is not 'local' (regression: cm-directory went empty)."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "app.py"), "w") as f:
        f.write(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            "@app.get('/thing')\n"
            "def handler():\n"
            "    return Helper.load()\n"
            "class Helper:\n"
            "    @staticmethod\n"
            "    def load():\n"
            "        return load()\n"                  # same-name delegation to the module fn below
            "def load():\n"
            "    ModelD.objects.all()\n"
        )
    models = _models_read(d)
    assert "ModelD" in models, f"same-name facade dropped: {models}"


def test_get_object_or_404_reads_real_model():
    """get_object_or_404(Model, …) is a genuine read (Django shortcut runs Model.objects.get)."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "app.py"), "w") as f:
        f.write(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            "@app.get('/thing')\n"
            "def handler(pk):\n"
            "    obj = get_object_or_404(RealModel, pk=pk)\n"
            "    return obj\n"
        )
    assert "RealModel" in _models_read(d)


def test_get_object_or_404_skips_local_model_alias():
    """A runtime model *alias* (`M = apps.get_model(...)` / `M = RealModel`) passed to
    get_object_or_404 must NOT be credited as a table literally named `M` — no such table exists.
    Regression for the `Alias` phantom found by the gain audit."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "app.py"), "w") as f:
        f.write(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            "@app.get('/thing')\n"
            "def handler(pk):\n"
            "    Alias = apps.get_model('app', 'Thing')\n"     # a Capitalized *variable*, not a model class
            "    obj = get_object_or_404(Alias, pk=pk)\n"
            "    return obj\n"
        )
    assert "Alias" not in _models_read(d), "credited a phantom table named after a local alias var"


def test_sibling_branch_not_starved_by_shared_seen():
    """A later sibling branch that re-reads an earlier sibling's shallow models must STILL descend to
    its own unique deep read — novelty is per-branch, not per-endpoint. Regression for the shared-`seen`
    silent recall loss (adaptive dropped a real table while labelling the endpoint complete)."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "app.py"), "w") as f:
        f.write(
            "from fastapi import FastAPI\napp = FastAPI()\n"
            "@app.get('/thing')\n"
            "def handler():\n    a_branch(); b_branch(); return 1\n"
            "def a_branch(): Dup1.objects.all(); return a2()\n"
            "def a2():       Dup2.objects.all(); return a3()\n"
            "def a3():       Dup3.objects.all(); return 1\n"
            "def b_branch(): Dup1.objects.all(); return b2()\n"        # re-reads a-branch's models
            "def b2():       Dup2.objects.all(); return b3()\n"
            "def b3():       Dup3.objects.all(); return b4()\n"
            "def b4():       SecretLedger.objects.all(); return 1\n")  # UNIQUE deep read at depth 4
    ep = _thing_ep(d)
    tabs = {i.split(" @ ")[0].split(":")[0] for i in ep.e3_db_tables.items}
    assert "SecretLedger" in tabs, f"a sibling branch was starved by shared `seen`: {sorted(tabs)}"
    assert ep.follow_stop == "dried_out"


def test_leaf_at_ceiling_stays_complete_not_falsely_flagged():
    """A COMPLETE walk whose deepest fact-frame sits exactly at DEPTH_CEILING but is a LEAF (nothing left
    to follow) must stay 'dried_out'; only a genuinely deeper chain that is really cut may report
    'ceiling'. Regression for the false-positive ceiling/budget label."""
    from analyzer import DEPTH_CEILING
    leaf = _thing_ep(_deep_chain_repo([f"C{i}.objects.all()" for i in range(DEPTH_CEILING)]))
    assert leaf.follow_stop == "dried_out", f"leaf at ceiling mislabelled {leaf.follow_stop!r}"
    cut = _thing_ep(_deep_chain_repo([f"D{i}.objects.all()" for i in range(DEPTH_CEILING + 2)]))
    assert cut.follow_stop == "ceiling", f"a genuine cut must stay flagged, got {cut.follow_stop!r}"


def test_name_collision_resolves_independent_of_walk_order():
    """Two same-named helpers in different apps must resolve to the SAME one regardless of filesystem
    walk order — else the extractor emits different tables across machines/CI checkouts. Regression for
    the unsorted os.walk + `_pick` first-candidate tie."""
    import analyzer as A
    d = tempfile.mkdtemp()
    for app, mdl in [("alpha", "AlphaModel"), ("beta", "BetaModel")]:
        os.makedirs(os.path.join(d, "apps", app))
        with open(os.path.join(d, "apps", app, "helpers.py"), "w") as f:
            f.write(f"def shared_helper():\n    {mdl}.objects.create(x=1)\n")
    os.makedirs(os.path.join(d, "apps", "main"))
    with open(os.path.join(d, "apps", "main", "views.py"), "w") as f:
        f.write("from fastapi import FastAPI\napp = FastAPI()\n"
                "@app.get('/thing')\ndef handler():\n    return shared_helper()\n")

    def tabs():
        return {i.split(" @ ")[0].split(":")[0] for i in _thing_ep(d).e3_db_tables.items}

    normal = tabs()
    orig = A.os.walk
    try:                # force the opposite traversal order; sorted _iter_py must neutralise it
        A.os.walk = lambda p: [(dp, sorted(dn, reverse=True), sorted(fn, reverse=True)) for dp, dn, fn in orig(p)]
        flipped = tabs()
    finally:
        A.os.walk = orig
    assert normal == flipped, f"walk order changed name resolution: {normal} vs {flipped}"
