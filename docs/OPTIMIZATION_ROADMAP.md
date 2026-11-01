# Cointainr Optimization Roadmap

Reviewed: 2026-10-20. This document retains the initial audit and records the
implementation passes below. Recheck remaining findings against current
code before starting a ticket. No latency, memory, or accuracy gains have been
measured yet; effort bands are planning estimates, not promises.

## Implementation status

Completed in the first optimization pass:

- Fixed frontend cache hits ignoring expiry, stored per-entry TTLs, honored zero
  TTL and exact expiry boundaries, and retained stale data on fetch failure.
  Added six regressions, including legacy stored entries and matching expiry
  countdowns at custom-TTL boundaries.
- Corrected the same-currency API test to assert existing response metadata.
  Both initial failing tests now pass: **38 unit tests pass across 2 suites**.
- Removed whole-process environment injection and redundant output overrides
  from [Vite config](../frontend/vite.config.ts). Development logging uses
  `import.meta.env.DEV`; the build no longer emits those configuration warnings.
- Aligned [Docker](../Dockerfile) and [local Node version](../frontend/.nvmrc)
  on Node 24. CI uses the same version file.
- Added typecheck/unit/build gates, read-only multi-architecture PR validation,
  and a push-only publication job in the [workflow](../.github/workflows/docker-build.yml).
  PRs targeting both `main` and `beta` are validated without registry login.
- Removed three unreferenced internal components: ConfigurationDisplay,
  CorrelationMatrix, and PerformanceMonitor. The correlation prototype generated
  random data; the active performance-monitoring service remains. This is a
  maintainability cleanup, not a measured bundle-size improvement.
- Replaced the obsolete always-loaded project plan with a short
  [repository guide](../.github/instructions/instructions.instructions.md),
  [frontend design/behavior rules](../.github/instructions/frontend.instructions.md),
  and [backend safety rules](../.github/instructions/backend.instructions.md).
  The main instruction file is no longer ignored by Git.

Verification: frontend unit tests pass; Svelte check reports zero errors and
warnings; production build passes; touched frontend files are formatted;
workflow YAML and PR/push permission/dependency assertions pass. The five
touched frontend files retain 10 pre-existing ESLint errors, down from 11 at
the initial commit, with no new rule/message diagnostics. Repository-wide lint
is not claimed to pass.

Docker Desktop's Linux engine was unavailable during that first pass; local
image and startup verification is recorded in the follow-up below. Actual
GitHub workflow execution remains unverified. Backend tests, E2E, provider
calls, and application performance benchmarks were not run. No user databases
or holdings were changed. Financial totals/cost-basis fixes remain the next
correctness priority; do not treat this pass as completing every audit item.

### Build process follow-up

- Beta pushes retain automatic frontend checks but no longer publish images.
  A manual `workflow_dispatch` with `publish_beta: true` on `beta` publishes
  AMD64/ARM64 beta images after successful checks. The trigger must first be
  present on `main` to be available in GitHub's Actions interface.
- PR image validation uses native AMD64 only, without QEMU or registry login.
  Stable releases retain AMD64/ARM64 publication and existing version markers.
- Superseded beta-push/PR runs are cancelled; main and manual publication runs
  are not automatically cancelled. Jobs have explicit time limits. PR and
  publication builds use the same image-cache scope with cache export enabled;
  GitHub's branch access rules still apply.
- The Docker context now allows only Dockerfile inputs, keeping local build
  output, installed dependencies, environment files, private data directories,
  and database files out of context. No persisted volume paths were changed.

Validation: workflow YAML and seven publication scenarios pass local assertions,
including PR permissions, cancellation conditions, cache configuration, and
platform selection. The local Linux/AMD64 production image builds successfully.
A repeat build reused all application layers and completed in 2.07 seconds on
this machine; this is not a before/after GitHub cost benchmark. An ephemeral
container with network access disabled, placeholder provider keys, and a tmpfs
SQLite database passed real ASGI startup, health/HTML/compiled-asset HTTP checks,
table initialization, and SQLite integrity checking. It was removed after the
test, without mounting host data. ARM64 builds, remote cache reuse, registry
publication, and actual GitHub workflow runs remain unverified in this pass.
The clean Docker dependency installation initially reported 41 npm audit
findings (including 4 critical), the baseline for the security follow-up below.

### Dependency security follow-up

- Updated vulnerable dependency families within their existing version ranges,
  including Svelte, SvelteKit, Vite, Playwright, Lodash, and TypeScript ESLint,
  then applied compatible transitive security fixes without `--force`.
