# Batch Aggregator: session_lost vs challenge Partitioning & Fallback Invariants

## Context & Architecture
`automation_core.batch_aggregator` partitions machine failures into distinct failure buckets:
1. `session_lost_failures`: Hard auth loss (e.g. "logged out", "session expired", "văng", "đăng nhập lại"). Triggers `[P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`.
2. `challenge_failures`: Captcha / verification / checkpoint where session is not lost (e.g. "manual_challenge", "captcha", "checkpoint", "verify"). Triggers `[CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]`.
3. `auth_failures`: Legacy union parameter (`session_lost_failures + challenge_failures`).

## Critical Pitfall: Falsy Empty Lists in Fallback Logic
When calling `format_alert_message(...)` from `evaluate_batch(...)`:
Passing `session_lost_failures=session_lost_failures if session_lost_failures else None` turns an empty list `[]` into `None`.

If `format_alert_message` contains naive fallback logic:
```python
# BUGGY:
if session_lost_failures is None and auth_failures is not None:
    session_lost_failures = auth_failures
```
When a batch has **only challenge failures**:
- `session_lost_failures` is `[]` -> becomes `None`
- `challenge_failures` is `[m1]`
- `auth_failures` is `[m1]` (truthy)
- Result: `session_lost_failures` was incorrectly set to `auth_failures`, causing challenge failures to falsely trigger `P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT`.

## Required Fix & Pattern
1. In `format_alert_message`, only fall back to `auth_failures` if **neither** specific list was provided (legacy callers):
```python
if session_lost_failures is None and challenge_failures is None and auth_failures is not None:
    session_lost_failures = auth_failures
```
2. In caller `evaluate_batch`, always pass `[]` instead of `None` when the lists are empty:
```python
session_lost_failures=session_lost_failures if session_lost_failures else [],
challenge_failures=challenge_failures if challenge_failures else [],
```
This guarantees `session_lost_failures is None` will evaluate to `False` when evaluating partitions in `evaluate_batch`, preventing accidental fallback even if legacy checks change.

3. When testing alert messages for distinct categories:
- Explicitly test the mixed case: batch with both `session_lost` and `challenge` errors.
- Explicitly test the exclusive case: batch with `challenge` only must assert `P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT not in report.alert_message`.
- Explicitly test the exclusive case: batch with `session_lost` only must assert `CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI not in report.alert_message`.

## Pitfall: Composite Blocker Types Containing 'login' (e.g., login-gms-verification)
When runners return composite error types like `error_type='login-gms-verification'` with `error_message='manual_challenge marker detected'`:
If keywords are checked across the concatenated string `f"{m.error_type} {m.error_message}"` with `session_lost_failures` evaluated first:
- The keyword `"login"` inside `login-gms-verification` causes the machine to get classified into `session_lost_failures`.
- This falsely triggers `[P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]` when it is actually an in-session challenge.

### Rule & Pattern
Prioritize challenge detection first and exclude composite `login-gms-verification` from triggering challenge on type alone:
```python
challenge_failures = [
    m for m in failed
    if any(kw in (m.error_message or "").lower() for kw in CHALLENGE_KEYWORDS)
    or (
        (m.error_type or "").lower() != "login-gms-verification"
        and any(kw in (m.error_type or "").lower() for kw in CHALLENGE_KEYWORDS)
    )
]
session_lost_failures = [
    m for m in failed
    if m not in challenge_failures
    and (
        any(kw in (m.error_message or "").lower() for kw in SESSION_LOST_KEYWORDS)
        or any(kw in (m.error_type or "").lower() for kw in SESSION_LOST_KEYWORDS)
    )
]
```
Ensure a regression test covers `MachineResult(serial='...', error_type='login-gms-verification', error_message='manual_challenge marker detected')`.

## Canonical API Signatures & Test Authoring Pitfalls
When writing new tests or adapting requested test cases into `tests/test_batch_aggregator.py`, beware of draft/spec snippets using non-existent fields:
1. **`MachineResult` Constructor**:
   - ❌ DO NOT USE: `MachineResult(machine="M01", serial="serial1", success=False, error="...")`
   - ✅ CANONICAL: `MachineResult(serial="M01", succeeded=False, error_type="account missing", error_message="...", step_id="...")`
   - Key fields: `serial: str`, `succeeded: bool`, `error_type: Optional[str]`, `error_message: Optional[str]`, `step_id: Optional[str]`, `skipped: bool = False`.

2. **`evaluate_batch` Parameters**:
   - ❌ DO NOT USE: `aggregate_batch_run` (does not exist in `automation_core.batch_aggregator`)
   - ❌ DO NOT USE: `evaluate_batch(results, batch_total=4, error_rate_threshold=0.3, error_count_threshold=2)`
   - ❌ DO NOT USE: `machine_results=[...]`, `status="manual-needed"`
   - ✅ CANONICAL: `evaluate_batch(results: list[MachineResult], min_rate=0.3, min_count=2, script_name=None)`

