"""7-edge ground-truth checker for megashop — verifies the reviewer reproduces GROUND_TRUTH.md
exactly (0 hallucinations, 0 skips) across db / external / async / cache / pii / auth."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
from extractor.analyzer import analyze_repo  # noqa: E402

# per endpoint: db table set + expected edges. auth: 'closed' (real permission) / 'open' (AllowAny or
# []) / 'none' (no marker → ?). pii: expected status. forbidden: substrings that must never appear.
GT = {
    # orders
    "OrderListView":       dict(db={"orders"}, cache=True, auth="closed"),
    "OrderCreateView":     dict(db={"orders", "order_items"}, async_=True, auth="closed"),
    "OrderDetailView":     dict(db={"orders", "order_items", "customers"}, pii="?", auth="closed"),
    "OrderImportView":     dict(db={"orders", "audit_log"}, auth="closed"),
    "OrderCreateFormView": dict(db={"orders"}, auth="closed"),
    # billing
    "InvoiceExportView":   dict(db={"billing_invoices", "orders", "customers"}, pii="⚠", auth="closed"),
    "ChargeView":          dict(db={"orders", "customers", "billing_payments"}, external=True, async_=True, pii="✓", auth="closed"),
    "RevenueReportView":   dict(db={"orders", "billing_payments"}, forbidden=["recent"], auth="closed"),
    "RefundView":          dict(db={"billing_refunds"}, external=True, auth="closed"),
    "PaymentWebhookView":  dict(db={"billing_payments"}, auth="open"),
    # accounts
    "ProfileView":         dict(db={"accounts"}, pii="⚠", auth="open"),
    "UpdateProfileView":   dict(db={"accounts"}, pii="n/a", auth="closed"),   # filter().update() is a pure WRITE — no read, no PII
    "NotifyView":          dict(db={"accounts"}, async_=True, pii="✓", auth="closed"),
    "AccountWebhookView":  dict(db=set(), async_=True, auth="open"),
    "ArticleFetchView":    dict(db={"articles"}, forbidden=["model:"], auth="closed"),
    "SearchView":          dict(db={"accounts", "profiles"}, auth="closed"),
    "TrapView":            dict(db={"accounts"}, pii="✓", cache=True, forbidden=["secret_table"], auth="closed"),
    # catalog
    "CatalogListView":     dict(db={"catalog_items"}, cache=True, auth="closed"),
    "CategorySummaryView": dict(db={"categories", "catalog_items"}, auth="closed"),
    "CacheClearView":      dict(db=set(), cache=True, auth="closed"),
    # analytics (Flask + SQLAlchemy)
    "metrics_list":        dict(db={"metrics"}, auth="none"),
    "summary":             dict(db={"metrics"}, auth="closed"),
    "ingest":              dict(db={"visits"}, external=True, pii="✓", auth="none"),
    "export_reports":      dict(db={"reports"}, external=True, auth="none"),
    "email_report":        dict(db=set(), external=True, auth="none"),
    # gateway (FastAPI)
    "status":              dict(db=set(), auth="none"),
    "proxy_order":         dict(db=set(), external=True, auth="closed"),
    "dispatch":            dict(db=set(), async_=True, auth="none"),
    "gw_webhook":          dict(db=set(), external=True, auth="none"),
}


def tables_of(ep):
    out = set()
    for it in ep.e3_db_tables.items:
        name = it.split(" @ ")[0].split(":")[0].strip()
        out.add(ep.tables[name]["table"] if name in ep.tables else name)
    return out


def auth_kind(ep):
    joined = " ".join(ep.e2_auth.items or [])
    note = ep.e2_auth.note or ""
    if ep.e2_auth.status == "?":
        return "none"
    if "AllowAny" in joined or "permission_classes=[]" in joined or "open" in note:
        return "open"
    return "closed"


def evaluate():
    eps = {e.handler: e for e in analyze_repo(HERE)}
    halluc, skips, rows = [], [], []
    for h, gt in GT.items():
        e = eps.get(h)
        if e is None:
            skips.append(f"{h}: endpoint NOT DISCOVERED (E1)")
            continue
        found = tables_of(e)
        missing = gt["db"] - found
        extra = found - gt["db"] - {"<instance>"}
        raw = " ".join(e.e3_db_tables.items)
        tripped = [f for f in gt.get("forbidden", []) if f in raw]
        if missing:
            skips.append(f"{h}: SKIPPED tables {sorted(missing)} (found {sorted(found)})")
        if extra:
            halluc.append(f"{h}: HALLUCINATED tables {sorted(extra)}")
        if tripped:
            halluc.append(f"{h}: forbidden {tripped} in db facts")

        def present(edge):
            x = getattr(e, edge)
            return x.status != "n/a" and bool(x.items)
        for key, edge, name in [("cache", "e7_cache", "cache"), ("async_", "e5_async", "async"),
                                ("external", "e4_external", "external")]:
            if gt.get(key) and not present(edge):
                skips.append(f"{h}: {name} edge MISSED")
        if "pii" in gt and e.e6_pii.status != gt["pii"]:
            skips.append(f"{h}: PII status {e.e6_pii.status!r} != expected {gt['pii']!r}")
        ak = auth_kind(e)
        if ak != gt["auth"]:
            skips.append(f"{h}: auth {ak!r} != expected {gt['auth']!r}")
        rows.append((h, sorted(found), ak))
    return halluc, skips, rows


def main():
    halluc, skips, rows = evaluate()
    for h, db, ak in rows:
        print(f"  {h:22} auth={ak:7} db={db}")
    print("\n" + "=" * 66)
    print(f"HALLUCINATIONS: {len(halluc)}")
    for x in halluc:
        print("  ✗", x)
    print(f"SKIPS/MISMATCHES: {len(skips)}")
    for x in skips:
        print("  ✗", x)
    ok = not halluc and not skips
    print("\nRESULT:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