- Upgraded Vitest and its UI together from 3.2.4 to 4.1.12. The older test-runner
  line retained vulnerable mocker/worker dependencies; the existing service
  regressions pass without changes under Vitest 4.
- Added two narrowly scoped [npm overrides](../frontend/package.json):
  SvelteKit uses Cookie 0.7.2 or newer within 0.7, and Typography uses
  postcss-selector-parser 7.1.6 or newer within 7. These preserve the current
  SvelteKit 2/Vite 7/TypeScript 5 stack and upgrade the parser rather than
  accepting npm's suggested Typography downgrade to 0.5.4. Remove the overrides
  once upstream dependencies adopt fixed versions and repeat the checks.
- Compared old/new lockfile versions and checked resolved download sources:
  no compared package path was downgraded and all tarballs use the official
  npm registry. Local npm 12 needed an explicitly approved, command-only URL
  download allowance during resolution; no project/global policy was changed.

Validation: `npm audit` reports **0 findings**, down from 41; the production-only
audit reports **0**, down from 1. This is an npm advisory result, not a backend
dependency or container-OS security scan. Svelte check reports zero errors and
warnings; all 38 unit tests, the production build, installed peer-tree checks,
and dependency-file formatting pass. Cookie parsing/serialization, invalid
input rejection, and Typography selector/pseudo handling pass focused checks.

A clean Linux `npm ci` and production image build pass, followed by the same
offline, tmpfs-backed startup/health/HTML/asset/SQLite integrity checks. Windows
`npm ci` was blocked by a loaded native CSS DLL; local packages were restored
with `npm install`, and local checks pass, but a clean Windows reinstall is not
claimed. Desktop (1440px) and mobile (390px) browser smoke checks with synthetic
API fixtures verify portfolio rendering, nonblank distribution charts, tab
navigation, and opening/switching/closing the asset form, without horizontal
page overflow or uncaught JavaScript errors. No real holdings or providers
were used; full authenticated CRUD E2E, ARM64, and GitHub execution remain
unverified. Repository-wide lint is not claimed to pass.

### Portfolio totals correctness follow-up

- The active dashboard had its own totals loop; the previously audited
  calculator was instantiated but did not supply the visible totals. The
  dashboard now uses the tested
  [portfolio calculator](../frontend/src/lib/services/portfolioCalculations.ts).
  Its old totals cache and duplicate arithmetic were removed; sorting still
  has separate calculations and caching.
- Quote value and purchase cost are converted independently before subtraction.
  Purchase cost uses `buy_currency`, falling back only to an explicit asset
  currency. Missing currencies are not guessed, and failed conversions never
  add foreign amounts to target-currency totals.
- Value, yield, and performance are independently nullable. Missing quotes,
  unavailable costs, invalid FX responses, and numeric overflow produce
  `Unavailable` with an `Incomplete` status instead of invented numbers. Known
  zero quotes and zero purchase costs remain distinct from missing data; a
  zero investment basis has no defined percentage return.
- Quote loading no longer turns failures into a synthetic zero-dollar quote.
  The totals path uses the existing cached converter without forcing a provider
  refresh, retains usable stale FX on network failure, and rejects malformed
  conversion metadata. The batch API contract is unchanged.
- Each totals request snapshots assets and quotes. A revision check prevents
  older async results from replacing a newer currency/filter selection; pending
  totals are cleared so an old amount is not relabeled with the new currency.

Validation: 21 new public-service regressions use real FX/cache code with mocked
HTTP, bringing the unit suite to **59 passing tests across 3 suites**. Svelte
check reports zero errors and warnings; the production build and touched-file
formatting pass. Scoped ESLint comparison adds no diagnostics to the existing
baseline; repository-wide lint is not claimed to pass. Synthetic browser checks
at 1440px and 390px cover the worked currency example, filters, currency
switches, an obsolete delayed response, missing quotes, failed FX, and a usable
market value with unavailable purchase FX. No uncaught JavaScript errors or
horizontal page overflow were observed; the existing table remains scrollable.

No real holdings, credentials, databases, or providers were used. No backend,
storage, dependency, or rounding-policy changes were made. Individual row,
sorting, and chart calculations remain separate; full financial coverage,
authenticated CRUD E2E, and backend validation are not claimed by this pass.

### Shared position valuation and sorting follow-up

- Dashboard rows, financial sorting, and totals now consume one converted
  position snapshot from the existing portfolio calculator. This supersedes
  the earlier note about separate row/sorting arithmetic; charts remain
  independent and unchanged.
- Value, current unit price, purchase unit price, yield, and performance use
  the selected display currency. The original purchase amount and currency
  remain in the purchase-price tooltip and are not changed in storage.
