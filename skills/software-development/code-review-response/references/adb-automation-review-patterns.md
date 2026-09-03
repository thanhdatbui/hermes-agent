# ADB / Android Automation Code Review Patterns

Domain-specific patterns for reviewing Android ADB-automation code (TikTok workflow, app testing, device farming).

## Core ADB Action Patterns to Verify

### Force-Stop + Launch

```python
# Expected pattern: force-stop → sleep → launch with fallback
adapter._adb.shell(["am", "force-stop", package], timeout=10, check=False)
time.sleep(2)

# Launch via monkey (preferred, more reliable across Android versions)
result = adapter._adb.shell(["monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"])
if not result.ok:
    # Fallback to am start
    result = adapter._adb.shell(["am", "start", "-n", f"{package}/.MainActivity"])
```

**Review questions:**
- Is `check=False` or equivalent non-fatal error handling used? Force-stop on a stopped app should never crash the workflow.
- Is there a sleep (1-2s) between force-stop and launch? Android needs time to clean up.
- Is there a fallback if `monkey` fails? Some devices lack monkey.
- Is `launch_app()` itself an independent method that also force-stops (defense-in-depth), or is the force-stop only in the caller (single responsibility)?
- Double force-stop (caller + callee) is **idempotent and harmless** — not a bug, but flag as minor if redundant.

### UI Dump (uiautomator)

```python
# Expected fallback chain for reading UI XML:
# Strategy 1: dump + exec-out cat (portable)
result = adb.shell(["uiautomator", "dump", "/sdcard/ui_dump.xml"])
cat_result = adb.shell(["cat", "/sdcard/ui_dump.xml"])
if cat_result.ok and cat_result.stdout.lstrip().startswith(("<", "<?xml")):
    return cat_result.stdout

# Strategy 2: dump + pull to temp file
dump_result = adb.shell(["uiautomator", "dump", "/sdcard/ui_dump.xml"])
pull_result = adb.run(["pull", "/sdcard/ui_dump.xml", temp_file])

# Strategy 3: content provider (Android 10+)
content_result = adb.shell(["content", "read", "--uri", "content://debug/ui"])
```

**Review questions:**
- Is the XML validated to start with `<` or `<?xml` before parsing? (Prevents garbage data from being treated as valid UI.)
- Are temp files cleaned up in a `finally` block?
- Does the error message list ALL strategies that failed, not just the last one?
- **Critical**: In dry-run mode, does `dump_ui()` return mock XML? If so, verify that `_wait_for_feed` / feed verification is NOT called in dry-run (the handler should return early before polling feed).

### Feed/Home Verification

```python
# Expected pattern: poll UI dump for known indicators
feed_indicators = [
    "for you", "for_you",       # English "For You" tab
    "following",                 # English "Following" tab
    "đề xuất", "đềxuất",        # Vietnamese "Suggested"
    "home_tab",                  # Common resource-id suffix
    "com.ss.android.ugc.trill:id/home",  # Full resource-id
]

deadline = time.time() + timeout
while time.time() < deadline:
    xml_text = adapter.dump_ui()
    xml_lower = xml_text.lower()
    for indicator in feed_indicators:
        if indicator in xml_lower:
            return True
    time.sleep(2)
return False  # timeout — no fake success
```

**Review questions:**
- Does the polling loop **always** return `False` on timeout? No `return True` anywhere except after genuine indicator match.
- Is the `timeout` parameter reasonable (30s for feed load)?
- Is the sleep interval (1-3s) between polls appropriate for the expected UI load time?
- Are indicators comprehensive for the app locale (English + Vietnamese = "for you" + "đề xuất")?
- Is `xml_lower` used for case-insensitive matching?
- **Edge case**: Does `dump_ui()` exception get caught so one failed dump doesn't end the poll loop early?
- **Visual-gate freshness (V5-1)**: if the loop falls back to a screenshot-based visual verdict (e.g. `_visual_feed_surface_visible`), does EACH verdict use a FRESH frame? Red flag: a helper returns a fixed path like `run_dir / "feed-visual-fallback.png"` whenever the file exists — that reuses a frame from an earlier `_wait_for_feed`/previous run and false-accepts feed after the screen changed. Expected: unique timestamped capture per verdict (`feed-visual-{seq}-{ts}.png`), or an explicitly-passed caller artifact used for the first verdict only; legacy fixed-name file unlinked on capture. A test named "..._reuses_existing_artifact_frame" asserting no-recapture-when-file-exists is asserting the bug — must be replaced, not kept.

### Tap / Input

```python
# Tap at coordinates
adb.shell(["input", "tap", str(x), str(y)])

# Text input
adb.shell(["input", "text", escaped_text])

# Key event
adb.shell(["input", "keyevent", str(keycode)])
```

