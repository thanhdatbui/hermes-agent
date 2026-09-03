# Runtime app update and import reference

## OmniRoute-style local gateway

- Confirm the browser dashboard URL and displayed application version before changing anything.
- Use the dashboard's Security page to inspect `Require login`. If the user explicitly requests no password for a local-only dashboard, authenticate once through the UI, toggle it off, confirm the toggle is off after the page rerenders, and verify a fresh navigation no longer presents the login screen.
- For provider setup, distinguish the provider account connection from the gateway API key. The user adds the upstream provider account in the dashboard, then creates a separate local API key in the gateway's API-key manager for Hermes or another client.
- For proxy pools, use the dashboard path `Proxy/System → Proxy pool` (localized UI may call it `Nhóm proxy`). Open `More actions → Bulk import` (`More actions → Nhập proxy hàng loạt`). The supported text forms commonly include `NAME|HOST|PORT|USERNAME|PASSWORD|TYPE|REGION|STATUS|NOTES` and shorthand forms such as `host:port:user:pass`.
- Check the source workbook structure with a spreadsheet reader before importing: sheet names, header shape, and row count only. Never print rows containing username/password or API credentials.
- If the workbook contains credential-bearing proxy rows and the UI requires pasting bulk text, do not generate or expose the credential-bearing text in the chat transcript. Prefer a user-local paste into the dashboard, or request a sanitized file/credential-safe import path. Report the blocker plainly instead of claiming that the pool was imported.

## Browser verification pattern

1. Navigate to the exact local URL.
2. Take a fresh accessibility snapshot.
3. Use the current reference ID to click or type.
4. Take another snapshot immediately after the state change.
5. Reload/navigate afresh and verify persistence.

References become stale after navigation or rerender; never reuse an old ref ID for a different page state.

## Failure reporting

Use concise Vietnamese. Example:

- `Kết quả: Đã tắt yêu cầu đăng nhập; reload không còn trang login.`
- `Blocker: Workbook chứa user/password proxy; giao diện chỉ nhận bulk text. Chưa import để tránh làm lộ credential.`

Do not report tool internals such as approval-gate mechanics unless they are the actual user-facing blocker.
