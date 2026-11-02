# Session module owns token extraction and cleanup

Status: ready-for-agent
Blocked by: none

Spec: [Implementation decision 7](../spec.md#7-session-module-report-07).

`auth_middleware._extract_session_token` accepts a cookie, Bearer and
`X-Session-Token`; `endpoints/auth.get_session_token_from_request` accepts only
a cookie and Bearer, so `/logout` and `/status` miss sessions sent in the
header. The middleware also looks the session up twice per request, and
`demo_service._cleanup_sessions` deletes sessions with raw SQL.

## Decisions

- One module: `session_from(request) -> Session | None` (cookie, Bearer,
  `X-Session-Token`, in that order; one DB lookup) and `purge(now) -> count`,
  plus a purge-all for the demo reset.
- The middleware stores the session on the request; `/logout` and `/status`
  read it from there or call `session_from`. Remove the unread
  `request.state.username`.
- The demo reset uses the module instead of raw deletes.
- Login, the constant-time credential check and the off/on/demo modes are
  unchanged.

## Tests

- First, in `test_auth_modes.py`: log in, then call `/logout` and `/status`
  with the token in `X-Session-Token` (fails today).
- Existing auth mode tests pass unchanged.
