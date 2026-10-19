# Cointainr

## Working agreements

- Preserve portfolio data, API contracts, and offline behavior. Use temporary
	databases and mocked market-data providers for tests; keep live holdings,
	credentials, and provider responses out of commits and prompts.
- Start from the owning code path and a falsifiable hypothesis. Make one scoped
	change, run its cheapest meaningful check, then expand only when needed.
- Follow applicable `.github/instructions/` guidance. Preserve the existing
	Svelte design system; this repository uses SvelteKit, not React.
- For backend changes, check whether the code uses `app.db.session` or
	`app.db.database` before choosing fixtures or modifying transactions.
- Read package scripts and test configuration before running checks. Existing
	test scripts do not imply complete test coverage or a working test setup.
- Use installed engineering skills when their workflow fits. Read the skill
	before invoking it; skills are optional tooling, not a required download.

## Repository agents

Select a focused agent from `.github/agents/`: `cointainr-planner` for evidence
and sequencing, `cointainr-backend` for API/data changes, `cointainr-frontend`
for Svelte behavior, and `cointainr-reviewer` for an independent read-only review.
Delegate only independent, explicitly scoped work; the caller owns integration
and validation. For optimization priorities, read `docs/OPTIMIZATION_ROADMAP.md`.

## Git workflow

- Inspect branch, status, and diff first. Preserve unrelated work. Create a
	branch, commit, or push only when the user authorizes that operation.
- Stage explicit paths or hunks, inspect the staged diff, check for secrets and
	generated files, and run the checks relevant to that change before committing.
- Keep each commit one reviewable purpose. Use `type(scope): imperative summary`
	(for example, `docs(agents): define repository workflows`); explain meaningful
	tradeoffs and verification in the body. Do not claim unrun checks passed.
- The current release workflow recognizes `[feat]`/`[minor]` and
	`[breaking]`/`[major]`, not Conventional Commit release semantics. Preserve
	that distinction until an explicitly approved release-policy change.
- Review findings before publication. Use a feature branch and PR when
	authorized; avoid direct pushes to `main` or `beta` by default because pushes
	trigger image publication. Confirm the target and deployment effects first.
- Use normal, non-force pushes. Report commit hashes, checks, and whether work
	was pushed. Leave authentication and signing credentials with the user.

## Agent skills

### Issue tracker

Track issues and specs as local Markdown under `.scratch/<feature>/`.
See [issue tracker conventions](docs/agents/issue-tracker.md) when creating,
fetching, or updating tickets and specs.

### Triage labels

Use the five default triage roles as local issue `Status:` values.
See [triage labels](docs/agents/triage-labels.md) when triaging issues.

### Domain docs

Use a single-context root glossary and `docs/adr/`.
See [domain documentation rules](docs/agents/domain.md) before exploring domain
concepts or proposing architectural changes.
