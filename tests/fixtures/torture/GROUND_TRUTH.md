# Torture fixture — ground truth (hand-authored, not tool-generated)

This is the **authoritative** record of what every endpoint in this fixture *actually does*, written
by reading the code — **not** produced by the extractor. `check.py` asserts the extractor reproduces
exactly this (0 hallucinations, 0 skips). If the tool and this file ever disagree, one of them has a
bug; this file is the reference.

The project is deliberately the most complex the reviewer has been run on: **4 apps, 2 web frameworks
(Django DRF + Flask), 2 ORMs (Django ORM + SQLAlchemy), 28 endpoints**, mirroring the layering
patterns common to large Django/Flask commerce backends.

## Apps & architecture

| app | framework / ORM | style |
|-----|-----------------|-------|
| `apps/ads` | Django DRF / Django ORM | `api/controllers.py` → `helpers`/`metrics`/`interactions`/`delivery_logs`; raw-SQL modules; custom manager; FK-collision models |
| `apps/subscriptions` | Django DRF / Django ORM | **nested** `api/<feature>/controllers.py` + `helpers/` subpkgs; class `repository`; cache; CRM + Stripe egress |
| `apps/portal` | Django DRF / Django ORM | celery, threading, boto3/S3, dynamic-model helpers, get_object_or_404, traps |
| `apps/reporting` | **Flask** / **SQLAlchemy** | blueprint routes on decorators; `session.query/.add/.execute`, `Model.query` |
| `common/` | — | raw-SQL constants + a custom `CampaignManager` |

## Models → SQL tables (every model in the repo)

| model | table (db_table / __tablename__) | app | PII cols | notes |
|-------|----------------------------------|-----|----------|-------|
| Campaign | `ad_campaigns` | ads | — | custom `CampaignManager` |
| LeadDeliveryLog | `ad_delivery_logs` | ads | — | FK→Campaign |
| AuditLog | `ad_audit_log` | ads | — | |
| Entity | `ad_entity` | ads | — | (unused by endpoints) |
| AdTarget | `ad_target` | ads | — | |
| AdTargetEntity | `ad_target_entity_slice` | ads | — | **db_table collision** (real example); FK→AdTarget |
| Lead | `leads` | subscriptions | email, phone | |
| Product | `products` | subscriptions | — | |
| Order | `orders` | subscriptions | — | FK→Lead |
| OrderedItems | `order_items` | subscriptions | — | FK→Order, Product |
| Payment | `payments` | subscriptions | — | FK→Order |
| CampaignPage | `campaign_pages` | subscriptions | — | |
| User | `users` | portal | email, phone | |
| Profile | `user_profiles` | portal | — | FK→User |
| Article | `articles` | portal | — | FK→Domain |
| Domain | `domains` | portal | — | |
| CartEntry | `portal_cartentry` | portal | — | **no db_table** → Django convention `portal_cartentry` |
| Metric | `metrics` | reporting | — | SQLAlchemy |
| Visit | `visits` | reporting | email | SQLAlchemy |
| Report | `reports` | reporting | — | SQLAlchemy (unused by endpoints) |

## Endpoints — full ground truth

