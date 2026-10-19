---
description: "Use for Cointainr FastAPI endpoints, pricing and FX services, SQLAlchemy, SQLite, authentication, and backend tests."
applyTo: "backend/**"
---

# Backend

- Trace the endpoint to the service and CRUD function before changing behavior.
  Preserve existing API fields, status codes, and optional-auth behavior unless
  the requested change explicitly revises the contract.
- Determine whether a caller uses `app.db.session` or the replaceable dependency
  in `app.db.database`. Override the actual owner in tests; use temporary SQLite
  databases and mocked providers, never the user's configured database.
- Keep session ownership and transaction boundaries explicit. Each concurrent
  task needs its own async session. Validate rollback and exception paths.
- Isolate blocking provider work from async request handlers; set bounded
  timeouts/concurrency and respect rate limits. Preserve last-known prices and
  their timestamps when providers fail.
- Validate finite financial inputs and currency units. Agree on valid zero,
  negative, and fractional positions before imposing new constraints. Specify
  rounding before changing numeric storage or response serialization.
- Keep credentials, session tokens, and holdings out of logs and fixtures.
  Test auth enabled/disabled/demo modes when touching authentication or startup.
- For persisted schema changes, define backup, restore, migration, and rollback
  checks first. Startup and demo cleanup must preserve non-demo holdings.
- Inspect `backend/requirements.txt` and the selected interpreter before running
  checks. Dependency packages can be transitive; absence of a direct import is
  not evidence that a requirement can be removed.