- Removed the old sort cache and its incomplete invalidation keys. Sorting
  uses already-calculated values without fetching quotes or FX. Unavailable
  and inapplicable values sort last in both directions; zero and negative
  amounts remain real values. Aggregate returns retain investment weighting
  rather than averaging position percentages.
- Currency, filter, and quote changes replace both row and total snapshots.
  The revision guard rejects obsolete results, pending rows do not relabel old
  amounts, and teardown cancels the filter debounce and invalidates pending
  valuation results. Manual refresh and cache-status components are retained.
- Sort headers use native buttons with keyboard activation and `aria-sort`.
  Existing table layout, profit/loss styling, and mobile scrolling are retained.

Validation: 13 additional regressions bring financial/service sorting coverage
to **34 tests** and the full unit suite to **72 passing tests across 3 suites**.
Typecheck reports zero errors and warnings; formatting and production build
pass, with no new scoped ESLint diagnostics against the existing baseline.
Synthetic desktop (1440px) and mobile (390px) browser checks cover mixed
currencies, missing quotes/costs, a true zero quote, keyboard sorting in both
directions, filters, display-currency changes, original-cost tooltips, rejection
of a delayed CHF response, and manual refresh changing the active sort order.
The checked ascending/descending sort actions made zero additional quote/FX
HTTP requests; this is not a provider-load or application-wide benchmark.
No uncaught JavaScript errors or horizontal page overflow were observed.

No real holdings, providers, or databases were used. No backend, dependency,
storage, or rounding-policy changes were made; full authenticated CRUD E2E
and chart valuation correctness are not claimed. Standalone cell components
were retained rather than removed as an unrelated cleanup.

### Pre-publication financial review

- Quote loading now rejects superseded requests at the price-management owner,
  preventing an older load from replacing a completed forced refresh.
- Failed quote reloads retain validated prior quotes for requested assets,
  including true zero quotes; assets without usable prior data remain unavailable.
- FX validation also checks the backend's unrounded `amount * rate` contract
  with floating-point tolerance. Inconsistent results are unavailable, while
  valid negative cash conversions remain supported.

Seven additional HTTP-only regressions cover these review findings, bringing
the financial suite to **41 tests** and the full suite to **79 passing tests
across 3 suites**. The race, offline fallback, and malformed arithmetic cases
were observed failing before their fixes and passing afterward. Formatting,
typecheck (zero errors/warnings), production build, and baseline-relative
scoped ESLint checks pass.

The final production Docker image builds successfully. An isolated smoke test
with network disabled and a temporary tmpfs database passes application startup,
health, HTML, 20 referenced build assets, schema creation, and SQLite integrity.
No host database was mounted and no image was published.

## Initial audit priorities and evidence

