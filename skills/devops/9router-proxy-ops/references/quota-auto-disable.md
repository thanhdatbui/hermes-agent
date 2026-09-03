# Quota auto-disable: Antigravity/Gemini/Claude

## Root cause pattern

The quota dashboard has two separate paths:

- Auto-refresh fetches `/api/usage/<connectionId>` and updates displayed quota.
- `Turn off Empty` is a separate bulk `PUT /api/providers/<id>` action. Its presence does not mean auto-refresh disables accounts.

A common bug is checking only `used/total`. Antigravity quota responses also expose `remainingPercentage`; the live response used `used: 1000`, `total: 1000`, `remainingPercentage: 0` for depleted Gemini and Claude entries.

## Safe depletion predicate

Use this provider-agnostic order per quota entry:

1. Ignore `unlimited: true`.
2. Accept an entry when `total > 0`, or when a provider-specific remaining field such as `remainingPercentage` is present.
3. Entry is depleted when `remainingPercentage <= 0`; otherwise when `remaining <= 0`; otherwise when `used >= total`.
4. Auto-disable only when there is at least one usable quota and every usable quota is depleted.
5. Keep the connection enabled when any quota has remaining capacity or the API returned no usable quota data.
6. Limit the action to the intended provider (Antigravity in this incident) and call the existing provider PUT endpoint; do not write SQLite directly.

## Live verification recipe

Authenticate, fetch the paginated client list, fetch `/api/usage/<id>` for each target provider, then verify `providerConnections.isActive` in the database. For this incident the resulting state was:

- `thanhdatbui19951@gmail.com`: disabled
- `jinrakal@gmail.com`: disabled
- `marcusephillips52sns@gmail.com`: disabled
- `dinhlan24072000@gmail.com`: disabled
- accounts with remaining quota stayed enabled

Do not rely on the screenshot alone. A browser reload can redirect to `/dashboard`; navigate back to `/dashboard/quota` after login.

## Emergency compiled-bundle patch verification

If source/build files are unavailable and an operational patch must be applied to the installed bundle:

1. Create a sibling backup before editing.
2. Patch only the quota page bundle and keep the provider PUT behavior narrow.
3. Run `node --check <bundle>`.
4. Assert the bundle contains both the depletion predicate and the auto-disable PUT/log call.
5. Verify live API plus database state.
6. Record that the bundle patch is temporary and should be regenerated from source on the next package build/update.

This evidence came from 9Router v0.5.55 on Windows and should be revalidated if the quota response schema or build output changes.
