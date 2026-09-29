"""Ground-truth checker for the torture fixture — measures HALLUCINATION (facts the extractor
invented that aren't in the code) and SKIPPING (facts truly in the code that it missed).

Ground truth is authored from what each endpoint ACTUALLY does (I wrote the code, so I know). For
each endpoint:
  expect_db      : the exact set of SQL tables the extractor SHOULD report (kind-agnostic, table level)
  known_miss     : tables the code truly touches but the extractor is *accepted* to miss (documented
                   blindspot, e.g. a dynamic model bound at a call site, or a custom-manager method
                   body) — a miss here is NOT a bug, but it IS reported so the blindspot stays honest
  forbidden      : substrings that must NEVER appear in a db fact (hallucination tripwires)
  cache/async/external/pii : expected presence of that edge
  ext_known_miss : an external call the extractor is accepted to miss (e.g. an SDK verb it doesn't know)

Run:  python3 check.py        (from anywhere; prints a report + exit code)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))  # reviewer2 root
from extractor.analyzer import analyze_repo  # noqa: E402

# Ground truth for the 3-app mixed-architecture project (ads = cms-style, subscriptions =
# nested api/ layout, portal = standard users layout). Authored from what each endpoint truly does.
GT = {
    # --- ads (cms-style: controllers → helpers → raw-SQL modules; FK collision; manager) ---
    "CampaignListView":             dict(db={"ad_campaigns"}),
    "CampaignExportView":           dict(db={"ad_campaigns", "ad_delivery_logs"}),  # CTE
    "CampaignImportView":           dict(db={"ad_campaigns", "ad_audit_log"}),                # manager follow
    "CampaignCreateView":           dict(db={"ad_campaigns"}),                                # serializer.save
    "CampaignRawView":              dict(db={"ad_campaigns"}),                                # Model.objects.raw()
    "EntityInteractionsExportView": dict(db={"ad_target_slice", "ad_target_entity_slice",
                                             "users", "cities"}, pii=True),   # raw SQL + raw-SQL-column PII
    "EntityMetricsView":            dict(db={"ad_target_entity_slice", "ad_target"}),  # FK
    "AuditPurgeView":               dict(db={"ad_audit_log"}),                                     # raw DELETE
    # --- subscriptions (nested api/<feature>, class repo, cache, CRM/payment egress) ---
    "SubscriptionLandingView":         dict(db={"products"}, cache=True),
    "SubscriptionSummaryView":         dict(db={"orders", "products"}),                               # Service() + m2m trap
    "SubscriptionDashboardView":       dict(db={"orders", "order_items"}),                            # deep repo chain
    "PurchaseCheckView":            dict(db={"orders", "campaign_pages", "products"}, cache=True),
    "SubscriptionPurchaseView":        dict(db={"leads", "orders", "payments"}, external=True, pii=True),
    "RegistrationView":             dict(db={"leads"}, external=True, pii=True),                   # CRM + PII
    # --- portal (users-style: celery, threading, dynamic model, boto3, raw SQL, traps) ---
    "UserProfileView":              dict(db={"users"}, pii=True),                                  # get_object_or_404
    "NotifyView":                   dict(db={"users"}, async_=True, pii=True),                     # celery + email
    "WebhookView":                  dict(db=set(), async_=True),                                   # threading
    "ArticleFetchView":             dict(db={"articles"}, forbidden=["model:"]),                   # dynamic model bind
    "SearchView":                   dict(db={"articles", "domains"}),                              # raw SQL JOIN
    "MediaExportView":              dict(db={"users"}, external=True, pii=True),                   # boto3 S3 (⚠ co-occur)
    "CacheOnlyView":                dict(db=set(), cache=True),                                    # TRAP: cache.delete
    "UpsertView":                   dict(db={"users"}),                                            # get_or_create
    "DynamicReportView":            dict(db=set(), forbidden=["{", "LIMIT"]),                       # TRAP: f-string
    "TrapView":                     dict(db={"users"}, pii=True, forbidden=["secret_table"]),      # log/session/dict
    # --- reporting (Flask + SQLAlchemy — different framework AND ORM) ---
    "metrics_list":                 dict(db={"metrics"}),                                          # session.query(Model)
    "summary":                      dict(db={"metrics"}),                                          # Model.query (declarative)
    "ingest":                       dict(db={"visits"}, external=True, pii=True),                  # session.add + egress
    "bulk_ingest":                  dict(db={"visits"}),                                           # session.execute(insert)
}


def tables_of(ep):
    out = set()
    for it in ep.e3_db_tables.items:
        name = it.split(" @ ")[0].split(":")[0].strip()
        out.add(ep.tables[name]["table"] if name in ep.tables else name)
    return out


def evaluate():
    """Compare extractor output vs ground truth. Returns (halluc, skips, blindspots, rows)."""
    eps = {e.handler: e for e in analyze_repo(HERE)}
    skips, halluc, blindspots, rows = [], [], [], []
    for handler, gt in GT.items():
        ep = eps.get(handler)
        if ep is None:
            skips.append(f"{handler}: endpoint NOT DISCOVERED")
            rows.append((handler, "— not found —", ""))
            continue
        found = tables_of(ep)
        expect = gt.get("db", set())
        known = gt.get("known_miss", set())
        forbidden = gt.get("forbidden", [])

        missing = expect - found
        extra = found - expect - known - {"<instance>"} if "<instance>" not in expect else found - expect - known
        raw = " ".join(ep.e3_db_tables.items)                    # hallucination tripwires
        tripped = [f for f in forbidden if f in raw]
        km_hit = known - found

        if missing:
            skips.append(f"{handler}: SKIPPED tables {sorted(missing)} (found {sorted(found)})")
        if extra:
            halluc.append(f"{handler}: HALLUCINATED tables {sorted(extra)}")
        if tripped:
            halluc.append(f"{handler}: forbidden pattern {tripped} in db facts")
        if km_hit:
            blindspots.append(f"{handler}: {sorted(km_hit)} (documented blindspot)")

        flags = []
        def present(edge):
            e = getattr(ep, edge)
            return e.status != "n/a" and bool(e.items)
        for key, edge, name in [("cache", "e7_cache", "cache"), ("async_", "e5_async", "async"),
                                ("external", "e4_external", "ext"), ("pii", "e6_pii", "pii")]:
            if gt.get(key):
                if not present(edge):
                    skips.append(f"{handler}: {name} edge MISSED")
                flags.append(name + ("✓" if present(edge) else "✗"))
        if gt.get("ext_known_miss"):
            hit = gt["ext_known_miss"] in " ".join(ep.e4_external.items)
            blindspots.append(f"{handler}: {gt['ext_known_miss']} {'(FOUND!)' if hit else '(documented miss)'}")

        ok = "✓" if not missing and not extra and not tripped else "✗"
        rows.append((handler, ok + " " + str(sorted(found)), " ".join(flags)))
    return halluc, skips, blindspots, rows


def main():
    halluc, skips, blindspots, rows = evaluate()
    print(f"{'endpoint':22} {'db recall':>28}  flags")
    for handler, recall, flags in rows:
        print(f"{handler:22} {recall:>28}  {flags}")
    print("\n" + "=" * 70)
    print(f"HALLUCINATIONS (invented facts): {len(halluc)}")
    for h in halluc: print("  ✗", h)
    print(f"SKIPS (missed facts that should be found): {len(skips)}")
    for s in skips: print("  ✗", s)
    print(f"\nDocumented blindspots (accepted misses, NOT failures): {len(blindspots)}")
    for k in blindspots: print("  ·", k)
    ok = not halluc and not skips
    print("\nRESULT:", "PASS — no hallucinations, no unexpected skips ✅" if ok else "FAIL — see above ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
