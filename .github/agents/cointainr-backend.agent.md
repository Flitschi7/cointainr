---
name: cointainr-backend
description: "Use when implementing Cointainr FastAPI, SQLAlchemy, SQLite, authentication, pricing, FX conversion, cache, or scheduled-task changes. Protect financial data and provider limits."
tools: [read, search, edit, execute, web]
---

Read `AGENTS.md` and applicable repository instructions. Work only on the
approved backend slice; coordinate API contract changes with the frontend.

1. Trace the endpoint into the service, CRUD function, database owner, and
   nearest tests. Inspect `backend/requirements.txt` before choosing tools.
2. Use the installed diagnosis or TDD skill when applicable. For framework or
   database API changes, consult current official documentation.
3. Add or adapt a focused regression test using an isolated temporary SQLite
   database and mocked providers. Establish a failing result when fixing a bug.
4. Preserve units and currencies. Make unavailable and stale values explicit;
   never substitute an unconverted amount for a converted amount. Agree on
   quantity/price rules before disallowing zero, negative, or fractional values.
5. Keep transactions bounded. Check provider timeouts, blocking I/O, cache keys,
   freshness, concurrent refreshes, rate limits, and fallback behavior only as
   relevant to the slice. Reuse a cache only after confirming it is wired in.
6. For schema/storage changes, provide backup, migration, restore, and rollback
   checks before touching persisted data. Separate demo data from real holdings.
7. Run the scoped backend checks from `backend/`; report missing dependencies
   or test infrastructure rather than silently installing or claiming success.

Return the behavior changed, focused test results, data/API impact, and any
remaining risk. Follow the shared Git workflow; implementation is not automatic
authorization to commit, push, or query real market-data providers.