# Megashop — 7-edge ground truth (hand-authored, verified against the reviewer)

The **most complex** fixture in this repo — deliberately harder than `tests/fixtures/torture`:
**6 apps, 3 web frameworks (Django DRF + Flask + FastAPI), 2 ORMs (Django ORM + SQLAlchemy),
29 endpoints**, deep 5-hop abstraction chains, and the **full auth matrix**. This file is the
authoritative record of what each endpoint does across **all 7 lens edges**; `check.py` asserts the
reviewer reproduces it (0 hallucinations, 0 skips). Written from the code, not tool-generated.

The 7 edges: **E1** route→handler · **E2** auth · **E3** db tables (R/W) · **E4** external calls ·
**E5** async/worker · **E6** PII · **E7** cache.

## Apps & architecture

| app | framework / ORM | style / what it stresses |
|-----|-----------------|--------------------------|
| `apps/orders` | Django DRF / Django ORM | **5-hop chain**: controller → use-case (instance var) → service → repository → dao; custom manager; FK traversal; serializer.save; celery+thread; cache; permission constant |
| `apps/billing` | Django DRF / Django ORM | base-class auth; **streaming raw-SQL PII export**; stripe/razorpay/requests egress; CTE; celery apply_async; open webhook |
| `apps/accounts` | Django DRF / Django ORM | **full auth matrix**; get_object_or_404; dynamic-model; all 3 PII destinations; trap cluster |
| `apps/catalog` | Django DRF / Django ORM | cache lens (get/set/delete/clear, `caches[..]`); `.raw()`; `Service()` instance-call; m2m-add trap |
| `apps/analytics` | **Flask** / **SQLAlchemy** | blueprint routes; `session.query/.add/.execute`, `Model.query`; boto3/sendgrid; `login_required` |
| `apps/gateway` | **FastAPI** | `APIRouter` prefix; `Depends` auth; httpx egress; celery `send_task` |

## Models → SQL tables (every model)

| model | table | app | PII | notes |
|-------|-------|-----|-----|-------|
| Customer | `customers` | orders | email, phone | |
| Product | `products` | orders | — | |
| Order | `orders` | orders | — | custom `OrderManager`; FK→Customer |
| OrderItem | `order_items` | orders | — | FK→Order, Product |
| AuditLog | `audit_log` | orders | — | written inside the manager + tasks |
| Invoice | `billing_invoices` | billing | — | FK→Order |
| Payment | `billing_payments` | billing | — | FK→Order |
| Refund | `billing_refunds` | billing | — | FK→Payment |
| Account | `accounts` | accounts | email, phone | Django `PERSON_MODELS` |
| Profile | `profiles` | accounts | — | FK→Account |
| Article | `articles` | accounts | — | dynamic-model target |
| Category | `categories` | catalog | — | |
| Item | `catalog_items` | catalog | — | m2m→Product |
| Metric | `metrics` | analytics | — | SQLAlchemy |
| Visit | `visits` | analytics | email | SQLAlchemy |
| Report | `reports` | analytics | — | SQLAlchemy |

PII: **✓ off-platform** (sensitive field traced to a third party — external/log/queue: the real leak) ·
**⚠ to-client** (returned to the caller, OR person-read co-occurring with egress) · **? source** (read
only) · **n/a**. Auth `[✓]` = resolved (may be *open* — see the value); `[?]` = none detected.

## apps/orders (Django DRF, deep chain)

| route | handler | method | E2 auth | E3 db | E4 ext | E5 async | E6 pii | E7 cache |
|-------|---------|--------|---------|-------|--------|---------|--------|---------|
| `orders/` | OrderListView | GET | `ORDER_PERMS` = IsAuthenticated + ApiKeyPermission (constant) | orders R | — | — | — | R+W `orders:active` |
| `orders/create/` | OrderCreateView | POST | DRF default (IsAuthenticated) | orders **W**, order_items **W** (5-hop chain) | — | celery.delay `sync_to_crm`; threading.Thread `_reindex` | — | — |
| `orders/<id>/` | OrderDetailView | GET | `ORDER_PERMS` | orders R, order_items R, customers R (FK traversal) | — | — | ? (Customer person-read) | — |
| `orders/import/` | OrderImportView | POST | IsAdminUser | orders **W**, audit_log **W** (custom manager `bulk_import`) | — | — | — | — |
| `orders/form-create/` | OrderCreateFormView | POST | DRF default | orders **W** (serializer.save→Meta.model) | — | — | — | — |

## apps/billing (Django DRF, payments)

| route | handler | method | E2 auth | E3 db | E4 ext | E5 async | E6 pii | E7 cache |
|-------|---------|--------|---------|-------|--------|---------|--------|---------|
| `billing/invoices/export/` | InvoiceExportView | GET | IsAdminUser (**inherited** BaseBillingView) | billing_invoices R, orders R, customers R (raw SQL, streamed) | — | — | **⚠ to-client** (email streamed via `yield`) | — |
| `billing/charge/` | ChargeView | POST | IsAdminUser (inherited) | orders R, customers R, billing_payments **W** | stripe.Charge.create; requests.post→`{PAYMENT_URL}` | celery.apply_async `send_receipt` | **✓ off-platform** (email→requests.post) | — |
| `billing/revenue/` | RevenueReportView | GET | IsAdminUser (inherited) | orders R, billing_payments R (raw SQL **CTE** — `recent` is not a table) | — | — | — | — |
| `billing/refund/` | RefundView | POST | IsAdminUser (inherited) | billing_refunds **W** | requests.post→`{RAZORPAY_URL}` | — | — | — |
| `billing/webhook/` | PaymentWebhookView | POST | **OPEN** (`permission_classes=[]`) | billing_payments **W** | — | — | — | — |

