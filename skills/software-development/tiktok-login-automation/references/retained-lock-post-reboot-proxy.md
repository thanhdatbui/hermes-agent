# Post-reboot proxy restoration while reconcile retains the device lock

## Failure class

A reconcile runner may intentionally retain machine+serial locks across:

`inventory -> reboot -> login -> verify`

If reboot removes `tun0`, a separate proxy watcher cannot restore VPN because it needs the same lock. Waiting for the watcher creates a lock cycle:

- reconcile owns the lock and waits for VPN readiness;
- watcher waits for the lock before calling Vi Changer;
- reconcile times out without reaching login.

A live VPN verifier only fixes stale/missing readiness markers when VPN is already active. It does **not** restore a tunnel lost during reboot.

## Correct architecture

1. Keep the parent reconcile lock for the whole goal.
2. Use the shared guarded reboot API with a post-reboot callback (`reboot_and_restore(..., wait_for_proxy_ready_after_reboot=...)`) rather than a helper that only waits for watcher proof.
3. The callback calls the existing proxy provider/primitive directly under the retained parent lock.
4. Before loading a proxy mapping or calling `START_VPN`, the provider must verify both central lock files still match the parent:
   - host;
   - PID;
   - machine;
   - serial;
   - lock ID.
5. Load the exact machine+serial proxy mapping in memory. Never print it, pass it on the command line, or persist it in artifacts.
6. Reuse the provider's existing `set_proxy` / Vi Changer `START_VPN` primitive; do not recreate the flow with taps.
7. Continue only after both `tun0` UP and Android VPN `CONNECTED/VALIDATED` proof.
8. Parent-lock mismatch, ambiguous mapping, provider timeout, or failed VPN verification fails closed and retains recovery artifacts.

## Logged-out Profile is not an account-switcher navigation failure

On TikTok 46.x, a device with no logged-in accounts may show a Profile containing all of:

- `Hồ sơ` / `Profile`;
- `Đăng nhập vào tài khoản hiện có` / `Log in to an existing account`;
- a clickable `Đăng nhập` / `Log in` CTA.

There is no sticky username or switcher anchor. When all semantic markers are present, inventory should return an empty account set so reconcile treats every expected workbook ID as device-missing and enters the normal login flow. A generic `Đăng nhập` string alone is insufficient.

A common first-run sequence is:

1. Feed tutorial `Vuốt lên để xem thêm` blocks bottom navigation -> perform one upward swipe and recapture.
2. Tap Profile and recapture.
3. Dismiss only the topmost known layer, one action per recapture (for example Google re-login sheet, then loading overlay, then TikTok login modal).
4. Confirm the logged-out Profile semantic signature.

If XML is non-XML but screenshot remains healthy, continue the screenshot-guided one-action/recapture loop; XML failure alone is not `FINAL_BLOCKED`.