**Review questions:**
- Does `tap()` raise a typed error on failure (e.g. `AccountSwitcherError("TAP_FAILED")`) or silently succeed?
- In dry-run, does `tap()` log the action without calling ADB?
- Are coordinates from UI element bounds (dynamic) or hardcoded (brittle)?

## Fallback Chain Patterns

### UI Element Location (Bottom Navigation)

A common pattern — finding the profile tab in TikTok's bottom navigation:

```
Strategy 1: Resource-ID match  → "com.ss.android.ugc.trill:id/profile_tab"
Strategy 2: Text match          → "Hồ sơ" / "Profile"
Strategy 3: Content-desc match  → "hồ sơ" / "profile"
Strategy 4: Bottom-nav scan     → Find elements in bottom 80% of screen, pick rightmost
Strategy 5: Resolution-aware    → `wm size` → width//5 + height-80
Strategy 6: Hardcoded coords    → Common resolution presets
```

**Review requirements:**
- Each strategy returns immediately on success (no double-tap).
- Strategy 4 computes `screen_height` from XML bounds dynamically, not from a hardcoded value.
- Strategy 5 uses `wm size` ADB command to get actual device resolution.
- Strategy 6 only fires after all other strategies fail (true last-resort).
- All strategies are wrapped in try/except so one XML parse failure doesn't cascade.

### Timeout → Escalation (MANUAL_REVIEW)

```python
# After all retries exhausted:
self.context.is_ui_unavailable = True
self.context.error = (
    f"[STATE_FAILED] Description of what went wrong. "
    f"Cần MANUAL_REVIEW: instructions for human operator."
)
return False

# Then in state machine transition:
# _transition(success=False) checks is_ui_unavailable → routes to MANUAL_REVIEW
```