Legend: **R**=read, **W**=write. Raw-SQL tables are marked `(sql)`. PII (destination-aware): **✓
off-platform** (a sensitive field is traced to a THIRD PARTY — external API / log / task queue: the
real leak) / **⚠ to-client** (a sensitive field is returned to the caller in the response, OR a
person-model read co-occurs with egress but isn't traced — surface & verify, not a third-party leak) /
**? source** (read only, no egress traced) / **n/a**.

### apps/ads (Django DRF, cms-style)

| # | route | handler | method | auth | DB tables (R/W) | cache | async | external | PII | key pattern |
|---|-------|---------|--------|------|-----------------|-------|-------|----------|-----|-------------|
| 1 | `ads/campaigns/` | CampaignListView | GET | IsAuthenticated | `ad_campaigns` R | — | — | — | n/a | direct ORM |
| 2 | `ads/campaigns/export/` | CampaignExportView | GET | DRF default | `ad_campaigns` R, `ad_delivery_logs` R `(sql)` | — | — | — | n/a | raw SQL **CTE** (`recent` alias is NOT a table) |
| 3 | `ads/campaigns/import/` | CampaignImportView | POST | IsAdminUser | `ad_campaigns` W, `ad_audit_log` W | — | — | — | n/a | **custom manager** `objects.import_batch` followed; `self.create()` resolved to the managed model |
| 4 | `ads/campaigns/create/` | CampaignCreateView | POST | DRF default | `ad_campaigns` W | — | — | — | n/a | `serializer.save()` → Meta.model |
| 5 | `ads/campaigns/raw/` | CampaignRawView | GET | DRF default | `ad_campaigns` R `(sql)` | — | — | — | n/a | `Model.objects.raw()` |
| 6 | `ads/<kind>/<pk>/interactions/export/` | EntityInteractionsExportView | GET | DRF default | `ad_target_slice` R, `ad_target_entity_slice` R, `users` R, `cities` R — all `(sql)` | — | — | — | ⚠ to-client¹ | raw SQL JOIN via **function-local `from . import interactions`** → `_stream`→`_source_rows`→`cursor.execute(_INTERACTIONS_SQL)`; email streamed to the client |
| 7 | `ads/<kind>/metrics/` | EntityMetricsView | GET | DRF default | `ad_target_entity_slice` R, `ad_target` R | — | — | — | n/a | **FK traversal** `ad_target__added_on__gte` → AdTarget; exercises the db_table collision |
| 8 | `ads/audit/purge/` | AuditPurgeView | POST | IsAdminUser | `ad_audit_log` W `(sql)` | — | — | — | n/a | raw `DELETE FROM` |

The tables above are **code truth** — and the tool now matches all of them, including PII destination.

¹ **Fully traced now.** The SQL selects `u.email`; the tool taints the cursor, follows the PII through
`fetchall()` and the streaming `yield`, and lands it at the client → **⚠ to-client** (verify the
caller is authorised). It is deliberately **not ✓**: ✓ is reserved for PII that leaves the platform
(external API / log / queue). This export hands a user their own data back, which is a real but weaker
signal — exactly the distinction that keeps ✓ meaning *"someone is shipping PII off-platform"* (only 3
such endpoints across ~1000 in the example repos, vs ~20 before the split).

### apps/subscriptions (Django DRF, nested api/)

| # | route | handler | method | auth | DB tables (R/W) | cache | async | external | PII | key pattern |
|---|-------|---------|--------|------|-----------------|-------|-------|----------|-----|-------------|
| 9 | `subscriptions/landing/` | SubscriptionLandingView | GET | DRF default | `products` R | R+W `catalog` | — | — | n/a | controller → `SubscriptionHelper` → `ProductRepository` (cache-fronted) |
| 10 | `subscriptions/<lead_id>/summary/` | SubscriptionSummaryView | GET | DRF default | `products` R, `orders` R | — | — | — | n/a | **`Service().method()`** instance-call; m2m `order.products.add()` is NOT a write (trap) |
| 11 | `subscriptions/<lead_id>/dashboard/` | SubscriptionDashboardView | GET | IsAuthenticated | `orders` R, `order_items` R | — | — | — | n/a | deep chain controller→helper→repository |
| 12 | `subscriptions/<lead_id>/purchase-check/` | PurchaseCheckView | GET | DRF default | `orders` R, `campaign_pages` R, `products` R | R+W `purchase:{lead_id}` | — | — | n/a | cache + multiple ORM reads |
| 13 | `subscriptions/purchase/` | SubscriptionPurchaseView | POST | DRF default | `leads` R, `orders` R, `payments` W | — | — | `stripe.Charge.create`, `requests.post`→`{PAYMENT_URL}` | **✓ off-platform** email→requests.post | function-local class import → `PaymentGateway.charge` |
| 14 | `subscriptions/register/` | RegistrationView | POST | DRF default | `leads` W | — | — | `requests.post`→`{CRM_URL}` | **✓ off-platform** email+phone→requests.post | **CrmService** CRM egress |

### apps/portal (Django DRF, users-style)

| # | route | handler | method | auth | DB tables (R/W) | cache | async | external | PII | key pattern |
|---|-------|---------|--------|------|-----------------|-------|-------|----------|-----|-------------|
| 15 | `portal/users/<pk>/` | UserProfileView | GET | IsAuthenticated | `users` R | — | — | — | **? source** | `get_object_or_404(User)` |
| 16 | `portal/notify/` | NotifyView | POST | DRF default | `users` R | — | `celery.delay send_receipt` | — | **✓ off-platform** email→celery.delay | celery dispatch |
| 17 | `portal/webhook/` | WebhookView | POST | DRF default | — | — | `threading.Thread _process` | — | n/a | threading async |
| 18 | `portal/articles/` | ArticleFetchView | GET | DRF default | `articles` R | — | — | — | n/a | **dynamic model** `fetch_all(Article)` — param bound to Article, not `<instance>` |
| 19 | `portal/search/` | SearchView | GET | DRF default | `articles` R, `domains` R — `(sql)` | — | — | — | n/a | inline raw SQL JOIN |
| 20 | `portal/media/export/` | MediaExportView | POST | DRF default | `users` R | — | — | `boto3.client`→s3 | **⚠ potential** (User read co-occurs with S3 egress; only `id` read → not traced) | boto3 SDK egress |
| 21 | `portal/cache-demo/` | CacheOnlyView | GET | DRF default | — | R `home`, W `home` (set), W `home` (delete) | — | — | n/a | **trap:** `cache.delete` is NOT a DB write |
| 22 | `portal/upsert/` | UpsertView | POST | DRF default | `users` W | — | — | — | n/a | `get_or_create` |
| 23 | `portal/report/dynamic/` | DynamicReportView | GET | DRF default | — (none) | — | — | — | n/a | **trap:** `f"... FROM {table}"` → unresolvable → no table invented |
| 24 | `portal/misc/` | TrapView | POST | DRF default | `users` R | — | — | — | **✓ off-platform** email→log.info | **traps:** `request.session[..]=` not a table; `{"q": "SELECT ... FROM secret_table"}` never executed → not a table |

### apps/reporting (Flask + SQLAlchemy)

| # | route | handler | method | auth | DB tables (R/W) | cache | async | external | PII | key pattern |
|---|-------|---------|--------|------|-----------------|-------|-------|----------|-----|-------------|
| 25 | `/reporting/metrics` | metrics_list | GET | none (?) | `metrics` R | — | — | — | n/a | `session.query(Metric)` |
| 26 | `/reporting/summary` | summary | GET | **login_required** | `metrics` R | — | — | — | n/a | `Metric.query` (declarative) |
| 27 | `/reporting/ingest` | ingest | POST | none (?) | `visits` W | — | — | `requests.post`→literal analytics URL | **✓ off-platform** email→requests.post | `session.add(Visit(..))` |
| 28 | `/reporting/bulk` | bulk_ingest | POST | none (?) | `visits` W | — | — | — | n/a | `session.execute(insert(Visit))` (SQLAlchemy 2.x core) |

## What must NEVER be reported (hallucination tripwires)

| # | endpoint | must NOT appear | why |
|---|----------|-----------------|-----|
| 2 | CampaignExportView | table `recent` | CTE alias (`WITH recent AS ...`), not a table |
| 6/2 | (any CTE/subquery) | subquery aliases | `FROM (SELECT ...)` opener has no table |
| 10 | SubscriptionSummaryView | any write from `order.products.add()` | Django m2m add ≠ SQLAlchemy `session.add` |
| 18 | ArticleFetchView | table `model` | dynamic param name is never a table |
| 21 | CacheOnlyView | any table | `cache.get/set/delete` are cache ops, not DB |
| 23 | DynamicReportView | table `{table}` / `LIMIT` | f-string placeholder is unresolvable, not a table |
| 24 | TrapView | table `secret_table` | SQL string sits in a dict, never executed |

## Known lens limitations (honest gaps — NOT bugs, and NOT counted as skips)

1. ~~Raw-SQL PII isn't traced to egress.~~ **CLOSED** — raw-SQL columns are scanned for PII, the cursor
   is tainted, and the value is followed through `fetchall()`/streaming `yield` to the response. PII is
   now **destination-aware**: **✓** only when it leaves the platform (external / log / queue); **⚠**
   when returned to the client. (Endpoint 6 is now ⚠ to-client, its honest label.)
2. ~~Custom-manager `self.create()` is not model-resolved.~~ **CLOSED** — a followed Manager method now
   binds `self` to the managed model, so `self.create()`/`self.bulk_create()` register as real writes
   (endpoint 3's `ad_campaigns` is now a **write**, no spurious fallback read).
3. **Module imports beyond level-1 relative need classes.** `from ..pkg import module` /
   `from apps.x import module` are not resolved for `module.fn()` follows; cross-package delegation in
   this fixture is therefore class-based (`Service.method()`), which resolves by name. (Level-1
   `from . import x`, as in endpoint 6, *is* resolved.)

These are surfaced honestly by the tool (`⚠`/`?`/`n/a` or `follow_stop`), never as false "safe".

## How to verify

```bash
python3 tests/fixtures/torture/check.py     # prints per-endpoint recall + PASS/FAIL vs this file
python3 -m pytest tests/test_torture.py -q   # enforces 0 hallucinations / 0 skips / 0 blindspots in CI
```
