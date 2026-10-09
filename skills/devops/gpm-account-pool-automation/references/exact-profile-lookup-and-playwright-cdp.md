# Exact GPM profile lookup and Playwright/CDP interaction

## Profile lookup
The default `/api/v3/profiles` response may be paginated or limited to 50 entries. Do not conclude that an account is missing from the first response. Query by exact email, then verify the returned profile name, profile ID, and proxy before opening.

Example:
```bash
curl -s 'http://127.0.0.1:19995/api/v3/profiles?search=duongkien12022001%40gmail.com'
```

## Open and verify
1. Start only the exact profile with `/api/v3/profiles/start/{id}`.
2. Read the returned `remote_debugging_address`.
3. Connect using Playwright `chromium.connectOverCDP('http://127.0.0.1:<port>')`.
4. Enumerate pages and verify the target account/profile before any logout, OAuth, or onboarding.
5. Use bounded navigation/screenshot timeouts. A CDP connection alone is not proof that the visible target is ready; `chrome://newtab` or a hanging screenshot requires target diagnosis, not blind clicks.

## Safety
- Do not use generic desktop automation as a substitute for Playwright/CDP on GPM profiles.
- Do not logout, reauthenticate, change project IDs, or onboard until the exact account is visibly verified.
- Preserve proxy/profile isolation: one target account per GPM profile/session.
