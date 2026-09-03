# Live popup and capture recovery evidence (2026-08-09)

## Shop CTA false manual review

Observed during feed-session-smoke:

- The workflow correctly detected the paired TikTok Shop CTA markers `Mua ngay` and `Đóng`.
- The action selector was brittle: it hard-coded an old close resource-id (`...:hvm`). Live variants used different IDs (`...:hyw`, `...:hwn`), so the handler detected the overlay but could not find its close target and later classified it as `MANUAL_NEEDED_POPUP`.

### Required handler behavior

1. Identify the overlay only when both exact markers `Mua ngay` and `Đóng` are present in TikTok package context.
2. Resolve the **current XML's exact `Đóng` node dynamically**; never key the action to one obfuscated resource-id.
3. Never tap `Mua ngay`.
4. After a close action, recapture and require feed evidence before considering the popup resolved.
5. If the UI is the distinct fullscreen-shop-ad form with no safe close node, use only its existing bounded, evidence-gated swipe-through-overlay handler; no blind coordinate tap and no repeated swipe loop.
6. Add regression fixtures with changed obfuscated IDs, so the detection/action relationship—not one resource-id—is tested.

## CAPTURE_INVALID is transport failure, not necessarily a visible TikTok popup

A real `CAPTURE_INVALID` case had this sequence:

- persistent ATX/UIAutomator capture: HTTP 502;
- shell `uiautomator dump`: ADB timeout;
- subsequent capability probe also timed out;
- terminal signature: `ADB_TRANSPORT_LOST_AFTER_VERIFIED_PERSISTENT_CAPTURE`.

Treat this as an ADB/UIAutomator transport incident. Preserve screenshot/UI-dump evidence and do not infer the screen itself is the cause. A live retry must be gated by restored transport/readiness and a verified recapture; otherwise remain fail-closed.

## Runtime model-call timeout

Recovery executor slots must have a bounded timeout short enough to surface a real error to the operator. A 90-minute one-shot model timeout can make an active recovery appear silently stuck and consume the ladder without operational feedback. Record the timeout as a slot result and advance/fail-closed according to the configured ladder; never leave a live incident waiting indefinitely.

## Structured repair decision boundary

A repair executor can return a full `PatchDecision` whose machine-readable `decision` is `PATCH_READY`. This is **not** a planner-status result.

1. Parse and validate `PatchDecision` before passing an executor JSON object to `planner_result_from_value`; otherwise a generic `status: PATCH_READY` can be downgraded to `planner-status-invalid` and incorrectly produce `REPAIR_NOT_READY`.
2. Keep the nonzero-exit quota/provider-unavailable check ahead of any route that could authorize a live patch; malformed or incomplete decisions remain fail-closed.
3. On Windows, pass Vietnamese prompts to one-shot Hermes subprocesses with explicit UTF-8 text encoding; locale decoding can make the CLI reject stdin as invalid UTF-8.
4. Regression-test both repair backends with the same `PATCH_READY` fixture, and assert the Hermes subprocess uses its bounded timeout plus UTF-8 encoding.