**Review questions:**
- Is `is_ui_unavailable` set BEFORE returning `False`? (Order matters — `_transition` reads the flag.)
- Is the error message **actionable** in Vietnamese (or user's language)? It should tell the human what to do, not just what failed.
- Is the last_error captured from the final attempt and included in the message?
- Is a checkpoint saved with the correct `last_state` and error?

## Device Reboot Recovery (Soft Reboot)

When TikTok (or another background app) fails to load after repeated force-stop+launch, the workflow may attempt a **soft reboot recovery** — rebooting the device and retrying from scratch. This is a high-risk operation (device goes offline for 60–180s) so every step must be robust.

### Required 6-Step Sequence

```python
# Step 1 — Reboot
adb.shell(["reboot"], timeout=5, check=False)
# Should NOT block — the reboot command is fire-and-forget.
# Must check result.ok — if reboot command itself fails, bail immediately.

# Step 2 — Wait-for-device
adb.run(["wait-for-device"], timeout=120, check=False)
# BLOCKING — waits for the device to reappear in fastboot/adb mode.
# 120s is a conservative timeout (most Android devices boot in 45-90s).

# Step 3 — Poll sys.boot_completed=1 (60s)
deadline = time.time() + 60
while time.time() < deadline:
    prop = adb.shell(["getprop", "sys.boot_completed"], timeout=5, check=False)
    if prop.ok and prop.stdout.strip() == "1":
        boot_ok = True
        break
    time.sleep(2)
# sys.boot_completed is the canonical "boot finished" signal.
# Extra 5s settle after boot_completed before proceeding.

# Step 4 — Force-stop TikTok
adb.shell(["am", "force-stop", package], timeout=10, check=False)
# Idempotent, same as the pre-launch force-stop.

# Step 5 — Launch TikTok
adapter.launch_app(package)
# Reuses the same launch_app() with monkey + am start fallback.

# Step 6 — Wait for feed (30s)
self._wait_for_feed(adapter, feed_indicators, timeout=30)
# Same feed-indicator polling as the initiatial launch retries.
```

**Review questions:**
- Is every step individually logged with a `[STEP N/6]` tag so an operator can see where recovery failed?
- Does **every** step return `False` on failure (not `True` with a swallowed error)?
- Is `wait-for-device` an `adb.run()` call (not `adb.shell()`) — `run()` is the proper command for blocking ADB state transitions?
- Is `sys.boot_completed` polled with a 2s interval and 60s total timeout? (30s is too short — devices with encryption take longer.)
- Is there a small settle time (3-5s) after `boot_completed=1` before proceeding? (Some services register post-boot.)
- Is `check=False` used? A failure at the ADB transport layer is a recoverable condition, not a crash.
- Does `launch_app` reuse the existing method (not re-implementing monkey+am start inline)?
- Is the force-stop after reboot **redundant** with launch_app's internal force-stop? Harmless but flag as minor.

### Special: Config-Guarded Reboot

```python
# In config.py:
@property
def allow_device_reboot_recovery(self) -> bool:
    return bool(self._data.get("allow_device_reboot_recovery", False))
```

The reboot recovery path should be guarded by a config flag defaulting to `False` — recovering via device reboot is destructive (interrupts all other work on that device) and must be opt-in.

**Review questions:**
- Is the flag read from config and passed into the state machine context (not hardcoded)?
- Is the default `False`? (Reboot should never happen without explicit configuration.)
- Is the reboot code only reachable AFTER all non-reboot retries are exhausted? (The flag gates the fallback, not the core loop.)
- When reboot is disabled, does the code flow cleanly to MANUAL_REVIEW without checking or attempting the flag?

### Common Pitfalls

#### Reboot → Boot-Completed Timing
Devices with full-disk encryption (FDE) or File-Based Encryption (FBE) may show `sys.boot_completed=1` before the lock-screen PIN prompt is shown, but `uiautomator dump` will fail until the user unlocks. The workflow must handle this — if `dump_ui()` fails after boot_completed, the feed verification will also fail, correctly triggering MANUAL_REVIEW.

#### wait-for-device Exit Conditions
`adb wait-for-device` returns as soon as the device appears in `adb devices`, which is before boot completes. Do NOT treat step 2 as "device is ready" — it only means "device is in some ADB-visible state". Always follow with `sys.boot_completed` polling (step 3).

#### Dry-Run Safety for Reboot
In dry-run mode, `_handle_open_tiktok` must short-circuit at the top before reaching the reboot code path. Trace both paths (dry_run=True and dry_run=False) to confirm.

#### Capping Reboot Attempts
The reboot recovery fires once after 3 failed force-stop+launch attempts. There should not be a nested retry loop around the reboot itself — if the device reboots but TikTok still fails to load, the workflow escalates to MANUAL_REVIEW. Never auto-reboot a second time in the same job.

## Unlock Retry (Dumpsys-Verified)

Consumer-side unlock recovery after `prepare_device` reports `locked_or_secure` — the core swipe (85%→35%, 280ms) wasn't enough, so the consumer retries with more aggressive parameters (95%→25%, 500ms) and verifies via `dumpsys window policy`.

### Required Implementation Pattern

```python
_UNLOCK_RETRIES = 3
if readiness.unlock_state == "locked_or_secure":
    width, height = readiness.screen_size or (1080, 1920)
    for retry in range(1, _UNLOCK_RETRIES + 1):
        # Swipe from sát bottom edge (95% height), longer duration (500ms)
        adb_client.shell(["input", "swipe",
            str(width // 2), str(round(height * 0.95)),
            str(width // 2), str(round(height * 0.25)),
            "500"], timeout=10, check=False)
        time.sleep(1.5)

        # Verify unlock via dumpsys window policy
        policy = adb_client.shell(["dumpsys", "window", "policy"],
                                   timeout=10, check=False)
        if policy and policy.ok:
            if not _is_locked_in_dumpsys(policy.stdout):
                logger.info(f"Consumer swipe retry {retry} succeeded ✓")
                break
        else:
            logger.warning(f"dumpsys failed (retry {retry}) — sẽ retry")
    else:
        # for-else: only reached when break was NOT hit → all retries exhausted
        self.context.is_ui_unavailable = True
        self.context.error = "[DEVICE_LOCKED] ..."
        return False

# rotation check only reached after unlock confirmed or never needed
if readiness.rotation_locked is not True:
    ...
```

### Keyguard Detection Patterns (Module-Level Constants)

Only match **exact lock-state indicators** — NOT capability/debug fields.

```python
# CORRECT: Only match actual lock state, not capability flags.
# deviceHasKeyguard=true is a CAPABILITY (device supports keyguard)
# NOT a lock indicator — never match on it.
_LOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"mShowingLockscreen\s*=\s*true", re.IGNORECASE),    # AOSP standard
    re.compile(r"isStatusBarKeyguard\s*=\s*true", re.IGNORECASE),   # Some ROMs
)

def _is_locked_in_dumpsys(text: str) -> bool:
    return any(pattern.search(text) for pattern in _LOCKED_PATTERNS)
```

### Review Questions

- **Swipe parameters**: Does the retry use 95% height → 25% height (not the same 85%→35% as core)? Duration 500ms (not 280ms)?
- **Verification method**: Is unlock verified via `dumpsys window policy` (not blind success)? Are the keyguard patterns correct — only `mShowingLockscreen` and `isStatusBarKeyguard`? Do NOT include broader patterns like `keyguard(?:Showing|Locked)?\s*=\s*true` that match `deviceHasKeyguard=true` (a **capability** flag, not lock state).
- **dumpsys failure tolerance**: If the `dumpsys` command itself fails (adb error), does the code log a warning and CONTINUE to the next retry (not immediately give up)?
- **for-else pattern**: Does the code use Python's `for...else` so the `else` block only fires when `break` is NOT reached (i.e., all retries exhausted)? If using a flag variable instead, flag as minor style issue.
- **Escalation**: On retry exhaustion, does it set `is_ui_unavailable=True` and `return False` (→ MANUAL_REVIEW via transition map)? Is the error message actionable in the user's language?
- **No hard guard on `locked_or_secure`**: The `if readiness.unlock_state == "locked_or_secure":` gates the retry logic, NOT the entire handler. If the device is already unlocked, the retry is skipped cleanly and falls through to the rotation check. The code must NOT hard-fail just because unlock_state isn't perfectly "unlocked" — the consumer retry handles that.
- **Screen size provenance**: Is screen size sourced from `readiness.screen_size` (already fetched by `prepare_device`), not a separate `adb shell wm size` call? Fallback safe for the target farm devices (e.g. `(1080, 1920)` for Samsung S7).
- **Rotation check ordering**: Is the `rotation_locked` check placed AFTER the unlock retry block (not before)? Lock screen prevents `settings put system` commands from applying.
- **No-op after success**: After the consumer swipe succeeds, look for a stale `readiness = readiness` (no-op) assignment instead of updating `readiness.unlock_state`. This is cosmetic — the flow only checks `rotation_locked` afterward — but it's a code-quality flag. The readiness object still claims `locked_or_secure` even though the device was successfully unlocked.

### Common Pitfalls

#### for-else Mistaken as if-else
The `for...else` in Python is notorious — the `else` runs when the loop completes normally (no `break`). A reviewer who misses this will misunderstand the exhaustion logic. Confirm the code uses `break` on success and `else:` only for the all-failed path.

#### Blind Proceeding After Core `locked_or_secure`
Without the consumer retry, a handler that skips the `unlock_state` check entirely will proceed as if the device is ready, only to have TikTok open on a locked screen → stuck at SplashActivity → `_wait_for_feed` fails → PROFILE_ROOT_NOT_CONFIRMED cascade → MANUAL_REVIEW with an unhelpful error message. The unlock retry catches this early with a clear escalation path.

#### Rotation Check Before Unlock
If the rotation check (`settings put system user_rotation`) runs while the device is still locked, the ADB command may silently fail or apply only after unlock. Always place the rotation check after the unlock retry block.

#### deviceHasKeyguard is a Capability, Not Lock State
`deviceHasKeyguard=true` in dumpsys output means "this device model supports a keyguard UI" — it is a **capability/debug flag**, not a lock indicator. Matching on it causes false positives: the workflow thinks the device is locked when it isn't, blocking progress with a fake "unlock failed" error. Only match the two exact fields that indicate an active lockscreen:
- `mShowingLockscreen=true` — the actual lockscreen is visible
- `isStatusBarKeyguard=true` — the status-bar keyguard is engaged

Avoid generic patterns like `keyguard(?:Showing|Locked)?\s*=\s*true` whose optional group matches `*keyguard=true` broadly.

## Dry-Run Safety Verification

Dry-run mode must NEVER execute real ADB commands. Every method should:

```python
if self.dry_run:
    logger.info(f"[DRY-RUN] Would <action>")
    return True  # or return mock data
```

**Review questions:**
- Does every ADB-executing method check `self.dry_run` at the top?
- Does the state machine handler for the relevant state also check dry-run early (e.g. `_handle_open_tiktok` returns immediately in dry-run)?
- Does `dump_ui()` return mock XML in dry-run that won't accidentally trigger real behavior?
- Does tap/click type methods NOT call ADB in dry-run?
- **Double-check**: If the state machine returns early on dry-run, is the feed-verification polling really never reached? Trace both paths.

## Common Pitfalls

### Redundant Force-Stop
When `_handle_open_tiktok` force-stops AND calls `launch_app` which also force-stops — harmless but indicates unclear responsibility boundary between caller and callee. Flag as minor.

### Missing Vietnamese Locale Awareness
TikTok in Vietnam uses Vietnamese UI strings. Verification must check both English and Vietnamese indicators:
- "For You" / "Dành cho bạn"
- "Following" / "Đang Follow"
- "Suggested" / "Đề xuất"
- "Home" / "Trang chủ"

### Waking Screen Before Dump
If the device screen is off, `uiautomator dump` may return empty or stale data. Ensure wake/unlock happens before feed verification. The `prepare_device()` call should handle this.

### Mock XML with Feed Indicators
If the dry-run mock XML contains "home_tab" (a feed indicator), and a state machine handler does NOT return early in dry-run before `_wait_for_feed`, the feed check could falsely pass. Always ensure the handler short-circuits before feed polling in dry-run.