| Priority | Observed behavior and evidence                                                                                                                                                                                                                                                                                      | Next deliverable and acceptance check                                                                                                                                                                                                                                                | Owner / effort                         |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| P0       | [Dockerfile](../Dockerfile#L4) builds with Node 18; [frontend package](../frontend/package.json) and lockfile use Vite 7.0.4, whose engines require `^20.19.0                                                                                                                                                       |                                                                                                                                                                                                                                                                                      | >=22.12.0`.                            | Align local, CI, and Docker on a maintained compatible Node release; preserve the lockfile unless an upgrade is approved. Clean `npm ci`, check, unit tests, and image build succeed on that runtime. | Backend + frontend / S |
| P0       | [Docker workflow](../.github/workflows/docker-build.yml) logs into the registry and sets `push: true` on both push and PR events, without test jobs. Fork PRs may fail authentication; trusted PRs may publish images before merge.                                                                                 | Separate PR validation from authorized publication; skip registry credentials/push/releases on PRs, minimize permissions, gate publication on tests, and cover PRs targeting `beta`. Verify the event matrix without publishing a trial image.                                       | Backend + reviewer / M                 |
| P0       | [Portfolio calculations](../frontend/src/lib/services/portfolioCalculations.ts#L99) retry failed FX conversion individually, then add raw foreign amounts to target-currency totals if retries fail. Missing prices are skipped; yield calculation also subtracts purchase price without using `buy_currency`.      | Define explicit incomplete/stale results; never label mixed units as a target-currency total. Test batch and individual FX failures, missing prices, and differing quote/purchase currencies with fixed rates.                                                                       | Frontend + backend contract review / M |
| P1       | [Asset schemas](../backend/app/schemas/asset.py#L7) accept plain floats and optional strings without explicit finite/range/domain constraints on create or update. [Storage](../backend/app/models/asset.py#L38) uses floating point.                                                                               | Agree whether zero positions, short positions, negative cash, and free acquisitions are valid. Reject non-finite input and invalid currencies/symbols as appropriate. Test POST and partial updates. Specify rounding with golden fixtures before considering any storage migration. | Backend / M                            |
| P1       | Two frontend unit suites exist under [service tests](../frontend/src/lib/services/__tests__/enhancedApi.test.ts). No backend test files or frontend E2E specs were found in this audit; [Playwright](../frontend/playwright.config.ts) starts only frontend preview.                                                | Establish executable unit configuration and isolated backend fixtures. Add financial, cache, auth, and API-contract regressions, then login/add/edit/delete/refresh E2E flows with a disposable API/database.                                                                        | Backend + frontend / M-L               |
| P1       | [Price endpoint](../backend/app/api/endpoints/price.py#L39) calls an async [pricing method](../backend/app/services/price_service.py#L25) that invokes synchronous Finnhub and yfinance operations directly.                                                                                                        | Measure health-request latency while a mocked provider blocks. Isolate blocking I/O or use an appropriate async client with bounded concurrency and timeouts; retain provider quotas and stale-cache behavior. Prove responsiveness under the same workload.                         | Backend / M                            |
| P1       | [Dashboard sorting](../frontend/src/routes/+page.svelte#L371) computes value, yield, and performance separately; those helpers independently request quotes and conversions. Caches may reduce actual network work.                                                                                                 | Count calculations, frontend requests, and provider calls separately. Derive sorting/display/totals from one quote snapshot when justified; test refresh races, currency changes, and invalidation.                                                                                  | Frontend / M                           |
| P1       | [Session validation](../backend/app/services/auth_service.py#L114) commits and refreshes last activity on each successful call. [Price endpoints](../backend/app/api/endpoints/price.py#L16) capture `SessionLocal`, while [shared dependency](../backend/app/db/database.py) supports a replaceable session maker. | Measure authenticated polling write load and inspect active transaction paths. Unify fixture/dependency ownership before tuning; test isolated databases, rollback, expiry, logout, and concurrent reads/refreshes. Avoid sharing an async session between concurrent tasks.         | Backend / M                            |
| P2       | [Dockerfile](../Dockerfile#L28) retains a compiler in the runtime image, has no non-root user, and makes the data directory world-writable. [Compose](../docker-compose.yml) persists SQLite under `/app/data`.                                                                                                     | Introduce a non-root runtime and narrowly writable data volume, separate build-only dependencies where useful, scan dependencies/images, and prove startup and backup/restore with existing volume ownership.                                                                        | Backend + reviewer / M                 |

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

| Measure               | Baseline method                                                                                | Acceptance criterion                                                                                                         |
| --------------------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| API responsiveness    | Compare health-request p50/p95 during idle and a fixed slow-provider simulation.               | Agree a latency budget before implementation; eliminate event-loop starvation under the same workload.                       |
| Request amplification | Count UI requests, unique symbols/pairs, provider calls, cache hits, and concurrent refreshes. | Warm-cache operations require zero provider calls; concurrent identical misses coalesce or obey an explicit provider budget. |
| Dashboard work        | Record sorting/total calculation counts and desktop/mobile browser traces.                     | Avoid redundant quote/conversion work for unchanged snapshots without stale totals after mutations or currency changes.      |
| SQLite contention     | Count writes and lock errors during authenticated polling plus manual refresh.                 | No lock failures in the controlled workload; reduce unnecessary writes without extending session validity incorrectly.       |
| Delivery cost         | Record compressed JS payload, build time, image size, and runtime memory.                      | Agree budgets from the baseline; split/lazy-load heavy charts only when the trace justifies it.                              |

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

### Initial baseline before implementation

`npm --prefix frontend run test:unit` ran with Vitest 3.2.4: **30 passed,
2 failed across 2 suites**. Application code and tests were unchanged.

- [Cache suite](../frontend/src/lib/services/__tests__/cacheService.test.ts#L71):
  "should fetch fresh data when cache is expired or forced" expected two fetch
  calls but observed one. Determine whether the test setup or cache contract
  is wrong before changing either.
- [API suite](../frontend/src/lib/services/__tests__/enhancedApi.test.ts#L173):
  the same-currency rate assertion rejects additional `fetched_at` and `source`
  fields. Confirm the response contract before changing the assertion or API.

Both failures are addressed in the implementation pass above. Keep this
initial result as history, not the current test status. Backend tests, frontend
typecheck/lint/build, E2E, container builds, and performance benchmarks were not
run during the initial documentation-only audit.

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
