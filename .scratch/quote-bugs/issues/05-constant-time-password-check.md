# Password is compared with `==`

Status: ready-for-agent

`AuthService.validate_credentials` in `backend/app/services/auth_service.py`
checks `username == AUTH_USER and password == AUTH_PASSWORD`. Plain string
comparison can return early on the first different character, which leaks
timing. Use `secrets.compare_digest` on UTF-8 bytes for both values, and
evaluate both comparisons so a wrong username takes the same path.

Not pinned yet: add a test to `backend/tests/test_auth_modes.py` that valid,
wrong, and empty credentials keep their current results.