3. **`BatchAggregationReport` Attributes**:
   - ❌ DO NOT USE: `report.failed_machines`, `report.systemic_errors` (as object list with `.error_count` or `.machines`)
   - ✅ CANONICAL:
     - `report.failed_count: int`
     - `report.systemic_signatures: dict[str, list[MachineResult]]` (keys are normalized signatures, values are lists of `MachineResult`)
     - `report.sporadic_signatures: dict[str, list[MachineResult]]`
     - `report.session_lost_count: int`, `report.challenge_count: int`, `report.skipped_count: int`

## Pitfall: Patch Tool Mangling on Adjacent List Comprehensions
In `evaluate_batch`, `challenge_failures` and `session_lost_failures` are adjacent list comprehensions iterating over `[m for m in failed if ...]`.
Because both list comprehensions share very similar structure, the Hermes `patch` tool's fuzzy-matching heuristics can inadvertently match and overwrite `session_lost_failures = [...]` when attempting to patch `challenge_failures = [...]`.
This immediately leads to `NameError: name 'session_lost_failures' is not defined` across all batch aggregator tests.

### Prevention Rule
Always include sufficient unambiguous surrounding context in `old_string` when patching `challenge_failures` or `session_lost_failures`:
- Include lines above (e.g. `sporadic[sig] = machines`) or lines below (e.g. `auth_failures = session_lost_failures + challenge_failures`).
- Always run `git diff` immediately after patching to verify that `session_lost_failures` was not accidentally replaced or deleted.

## Pitfall: False Positive 'profile verification' in Challenge Detection
`CHALLENGE_KEYWORDS` contains `"verification"` and `"verify"`.
When a runner fails during post-swipe follower count or profile telemetry (e.g. `profile verification navigation-failed: focused package unavailable`), the substring `"verification"` matches and falsely categorizes the failure as `challenge_failures`, triggering `[CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]` on Telegram even though the session completed all video swipes and the TikTok account was never challenged or captcha-blocked.

### Rule & Pattern
Strip `"profile verification"` when evaluating `CHALLENGE_KEYWORDS`:
```python
challenge_failures = [
    m for m in failed
    if any(
        kw in (m.error_message or "").lower().replace("profile verification", "")
        for kw in CHALLENGE_KEYWORDS
    )
    or (
        (m.error_type or "").lower() != "login-gms-verification"
        and any(
            kw in (m.error_type or "").lower().replace("profile verification", "")
            for kw in CHALLENGE_KEYWORDS
        )
    )
]
```
Real captcha/challenges during profile steps will still match because keywords like `"captcha"`, `"manual_challenge"`, or `"checkpoint"` remain untouched.

## Pitfall: Canary Machine Command Rendering 'N/A' on Sporadic Failures
In `format_alert_message`, `canary_candidates` only collects serials from `systemic_signatures`. When a batch has failures but 0 systemic clusters (all sporadic below rate/count thresholds):
`systemic_signatures` is empty `->` `canary_candidates` is empty `->` canary command renders as `python D:/Taadaa/tools/inspect_machine.py N/A`.

### Rule & Pattern
Always provide fallback candidate serials in priority order, log structured telemetry for observability, and expose `canary_machine` on `BatchAggregationReport`:
```python
canary_machine = "N/A"
canary_source = "none"
if canary_candidates:
    canary_machine = canary_candidates[0]
    canary_source = "systemic"
elif challenge_failures:
    canary_machine = challenge_failures[0].serial
    canary_source = "challenge_fallback"
elif session_lost_failures:
    canary_machine = session_lost_failures[0].serial
    canary_source = "session_lost_fallback"
elif auth_failures:
    canary_machine = auth_failures[0].serial
    canary_source = "auth_fallback"
logger.info("Canary target selected: machine=%s source=%s", canary_machine, canary_source)
```

In `evaluate_batch`, compute `canary_machine` using the identical fallback logic and populate:
- `BatchAggregationReport.canary_machine: Optional[str] = None`
- `to_dict()["canary_machine"] = self.canary_machine`
This enables consumers and automated tests to assert `report.canary_machine == "..."` programmatically without regex-parsing `report.alert_message`.

## Pitfall: False Positive 'verify' / 'did not verify' in Challenge Detection
`CHALLENGE_KEYWORDS` historically contained bare `"verify"`.
When any assertion, post-action check, or recapture fails with phrasing such as:
- `"Add phone close recapture did not verify a known TikTok screen with TikTok focus: unknown"`
- `"could not verify live proxy ip"`
- `"failed to verify selected account"`

The bare `"verify"` substring matches, falsely categorizing the sporadic capture or navigation error into `challenge_failures`. This immediately triggers `[CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]` on Telegram even when 0 systemic clusters exist and the account was never presented with a real captcha/checkpoint.