## apps/accounts (Django DRF, auth matrix + traps)

| route | handler | method | E2 auth | E3 db | E4 ext | E5 async | E6 pii | E7 cache |
|-------|---------|--------|---------|-------|--------|---------|--------|---------|
| `accounts/<pk>/` | ProfileView | GET | **AllowAny** (explicit open) | accounts R | — | — | **⚠ to-client** (email returned) | — |
| `accounts/<pk>/update/` | UpdateProfileView | POST | DRF default (IsAuthenticated) | accounts R+**W** (instance-var `UpdateFlow`) | — | — | ? (Account person-read) | — |
| `accounts/notify/` | NotifyView | POST | **ApiKeyPermission** (custom) | accounts R | — | celery.delay `send_receipt` | **✓ off-platform** (email→celery) | — |
| `accounts/webhook/` | AccountWebhookView | POST | **OPEN** (`permission_classes=[]`) | — | — | threading.Thread `_process` | — | — |
| `accounts/articles/` | ArticleFetchView | GET | DRF default | articles R (**dynamic model** `fetch_all(Article)`) | — | — | — | — |
| `accounts/search/` | SearchView | GET | DRF default | accounts R, profiles R (raw SQL JOIN) | — | — | — | — |
| `accounts/misc/` | TrapView | POST | DRF default | accounts R | — | — | **✓ off-platform** (email→log) | W (`cache.delete`) |

`accounts/misc/` traps (must NOT become DB facts): `request.session[..]=` (session), `{"q":"SELECT … FROM secret_table"}` (never executed), `cache.delete` (cache, not a table).

## apps/catalog (Django DRF, cache + traps)

| route | handler | method | E2 auth | E3 db | E7 cache |
|-------|---------|--------|---------|-------|---------|
| `catalog/` | CatalogListView | GET | DRF default | catalog_items R (`.raw()`) | R+W `catalog:list` |
| `catalog/categories/` | CategorySummaryView | GET | DRF default | categories R, catalog_items R (`Service().summary()`) | — |
| `catalog/cache/clear/` | CacheClearView | POST | DRF default | — (none) | W (`delete`, `clear`) |

`catalog/categories/` trap: the m2m `item.products.add(1)` is **not** a DB write.

## apps/analytics (Flask + SQLAlchemy)

| route | handler | method | E2 auth | E3 db | E4 ext | E6 pii |
|-------|---------|--------|---------|-------|--------|--------|
| `/analytics/metrics` | metrics_list | GET | none (?) | metrics R (`session.query(Metric)`) | — | — |
| `/analytics/summary` | summary | GET | **login_required** | metrics R (`Metric.query`) | — | — |
| `/analytics/ingest` | ingest | POST | none (?) | visits **W** (`session.add(Visit)`) | requests.post→`{ANALYTICS_URL}` | **✓ off-platform** (email→requests) |
| `/analytics/export` | export_reports | POST | none (?) | reports **W** (`session.execute(insert)`) | boto3.client→s3 | — |
| `/analytics/email` | email_report | POST | none (?) | — | sendgrid | — |

## apps/gateway (FastAPI)

| route | handler | method | E2 auth | E4 ext | E5 async |
|-------|---------|--------|---------|--------|---------|
| `/gw/status` | status | GET | none (?) | — | — |
| `/gw/proxy-order` | proxy_order | GET | **Depends**(get_current_user) | httpx.get→upstream | — |
| `/gw/dispatch` | dispatch | POST | none (?) | — | celery.send_task `worker.process_batch` |
| `/gw/webhook` | gw_webhook | POST | none (?) | httpx.post→hooks | — |

## Auth matrix (E2 coverage — the point of this fixture)

Every auth shape the lens resolves is exercised: **permission constant** (`ORDER_PERMS`), **explicit
class** (IsAdminUser), **AllowAny** (open by choice), **empty `[]`** (open webhook), **custom class**
(ApiKeyPermission), **base-class inheritance** (BaseBillingView), **DRF settings default**
(IsAuthenticated), **Flask decorator** (login_required), **FastAPI dependency** (Depends), and **none**
(FastAPI/Flask routes with no marker → honest `?`).

## Hallucination tripwires (must never appear)

`recent` (CTE alias · billing/revenue) · `secret_table` (dict SQL · accounts/misc) · `{table}`
(none here) · any write from `item.products.add` (m2m · catalog/categories) · any table from
`cache.delete`/`clear` (catalog, accounts) · `model` (dynamic-model param · accounts/articles).

## How to verify

```bash
python3 tests/fixtures/megashop/check.py     # per-endpoint 7-edge check vs this file
python3 -m pytest tests/test_megashop.py -q   # enforces 0 hallucinations / 0 skips in CI
```
