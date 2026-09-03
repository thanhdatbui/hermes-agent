# Reconcile guided recovery patterns

## Completion gate

`DONE: result=...`, exit code `4`, `recovery`, `locked`, timeout, or an empty `login_attempts` list are detection outcomes, not completion. Read the per-target summary, retain/take over the target lock only after proving the same-host owner PID is dead, and recapture the live state before choosing a handler.

## Reboot while reconcile retains the device lock

### Failure cycle

1. Reconcile retains machine+serial lock across inventory → reboot → login → verify.
2. Reboot drops `tun0`.
3. Proxy watcher needs the same lock to call Vi Changer.
4. Reconcile waits for proxy readiness while preventing the watcher from restoring it.

Do not release the goal lock merely to let the watcher race in. Use `reboot_and_restore()` with a post-reboot callback that restores the mapped proxy under the existing parent lease.

### Parent-lock provider contract

A proxy provider called under a retained parent lock must verify both lock files match all of:

- machine and serial;
- current host;
- parent PID;
- parent lock ID.

Only then load the exact machine+serial proxy mapping in memory, invoke the existing Vi Changer `START_VPN` primitive, and verify both `tun0` and Android VPN `CONNECTED/VALIDATED`. Never print or pass the proxy on the command line.

### Readiness verifier propagation

If `acquire_device_lock(..., live_vpn_verifier=...)` first calls `wait_for_proxy_ready()`, it must pass that verifier into the wait. Otherwise a stale `proxy_pending` marker times out before the live verifier runs. Test this propagation explicitly; a mock that only records “wait called” will miss the regression.

## Profile → account switcher handoff

Once `open_profile_root()` returns confirmed Profile XML, pass that exact payload into:

```python
open_switcher(..., pre_confirmed_xml=profile_xml)
```

Do not discard it and re-dump/re-navigate between Profile and switcher. On TikTok 46.x, an extra transition can leave the app back on Home feed and produce a misleading `SWITCHER_ANCHOR_AMBIGUOUS`.

For TikTok 46.2.3 at 1080×1920, observed semantic nodes include:

- Profile bottom tab: `content-desc=Hồ sơ`, center near `(972,1857)`;
- profile name/chevron button: resource suffix `sai`, bounds around `[36,249][375,330]`;
- Add Friends is a separate person-plus control near the upper-right and must never be treated as the switcher anchor.

A feed XML containing `For You/Friends/Following` is not evidence of an anchor problem. First prove Profile remained selected.

## Guided popup ladder

Use screenshot + bounded XML and one action per recapture:

1. Feed tutorial `Vuốt lên để xem thêm`: one upward swipe, recapture.
2. Android `GrantPermissionsActivity`: use automation-core `packageinstaller_permission` detector and semantic deny control.
3. Google re-login sheet: close only the topmost sheet, recapture.
4. TikTok login modal: close only when diagnosing the Profile state; do not enter credentials through the wrong layer.
5. Explicit save-login-info prompt: follow project policy (`Để sau`/`Not now` when inventory must continue without persisting login info). Require save-login markers; never tap a generic `Để sau` alone.

## Logged-out Profile

A logged-out Profile has no username/header or switcher anchor. Classify it only with a compound semantic signature such as:

- Profile/Hồ sơ marker;
- “Log in to an existing account” equivalent;
- login CTA.

For inventory, return an empty device account set so reconcile can enter the normal missing-account login flow. Do not reboot repeatedly for “account switcher navigation failed” when the device is simply logged out.

## UI dump hangs

If an autonomous helper or follow-up recapture hangs:

- external watchdog the whole process tree;
- verify the owner PID is dead before takeover;
- preserve the last screenshot/XML/foreground artifact;
- switch to guided screenshot flow when XML is missing/non-XML but screenshot and VPN are healthy.

Do not rerun the full reconcile command merely because a UI dump failed.
