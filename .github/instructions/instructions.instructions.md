---
description: "Cointainr repository context, architecture, and pointers to shared workflows."
applyTo: "**"
---

# Cointainr

Cointainr is a self-hosted portfolio tracker. Preserve user ownership of
holdings, reliable currency valuation, and useful offline behavior.

## Sources of truth

- Read `AGENTS.md` for working agreements, agent roles, skill routing, and Git
  authorization. Keep those rules there rather than duplicating them here.
- Consult `docs/OPTIMIZATION_ROADMAP.md` when choosing optimization work; verify
  its findings against current code before implementing them.
- Read `docs/agents/issue-tracker.md` when creating or updating local tickets.
- Treat package manifests, configuration, and active call sites as authoritative
  for versions, commands, providers, and defaults.

## Architecture

- `frontend/`: SvelteKit with TypeScript, Tailwind CSS, and Chart.js. The static
  adapter builds files that FastAPI serves; this is not a React application.
- `backend/app/`: FastAPI endpoints, SQLAlchemy async sessions, SQLite models,
  pricing/FX providers, caches, authentication, and scheduled tasks.
- `Dockerfile` and `docker-compose.yml`: single-container deployment with a
  persistent SQLite volume. Preserve volume paths during deployment changes.

Keep plans distinct from implemented behavior. Do not describe automatic
backups, provider fallbacks, or analytics as available until their active
implementation and checks establish that they work.
