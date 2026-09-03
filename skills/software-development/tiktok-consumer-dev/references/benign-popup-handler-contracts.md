# flows/benign_popup.py handler contracts (nurture repo `D:\Taadaa\tiktok-luot nuoi acc`)

Reusable, non-obvious facts for editing `dismiss_*_popup` handlers in
`python_runner/flows/benign_popup.py`. Learned fixing the rejected
`dismiss_follow_friends_suggestion_popup` closeout patch (2026-08-22).

## `capture_required_ui` returns a STRING, not a dict

`capture_required_ui(ctx, reason=...)` returns the **XML text** (a `str`), NOT a
dict. The buggy handler did `after = capture_required_ui(...); after.get("xml_path")`
→ `AttributeError` at runtime → the post-close verification block was dead code.

- Correct recapture: `xml = capture_required_ui(ctx, reason="...")` then
  `root = parse_xml(xml)`.
- It only returns a verified, hierarchy-rooted XML; on failure it raises (the
  live `capture_required_ui_result` is fail-closed). Treat a return that lacks
  `"<hierarchy"` as NOT verified.
- `capture_required_ui` is a **runtime-injected seam** in `flows/benign_popup.py`
  — it is NOT imported into the module. Sibling handlers call it with no local
  import, and tests patch `flows.benign_popup.capture_required_ui`. So a module
  attribute lookup `hasattr(m, "capture_required_ui")` is `False` at import time;
  rely on the name being present at call time (same contract as the rest of the
  file's `dismiss_*` siblings).

## `parse_bounds` wants real TikTok format `[x1,y1][x2,y2]`

`parse_bounds("[0,0][100,50]")` → `(0, 0, 100, 50)`.
`parse_bounds("[0,0,100,50]")` (the naive `[x,y,w,h]`) → **`None`**, and a
handler that does `if not bounds: break` will silently skip the tap. Always feed
fixtures the two-bracket form. The center is `(b[0]+b[2])//2, (b[1]+b[3])//2`.

## `ctx.last_xml_tree` is referenced but never assigned

Sibling handlers read `getattr(ctx, "last_xml_tree", None)` but nothing in the
tree ever sets it — so it is effectively always `None`. Do NOT rely on it for the
current hierarchy; use the `capture_required_ui` return + `parse_xml` instead.

## Fail-closed dismiss handler pattern (reusable skeleton)

For any `dismiss_*_popup(ctx, xml_root=None, *, step_name=...)`:

1. **Capability guard first**: if `ctx` has no `tap`, `shell`, or `adb.shell`,
   return `dismissed=False` immediately. Never report success with no action
   capability. Resolve a single `tap_action` callable so every tap path uses it
   (avoids a half-written `elif` that crashes).
2. **Tap at most N exact targets** (≤2 for Follow-lại/back), **recapture fresh
   XML after each tap**. If recapture raises / returns non-XML → **break and
   abort**: never fall through to a stale `current_root` for the close step.
3. **Close only a SEMANTIC control.** `resource-id` ending `:id/e63` ALONE is
   insufficient (on some layouts `e63` is a different control) — accept it only
   when it is also an `ImageView`/`ImageButton` with `clickable=true` and no
   conflicting text/desc; OR an explicit label `Đóng`/`Close`/`X`.
4. **After the close tap, require a fresh parsed hierarchy** and confirm the
   detector (`detect_*_popup(after_root)`) is `False` before reporting
   `dismissed=True`; otherwise fail-closed.
- **No tab-switch / Back** unless the specific handler is explicitly a
   back-based one. Never use a stale XML for a decision.

## Invariant: `has_sensitive_marker` must NOT be called inside specific benign popup detectors

In `automation-core/src/automation_core/tiktok/benign_popup.py`, specific detectors (`detect_*`) rely on their own structural, exact-label, or marker evidence.
- **Rule**: Never call `has_sensitive_marker(root)` inside a specific rule detector (e.g. `detect_contacts_settings_permission_dialog`).
- **Why**: `has_sensitive_marker` is intended only as a fallback gate when *no explicit benign popup matched*. If placed inside a specific detector, ordinary video feed captions, hashtag text, or clickable elements in the background (e.g. "tiếp tục", "đăng nhập", "mật khẩu") return `True` for `has_sensitive_marker`, causing the detector to return `None` and deadlocking legitimate in-app dialog dismissal over the feed.
- **Docstring contract**: *"Sensitive markers do not veto a rule-specific detector. A popup is actionable only when its detector supplies complete evidence and a selector; unmatched UI remains unverified."*

## `benign_popup_registry.py` handler & testing conventions

- **Priority 91 (`contacts_settings_permission_prompt`)**: In-app permission prompt for contacts settings. Detects both Vietnamese and English variants (`Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị`, `truy cập vào danh bạ của bạn trong mục cài đặt thiết bị`, `cho phép truy cập vào danh bạ của bạn trong mục cài đặt`, `To connect with people you know on TikTok, allow access to your contacts in device settings`, `allow access to your contacts in device settings`). Dismisser prioritizes deny element ("Không cho phép", "Don't allow", "Deny", "Từ chối", "Hủy", "Cancel") center tap, with fallback to `send_device_back_key`.
- **Do not re-import `send_device_back_key` locally**: Handlers in `benign_popup_registry.py` should use the module-level `from .benign_popup import send_device_back_key` instead of re-importing inside the function body (`from .benign_popup import PopupDismissResult, send_device_back_key`). Re-importing inside the function bypasses `unittest.mock.patch("flows.benign_popup_registry.send_device_back_key", ...)` in test suites.

## Narrow verification path

- Compile: `python -m py_compile flows/benign_popup.py`
- Scoped suite: `pytest tests/test_benign_popup.py -q` (114 passed, 10 skipped
  as of 2026-08-22). `test_classifier.py` is unrelated — don't touch it to prove
  a benign_popup fix.
- Confirm scope: `git diff --stat` must list **only** `flows/benign_popup.py`;
  pre-existing unrelated dirt (e.g. `multi_machine_feed_session.py`) must remain
  untouched.

## Ad-hoc verify harness (reusable)

Drop a `hermes-verify-*.py` in `C:\Users\Kibe\AppData\Local\Temp`, monkeypatch
`flows.benign_popup.capture_required_ui` to return fake XML (correct
`[x1,y1][x2,y2]` bounds), and record `ctx.tap`/`ctx.shell` calls into a list.
Make the mock return `CLEAN_FEED` once a **close-center** tap is seen (simulating
real dismissal) so the post-close check passes; assert counts of
follow-taps (≤cap) vs close-taps (==1 when dismissed, ==0 when fail-closed).
Run with the repo's real interpreter (NOT the hermes venv — see PYTHONPATH-poison
section), then delete the temp file. See `references/ad-hoc-verify-script-pattern.md`.