### Rule & Pattern
1. Remove bare `"verify"` from `CHALLENGE_KEYWORDS`. Use explicit challenge terms: `"verification"`, `"manual_challenge"`, `"checkpoint"`, `"captcha"`, `"xác minh"`, `"xac minh"`.
2. Add explicit `CHALLENGE_EXCLUSIONS` for negated assertion phrases:
```python
CHALLENGE_EXCLUSIONS: tuple[str, ...] = (
    "did not verify",
    "failed to verify",
    "could not verify",
    "cannot verify",
    "unable to verify",
    "recapture did not verify",
)
```
3. Guard `challenge_failures` evaluation with both exclusions and specific keywords:
```python
challenge_failures = [
    m for m in failed
    if not any(ex in (m.error_message or "").lower() for ex in CHALLENGE_EXCLUSIONS)
    and (
        any(kw in (m.error_message or "").lower() for kw in CHALLENGE_KEYWORDS)
        or (
            (m.error_type or "").lower() != "login-gms-verification"
            and any(kw in (m.error_type or "").lower() for kw in CHALLENGE_KEYWORDS)
        )
    )
]
```

## Remote ADB Transport Stale / Timeout Recovery
On dual-cluster setups with remote ADB hosts (e.g. Admin Farm `192.168.110.119:5037`):
A single device socket may hang, causing `inspect_machine.py` or `adb shell` to time out after 10.0s (`Model: ERROR: Command ... timed out`).
- ❌ CẤM: Restart toàn bộ adb server trên host remote làm gián đoạn các máy đang chạy khác.
- ✅ O(1) Targeted Recovery:
  `adb -H 192.168.110.119 -P 5037 -s <serial> reconnect`
  Lệnh này tái kết nối riêng socket transport của serial đích mà không chạm vào 79 thiết bị còn lại. Ngay sau đó `inspect_machine.py <N>` sẽ trả về kết quả tức thì.

## Account Switcher & Profile Root Navigation Exclusions from Session Lost (2026-10-02)
- **Background**: Errors during account switching or profile navigation such as `PROFILE_ROOT_NOT_CONFIRMED` or `SWITCHER_NOT_CONFIRMED` (e.g., `open_switcher failed: SWITCHER_NOT_CONFIRMED: switcher markers were not confirmed`) often contain keywords like "profile" or "switcher" or "login" in error hints/messages.
- **Problem**: If classified into `session_lost_failures`, they falsely trigger `[P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`, panicking operators into believing accounts were logged out when the app merely failed to open the switcher or profile tab cleanly (e.g. due to popups/onboarding).
- **Rule & Pattern**:
  In `SESSION_LOST_EXCLUSIONS`:
  ```python
  SESSION_LOST_EXCLUSIONS: tuple[str, ...] = (
      "profile verification",
      "navigation-failed",
      "navigation failed",
      "focus lost",
      "focused package unavailable",
      "failed to focus",
      "feed swipe",
      "swipe",
      "profile_root_not_confirmed",
      "profile root was not confirmed",
      "open_profile_root",
      "switcher_not_confirmed",
      "switcher markers were not confirmed",
      "open_switcher",
  )
  ```
  Ensure structured exclusion telemetry is emitted (`[SESSION_LOST_EXCLUSION] event=session_lost_excluded serial=...`) and verify with regression tests (`test_profile_root_not_confirmed_excluded_from_session_lost_with_telemetry` and `test_switcher_not_confirmed_excluded_from_session_lost_with_telemetry`).

## Exclusion of Safe Soft-Failure Signatures (e.g. FollowReleasedError) from Systemic Alerts (2026-10-02)
- **Background**: `FollowReleasedError` occurs when an account follows an anchor and TikTok's anti-spam algorithm silently releases the red follow button after pull-to-refresh. In `multi_machine_feed_session.py`, this is treated as a clean safe stop (`is_clean_follow_failed = True`), and the main feed session itself completed successfully.
- **Problem**: When `batch_aggregator` parses `follow_result.json`, `status == "FOLLOW_FAILED"` sets `succeeded = False` and `err_type = "FollowReleasedError"`. If 3+ machines (or >= 10% of batch) encounter this, it clusters into a systemic signature and triggers `[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG`, suggesting fleet shutdown when the farm, app, and scripts are completely healthy.
- **Solution & Invariants**:
  1. Define `SYSTEMIC_EXCLUSIONS: tuple[str, ...] = ("followreleasederror",)`.
  2. In `evaluate_batch`, check `is_systemic_excluded = any(ex in sig.lower() for ex in SYSTEMIC_EXCLUSIONS)` before promoting an error group to `systemic[sig]`:
     ```python
     for sig, machines in groups.items():
         count = len(machines)
         rate = count / total
         is_systemic_excluded = any(ex in sig.lower() for ex in SYSTEMIC_EXCLUSIONS)
         if rate >= min_rate and count >= min_count and not is_systemic_excluded:
             systemic[sig] = machines
         else:
             sporadic[sig] = machines
     ```
  3. This preserves individual failure counting in `report.failed_count` while preventing false-positive systemic alerts that would panic operators and freeze automation batches.




