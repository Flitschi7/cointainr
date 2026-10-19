# Cointainr Optimization Roadmap

Reviewed: 2026-10-19. Scope: static repository audit, existing frontend unit-test
baseline, and scoped agent setup, not implementation of the changes below.
Recheck findings against
current code before starting a ticket. No latency, memory, or accuracy gains
have been measured yet; effort bands are planning estimates, not promises.

## Priorities and evidence

| Priority | Observed behavior and evidence | Next deliverable and acceptance check | Owner / effort |
| --- | --- | --- | --- |
| P0 | [Dockerfile](../Dockerfile#L4) builds with Node 18; [frontend package](../frontend/package.json) and lockfile use Vite 7.0.4, whose engines require `^20.19.0 || >=22.12.0`. | Align local, CI, and Docker on a maintained compatible Node release; preserve the lockfile unless an upgrade is approved. Clean `npm ci`, check, unit tests, and image build succeed on that runtime. | Backend + frontend / S |
| P0 | [Docker workflow](../.github/workflows/docker-build.yml) logs into the registry and sets `push: true` on both push and PR events, without test jobs. Fork PRs may fail authentication; trusted PRs may publish images before merge. | Separate PR validation from authorized publication; skip registry credentials/push/releases on PRs, minimize permissions, gate publication on tests, and cover PRs targeting `beta`. Verify the event matrix without publishing a trial image. | Backend + reviewer / M |
| P0 | [Portfolio calculations](../frontend/src/lib/services/portfolioCalculations.ts#L99) retry failed FX conversion individually, then add raw foreign amounts to target-currency totals if retries fail. Missing prices are skipped; yield calculation also subtracts purchase price without using `buy_currency`. | Define explicit incomplete/stale results; never label mixed units as a target-currency total. Test batch and individual FX failures, missing prices, and differing quote/purchase currencies with fixed rates. | Frontend + backend contract review / M |
| P1 | [Asset schemas](../backend/app/schemas/asset.py#L7) accept plain floats and optional strings without explicit finite/range/domain constraints on create or update. [Storage](../backend/app/models/asset.py#L38) uses floating point. | Agree whether zero positions, short positions, negative cash, and free acquisitions are valid. Reject non-finite input and invalid currencies/symbols as appropriate. Test POST and partial updates. Specify rounding with golden fixtures before considering any storage migration. | Backend / M |
| P1 | Two frontend unit suites exist under [service tests](../frontend/src/lib/services/__tests__/enhancedApi.test.ts). No backend test files or frontend E2E specs were found in this audit; [Playwright](../frontend/playwright.config.ts) starts only frontend preview. | Establish executable unit configuration and isolated backend fixtures. Add financial, cache, auth, and API-contract regressions, then login/add/edit/delete/refresh E2E flows with a disposable API/database. | Backend + frontend / M-L |
| P1 | [Price endpoint](../backend/app/api/endpoints/price.py#L39) calls an async [pricing method](../backend/app/services/price_service.py#L25) that invokes synchronous Finnhub and yfinance operations directly. | Measure health-request latency while a mocked provider blocks. Isolate blocking I/O or use an appropriate async client with bounded concurrency and timeouts; retain provider quotas and stale-cache behavior. Prove responsiveness under the same workload. | Backend / M |
| P1 | [Dashboard sorting](../frontend/src/routes/+page.svelte#L371) computes value, yield, and performance separately; those helpers independently request quotes and conversions. Caches may reduce actual network work. | Count calculations, frontend requests, and provider calls separately. Derive sorting/display/totals from one quote snapshot when justified; test refresh races, currency changes, and invalidation. | Frontend / M |
| P1 | [Session validation](../backend/app/services/auth_service.py#L114) commits and refreshes last activity on each successful call. [Price endpoints](../backend/app/api/endpoints/price.py#L16) capture `SessionLocal`, while [shared dependency](../backend/app/db/database.py) supports a replaceable session maker. | Measure authenticated polling write load and inspect active transaction paths. Unify fixture/dependency ownership before tuning; test isolated databases, rollback, expiry, logout, and concurrent reads/refreshes. Avoid sharing an async session between concurrent tasks. | Backend / M |
| P2 | [Dockerfile](../Dockerfile#L28) retains a compiler in the runtime image, has no non-root user, and makes the data directory world-writable. [Compose](../docker-compose.yml) persists SQLite under `/app/data`. | Introduce a non-root runtime and narrowly writable data volume, separate build-only dependencies where useful, scan dependencies/images, and prove startup and backup/restore with existing volume ownership. | Backend + reviewer / M |

S: roughly half a day; M: roughly one to three days; L: several days. Confirm
scope after the first regression test, including database/API compatibility.
P0 denotes first implementation priority, not a claim of active exploitation.

Vite compatibility is confirmed by the lockfile engines and the official
[Vite 7 announcement](https://v7.vite.dev/blog/announcing-vite7#node-js-support).
Do not infer a measured rounding-error percentage from floating-point storage.
Do not call public demo credentials a new secret leak; review real credential,
session-token, and financial-data logging separately before changing log levels.

## Delivery sequence

### Phase 1: Reproducible checks and safe releases

1. Capture installed runtimes and existing check/test output. Fix the Node
	mismatch in its own change, then establish backend and frontend regression
	infrastructure without real API keys, provider traffic, or user databases.
2. Add CI check/unit jobs and disposable integration fixtures. Gate image
	publication with successful checks, and explicitly restrict push/release
	behavior to intended branch pushes. Verify fork and same-repository PRs.
3. Keep the current release-message markers until the versioning policy is
	deliberately changed; `feat:` alone does not currently request a minor bump.

Exit: a deliberate failing test blocks publication, a PR cannot publish or
release, and compatible clean builds work. Rollback: revert workflow/toolchain
changes independently; retain the last known-good image digest.

### Phase 2: Financial correctness and recovery

1. Fix mixed-unit fallbacks and missing-price completeness with mocked rates.
	Test purchase currency independently from quote and display currencies.
2. Agree on validation and rounding rules. Preserve valid existing holdings;
	changing SQLite types to Decimal is not automatically an exact-decimal design
	and is not a prerequisite for every calculation fix.
3. Test authentication enabled/disabled/demo modes, session expiry and logout,
	cookie configuration, rate limiting, and log redaction. Treat these as review
	targets until a concrete defect is reproduced.
4. Define a consistent SQLite backup procedure, restore into a temporary path,
	and compare holdings and schema. Check migrations and demo cleanup against
	that recovery procedure before altering persisted data.

Exit: deterministic fixtures cover unavailable prices, partial FX failure,
cross-currency cost basis, invalid inputs, and restoration. Rollback: keep API
changes additive where possible; restore backups only through a rehearsed path.

### Phase 3: Measured performance improvements

Use synthetic portfolios of 10, 100, and 1,000 positions with repeated symbols
and three currencies. Exercise fresh cache, expired cache, provider timeout,
manual refresh, sorting, and currency switches. Record machine/runtime details.

| Measure | Baseline method | Acceptance criterion |
| --- | --- | --- |
| API responsiveness | Compare health-request p50/p95 during idle and a fixed slow-provider simulation. | Agree a latency budget before implementation; eliminate event-loop starvation under the same workload. |
| Request amplification | Count UI requests, unique symbols/pairs, provider calls, cache hits, and concurrent refreshes. | Warm-cache operations require zero provider calls; concurrent identical misses coalesce or obey an explicit provider budget. |
| Dashboard work | Record sorting/total calculation counts and desktop/mobile browser traces. | Avoid redundant quote/conversion work for unchanged snapshots without stale totals after mutations or currency changes. |
| SQLite contention | Count writes and lock errors during authenticated polling plus manual refresh. | No lock failures in the controlled workload; reduce unnecessary writes without extending session validity incorrectly. |
| Delivery cost | Record compressed JS payload, build time, image size, and runtime memory. | Agree budgets from the baseline; split/lazy-load heavy charts only when the trace justifies it. |

Use existing cache/performance facilities only after confirming they are wired
into the active request path. Avoid adding another cache layer, unbounded
parallel requests, or a database rewrite. Rollback each optimization separately;
keep it only when correctness checks pass and before/after results support it.

### Phase 4: Deployment and ongoing maintenance

Harden the container after the volume recovery test. Review dependency updates,
retention, health/readiness behavior, environment-variable precedence, provider
timeouts, and scheduling shutdown. Add compatible configuration changes with
documented precedence and deprecation rather than breaking existing env files.
Confirm external telemetry is opt-in and that personal holdings stay local.

Exit: non-root image reads/writes an existing volume safely, backups restore,
dependency findings are triaged, and upgrades have a tested rollback procedure.

## Validation commands and limits

### Baseline captured during this review

`npm --prefix frontend run test:unit` ran with Vitest 3.2.4: **30 passed,
2 failed across 2 suites**. Application code and tests were unchanged.

- [Cache suite](../frontend/src/lib/services/__tests__/cacheService.test.ts#L71):
	"should fetch fresh data when cache is expired or forced" expected two fetch
	calls but observed one. Determine whether the test setup or cache contract
	is wrong before changing either.
- [API suite](../frontend/src/lib/services/__tests__/enhancedApi.test.ts#L173):
	the same-currency rate assertion rejects additional `fetched_at` and `source`
	fields. Confirm the response contract before changing the assertion or API.

Resolve these baseline failures in Phase 1 before making tests a required
publication gate. Backend tests, frontend typecheck/lint/build, E2E, container
builds, and performance benchmarks were not run for this documentation change.

### Implementation checks

Run frontend commands from `frontend/` after installing the locked dependencies
on a compatible runtime:

```text
npm ci
npm run check
npm run test:unit
npm run lint
npm run build
```

Run `python -m pytest` from `backend/` using the selected project environment
after adding isolated tests; no collected tests is not a passing backend gate.
Run `npm run test:e2e` only after creating specs, installing the browser runtime,
and arranging a disposable API or deterministic network mocks. Do not infer
working integration coverage from the presence of package scripts.

Use a clean image build and container smoke test after Docker changes, not for
documentation-only changes. Never target the production database or live market
providers in CI. Record baseline failures separately from introduced failures.

## Agents and change workflow

Use the four [repository agents](../.github/agents/cointainr-planner.agent.md):
planner for evidence and sequencing, backend for API/data/deployment work,
frontend for Svelte/calculations, and reviewer for independent static review.
The [shared guide](../AGENTS.md) defines safety, verification, and Git rules.

Create approved tickets under `.scratch/<feature>/issues/NN-<slug>.md` using
[local tracker conventions](agents/issue-tracker.md). Keep one implementation
purpose per branch/commit; include the regression check and rollback in each
ticket. Obtain authorization before creating branches or publishing changes.
No GitHub Issues or speculative implementation tickets are created by this plan.
