# App optimization: current app before new features

Status: ready-for-agent

Improve Cointainr as it exists today: make the backend safe to change, make
holdings data trustworthy, and fix the one real responsiveness problem. New
features (wallet syncing) are parked in [wallet-sync](../wallet-sync/spec.md).

Vocabulary follows [GLOSSARY.md](../../GLOSSARY.md). Decisions that are hard to
reverse are in [docs/adr/](../../docs/adr/).

## Context

- One person, one portfolio per instance. The real installation runs on a
  separate server; it pulls `ghcr.io/flitschi7/cointainr:latest` manually (no
  auto-update), and its SQLite file is backed up daily. Restores have been done
  before.
- Everything in the local checkout (database, backend) is test data.
- Nothing feels slow today.
- Frontend: valuation, sorting, and totals were reworked and smoke-tested in the
  browser (PRs 8–14). Backend: no tests, two competing session modules, and a
  local `.venv` that points to an uninstalled Python 3.13.

## Priorities

1. **Easier to change**: working local backend, backend tests, one session owner.
2. **More correct and safer**: holding validation, display precision.
3. **Faster**: only the blocking provider calls.
4. **Leaner to run**: only what the Python upgrade removes from the image.

## Decisions

### Domain

- Interface labels move to glossary terms: **Location** (was Location/Broker),
  **Gain/Loss** (was Yield), **Return** (was Performance). Code identifiers are
  renamed gradually as code is touched; database columns are not renamed.
- Holding rules, enforced on create and update only:
  - quantity may be 0;
  - quantity may be negative only for cash (no short holdings);
  - purchase price may be 0 (free acquisition);
  - `NaN` and `Infinity` are always rejected.
- Existing rows that break these rules still load and display. A read-only check
  lists violations so they can be fixed by editing.
- Numbers stay floats in storage and calculation, rounded only for display
  ([ADR 0002](../../docs/adr/0002-floats-for-money.md)).
- Display precision: quantities up to 8 decimals without trailing zeros; quotes
  and purchase prices below 1 shown with enough significant digits; money
  amounts keep 2 decimals.

### Backend platform

- Python 3.14 for local development and the image. Fall back to 3.13 only if a
  required package has no working 3.14 release.
- Dependencies: bump to the newest minor/patch within current major versions;
  majors are separate later changes. Accepted exception: transitive `cffi`
  1 → 2, because cffi 1.x has no Python 3.14 wheels and current `curl_cffi`
  (via yfinance) requires cffi 2.
- Split test tools (`pytest`, `pytest-asyncio`, …) into
  `backend/requirements-dev.txt`; the runtime image installs only
  `requirements.txt`. Remove `gcc` from the runtime image if every runtime
  package installs from a wheel.
- The container keeps running as root
  ([ADR 0003](../../docs/adr/0003-container-runs-as-root.md)).

### Tests and data access

- Backend tests come first, against a temporary SQLite file selected through
  `COINTAINR_DATABASE_URL`, with mocked market-data providers and no real API
  keys. Order: holdings CRUD and validation → prices and conversions →
  authentication modes.
- After tests exist, every endpoint, service, and scheduled task obtains sessions
  through the `get_db` dependency in `app/db/database.py`; `app/db/session.py`
  keeps only the engine, session maker, and `Base`.
- Backend tests run in CI as their own job; `build-and-push` needs both it and
  `frontend-checks`.

### Responsiveness

- Market-data lookups must not block the server: while a provider is slow, other
  requests (at least `/health` and holdings reads) still respond. Keep provider
  quotas and the stale-quote fallback.

### Delivery

- Features and risky changes go through a feature branch and PR to `main`.
  Small, low-risk changes may be pushed directly to `main`. The `beta` branch is
  no longer part of the flow; no more `main` → `beta` syncs.
- Every push to `main` publishes images; the real installation is only affected
  when it is pulled manually.

## Work items

Each item is one ticket. "PR" means feature branch and pull request; "direct"
means a small commit pushed to `main`.

| #   | Item                                                                                                                                                                 | Delivery | Blocked by |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------- |
| 01  | Documentation: glossary, ADRs 0001–0003, `.gitignore` exception for `docs/adr/`, this spec, parked wallet spec, roadmap rewrite, AGENTS.md and README delivery rules | direct   | –          |
| 02  | Interface labels: Location, Gain/Loss, Return                                                                                                                        | direct   | –          |
| 03  | Display precision for quantities and small prices                                                                                                                    | PR       | –          |
| 04  | Python 3.14, minor/patch bumps, `requirements-dev.txt`, slimmer image                                                                                                | PR       | –          |
| 05  | Backend tests: holdings CRUD (current behavior)                                                                                                                      | PR       | 04         |
| 06  | Backend tests: prices and conversions with mocked providers                                                                                                          | PR       | 04         |
| 07  | Backend tests: authentication off, on, and demo modes                                                                                                                | PR       | 04         |
| 08  | CI: backend test job gates publication                                                                                                                               | PR       | 05         |
| 09  | One session owner: `get_db` everywhere                                                                                                                               | PR       | 05, 06, 07 |
| 10  | Holding validation rules and read-only violation check                                                                                                               | PR       | 05         |
| 11  | Non-blocking market-data lookups                                                                                                                                     | PR       | 06         |

### Acceptance checks

- **01**: glossary and ADRs are tracked by git; the roadmap's open phases match
  this spec, dropped items are marked as dropped with a one-line reason, and the
  stale line about retained cell components is corrected; AGENTS.md and README
  describe the PR-or-direct rule without `beta` syncs.
- **02**: table headers, sort buttons, and filter placeholders use the glossary
  terms; no calculation changes; frontend tests, check, and build pass.
- **03**: 0.00512 BTC displays as `0,00512`; 10 displays as `10`; a 0.0004 USD
  quote displays its significant digits; money stays at 2 decimals; unit tests
  cover each case.
- **04**: a clean venv on 3.14 installs both requirement files; the backend
  starts locally against a copy of the test database; the image builds, starts
  offline, and passes health, HTML, and SQLite integrity checks; no package
  crosses a major version except the accepted `cffi` 2; `pytest` is absent
  from the runtime image.
- **05–07**: tests use a temporary database and mocked providers, never a real
  API key or provider call, and pass from a clean venv with one command.
- **08**: a deliberately failing backend test blocks publication in a PR run.
- **09**: no module outside `app/db/` imports `SessionLocal`; all tests from
  05–07 pass unchanged.
- **10**: create and update reject each invalid case with a 422 and accept each
  valid edge case (zero quantity, negative cash, zero purchase price); existing
  invalid rows still load; the violation check runs read-only against a copy of
  a backup and lists offending holdings.
- **11**: with a mocked provider that delays 10 s, `/health` and holdings reads
  answer within 1 s during a forced refresh; stale-quote fallback still works.

## Out of scope

- Wallet syncing (parked).
- Transaction history and realized gains
  ([ADR 0001](../../docs/adr/0001-holdings-based-portfolio.md)).
- Performance benchmarks with synthetic portfolios; dashboard work is not slow.
- Reducing session writes on authenticated requests.
- Non-root container, image scanning, and upgrade-rollback procedures.
- Backup and restore rehearsal (already done in practice).
- Renaming database columns or exact-decimal storage.
- Major-version dependency upgrades.
- Pre-existing ESLint errors in `+page.svelte` and `cacheService.ts`, unless a
  ticket touches those lines anyway.
