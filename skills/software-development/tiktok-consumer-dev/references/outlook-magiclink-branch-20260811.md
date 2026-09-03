# Outlook magic-link branch separation (2026-08-11, STT30)

TikTok registration can land on the **magic-link surface** ("Kiểm tra hộp thư
của bạn", "Gửi lại email", "liên kết") — this means the email has NO TikTok
account yet and TikTok sent a magic link, NOT a 6-digit OTP. For
Hotmail/Outlook/Live targets, `handle_tiktok_email_otp` used to fall into the
numeric readers (`_try_get_otp_outlook_cdp` CDP background-tab reader,
`_try_get_otp_browser`) which return 6-digit codes — entering a numeric code on
the magic-link surface fails with `OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK`.

## Live evidence (STT30 2026-08-11, serial ce0217126cd4bc640c, email redacted)

- TikTok XML contained `Kiểm tra hộp thư của bạn` and `liên kết`.
- Flow log sequence: `[7c] TikTok magic-link markers detected -> Gmail
  semantic-link mode` → `[otp-browser] ... Outlook` →
  `[otp-cdp] Fresh Outlook code found ...` → `[otp-enter] ... nhập OTP` →
  `[otp-enter] Cảnh báo: không còn ở màn OTP` →
  `RuntimeError OTP_ENTRY_SCREEN_MISMATCH_MAGIC_LINK`.
- Root cause: numeric readers ran on a magic-link surface; Gmail already had a
  proper semantic magic-link path but Hotmail/Outlook did not.

## Caller wiring (the minimal fix)

```python
# inside handle_tiktok_email_otp, replacing the unconditional CDP call:
if not code and not email.lower().endswith("@gmail.com"):
    if prefer_magic_link:
        code = _read_outlook_magic_link_with_evidence(device_id, email, password, stt=stt)
        if code != "MAGIC_LINK":
            _capture_tiktok_email_otp_final_blocked(
                device_id, stt, "OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED")
    else:
        code = _try_get_otp_outlook_cdp(device_id)

# the browser fallback MUST also skip magic-link:
if not code and not email.lower().endswith("@gmail.com") and not prefer_magic_link:
    code = _try_get_otp_browser(device_id, email, password)
```

`_capture_tiktok_email_otp_final_blocked` raises `[otp][FINAL_BLOCKED][...]` so
the magic-link failure is a distinct blocked signature and NEVER reaches
`_enter_tiktok_email_otp_with_one_fresh_retry` / `enter_otp_code`.

## New helpers in social_reg_v1.py (all consumer-only)

- `_OUTLOOK_MAGIC_LINK_ACTIONS` — semantic action labels: "Xác minh email",
  "Xác minh email của bạn", "Verify email", "Verify your email", "Xác nhận",
  "Confirm", "Verify", "Đăng ký", "Sign up", "Click here", "Tap here".
  **Deliberately NO bare "here"** (the weak generic fallback in
  `_try_get_otp_browser` used `find_text_tap(..., "here")` — banned).
- `_outlook_newest_tiktok_row(xml)` — picks the first clickable TikTok-bearing
  row in DOM order (Outlook web lists newest-first; probe máy 57 2026-08-11:
  1:07 AM before 1:05 AM), excludes url_bar/address_bar/omnibox resource-ids and
  y<240, records time_evidence + reason.
- `_outlook_magic_link_semantic_action(xml)` — `_semantic_clickable_node(xml,
  _OUTLOOK_MAGIC_LINK_ACTIONS, package="com.android.chrome")`.
- `_outlook_magic_link_visual_target(xml, *, row=None)` — **DEPRECATED stub
  (returns None)** since the STT30 tap-miss fix: the `https?://`-in-label visual
  fallback tapped the uiautomator bounds of a node whose REAL position was below
  the viewport. Kept only so external importers don't break.
- `_outlook_magic_link_ime_open(xml)` — IME/keyboard overlay detection: regex
  `mInputShown|mIsInputViewShown|inputShown|mShowRequested = ["']?true` (match
  BOTH quoted XML attrs and unquoted dumpsys) OR known keyboard packages
  (honeyboard / inputmethod.latin / swiftkey) OR class
  `inputmethodservice`/`KeyboardView`.
- `_outlook_magic_link_dismiss_ime(device_id, xml)` — BACK keyevent 4 tối đa
  MỘT lần + recapture; returns `(xml_after, ok)`; ok=False → caller fail closed
  (never tap while IME covers the tap zone). Takes the already-fetched xml so
  the no-IME common path adds ZERO extra `get_ui_xml` calls (mock page budget).
- `_outlook_magic_link_semantic_tap_ok(coord)` — semantic node usable only when
  center y ∈ [240, 1795] (viewport gate; STT30 semantic center 1896 → reject).
- `_outlook_magic_link_cdp_websocket_url(device_id)` — SEAM for tests: adb
  forward tcp:9224 → `localabstract:chrome_devtools_remote`, `/json` listing,
  pick tab whose url contains `outlook.live.com/mail`, return
  `webSocketDebuggerUrl` with port rewritten. `AdbClient.run` host commands are
  NOT intercepted by mocking module `shell` — tests monkeypatch this seam.
- `_cdp_probe_outlook_magic_link_anchor(websocket_url)` — `_cdp_evaluate` with
  `_OUTLOOK_MAGIC_LINK_CDP_PROBE_JS`: `querySelectorAll('a')`, prefer href
  `/email_verification/i` else `/tiktok\.com/i`, return
  `{href, text, rect:[x,y,w,h] (CSS px), innerWidth, innerHeight,
  devicePixelRatio}` or None. READ-ONLY — no JS click ever.
- `_cdp_scroll_outlook_anchor_into_view(websocket_url)` — `window.scrollBy(0,
  r.bottom - innerHeight*0.7)` via `_cdp_evaluate` (scroll allowed, click not).
- `_outlook_magic_link_cdp_anchor_to_device(probe)` — CSS→device map:
  `device_x = css_x * dpr`, `device_y = 240 + css_y * dpr` (content top 240,
  STT30 dpr3: CSS [33,545,293,44] → device [99,1875][978,2007]).
- `_outlook_magic_link_cdp_rect_plausible(rect_device)` — x1≥0, x2≤1080,
  y1≥240, y2≤1795, x2>x1, y2>y1.
- `_outlook_magic_link_cdp_tap_target(device_id, *, stt=None)` — composer:
  ws discovery → probe → map; `email_verification` NOT in href → None; y2 >
  1795 → `window.scrollBy` + re-probe (max `_OUTLOOK_MAGIC_LINK_CDP_SCROLL_ATTEMPTS`
  = 2); still outside → None; plausible gate; returns
  `{coord, bounds, label, href}` (coord = rect center) or None.
- `_open_outlook_inbox_verified(...)` — opens Chrome to
  `https://outlook.live.com/mail/0/inbox?nlp=1`, dismisses cookie/M365/
  protect/save-password popups with the same safe labels as the numeric path,
  canonical Hotmail login when a sign-in form appears, verifies via
  `_outlook_inbox_visible` (never trusts the URL bar).
- `_read_outlook_magic_link_with_evidence(...)` — the orchestrator. Returns
  `"MAGIC_LINK"` ONLY when: inbox verified → newest TikTok row → mail opened +
  Chrome + "tiktok" content → **IME dismiss** → semantic action (viewport-gated)
  OR CDP anchor rect tapped → `_verify_visual_magic_link_transition` recapture
  shows TikTok foreground or Open-with dialog (handled via
  `_handle_open_with_tiktok_dialog`). Any unverified step returns None and saves
  XML/screenshot evidence. Never calls the numeric readers.

## STT30 tap-miss fix 2026-08-11: IME dismiss + CDP anchor rect

Live probe (serial `ce0217126cd4bc640c`, tab 159): semantic node 'Xác minh
email' uiautomator bounds `[99,1872][978,1920]` — center y 1896 is BELOW the
viewport (bottom ≈ 1795 device) and the IME was open (`mInputShown=true`,
quickCompose reply editor) covering `[0,1795][1080,1920]` → the old tap missed.
CDP gave the REAL anchor geometry: href
`tiktok.com/ucenter_web/deeplink/email_verification?code=...`, rect CSS
`[33,545,293,44]`, viewport 360x518 CSS @ dpr3 (1080x1554 device), mask
`x_mask_email_link` CSS `[47,466,266,58]` → device `[141,1638][939,1812]`.

Mapping formula (verified against the XML mask): `device_x = css_x * dpr`,
`device_y = 240 + css_y * dpr` (WebView content top 240). Anchor CSS
`[33,545,293,44]` → device `[99,1875][978,2007]` (y2 2007 > 1795 → scroll
needed); after `window.scrollBy` re-probe CSS `[33,317,293,44]` → device
`[99,1191][978,1323]` (y2 ≤ 1795 → tap center `(538,1257)`).

Tap priority: semantic in-viewport → CDP email_verification rect → fail closed.
No CDP JS click (read-only rect + scroll only); no tap when IME open; no tap
when rect implausible/outside. Constants:
`_OUTLOOK_MAGIC_LINK_CONTENT_TOP_DEVICE = 240`,
`_OUTLOOK_MAGIC_LINK_VIEWPORT_BOTTOM_DEVICE = 1795`,
`_OUTLOOK_MAGIC_LINK_SCREEN_WIDTH_DEVICE = 1080`,
`_OUTLOOK_MAGIC_LINK_CDP_SCROLL_ATTEMPTS = 2`,
`_OUTLOOK_MAGIC_LINK_CDP_LOCAL_PORT = "9224"`.

## Regression tests (tests/test_login_outlook_magiclink_branch.py, 13 gốc + 5 case mới)

- (a) `test_hotmail_magic_link_skips_numeric_cdp_and_browser_readers` and
  `..._even_when_cdp_would_find_code` — magic-link Hotmail returns MAGIC_LINK
  and `_try_get_otp_outlook_cdp` / `_try_get_otp_browser` are NEVER called.
- (b) `test_outlook_magic_link_helper_returns_magic_link_only_on_verified_transition`
  (2 taps: row + action; verified recapture → MAGIC_LINK) and
  `..._fails_closed_on_unverified_transition` (Chrome-only recapture → None).
- (c) `test_hotmail_magic_link_unverified_raises_distinct_and_never_enters_code`
  (RuntimeError match OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED; enter_otp_code,
  resend handler, find_text_tap all zero calls) and
  `test_outlook_magic_link_numeric_only_message_fails_closed` (numeric-only
  mail → None, single row tap, no generic text tap) and
  `test_outlook_magic_link_actions_never_include_bare_here`.
- (d) `test_hotmail_registered_otp_still_calls_numeric_path_and_enters_code`
  (registered OTP → CDP + enter_otp_code; magic reader never called) and
  `test_outlook_newest_tiktok_row_picks_newest_and_excludes_url_bar`.
- (e) STT30-fix regressions (mocks: `_cdp_evaluate` sequence-driven,
  `_outlook_magic_link_cdp_websocket_url` → fake ws, `get_ui_xml`/`tap`/
  `keyevent`/`shell`/`swipe` no-op recorders):
  `test_outlook_magic_link_dismisses_ime_before_tap` (honeyboard overlay in
  message XML → keyevent 4 before the LINK tap — row tap legitimately first;
  semantic node tapped only after recapture clean),
  `test_outlook_magic_link_cdp_anchor_outside_viewport_scrolls_then_taps`
  (probe below → scroll → re-probe → tap (538,1257), 3 cdp calls),
  `test_outlook_magic_link_cdp_anchor_in_viewport_taps_verified_rect`
  (1 cdp call, tap (538,606), MAGIC_LINK),
  `test_outlook_magic_link_cdp_unavailable_fails_closed_without_link_tap`
  (parametrized: probe None → None; still-outside after 2 scrolls → None; only
  the row tap, no keyevent). Fixtures: `CDP_ONLY_MESSAGE_XML` has the semantic
  node at bounds `[99,1872][978,1920]` — pre-fix code taps it (wrong), post-fix
  viewport gate rejects → CDP path; `IME_MESSAGE_XML` adds a honeyboard node.

## Test-mocking pitfall: recapture loops vs. iterator mocks

Code under test that recaptures XML multiple times (this branch calls
`get_ui_xml` after row tap AND inside `_verify_visual_magic_link_transition`)
will exhaust a `iter([...])` + `next(pages)` mock with `StopIteration`. The
existing `tests/test_login_otp_health_fallback.py::test_outlook_browser_login_is_not_skipped_by_inbox_url_bar`
fails this way PRE-EXISTING (its 2-page iterator is consumed by the real CDP
probe + find_text_tap). Pattern that survives: a mock returning the LAST page
repeatedly:

```python
def _xml_pages(*pages):
    state = {"i": 0}
    def _get(*_a, **_k):
        idx = min(state["i"], len(pages) - 1)
        state["i"] += 1
        return pages[idx]
    return _get
monkeypatch.setattr(social, "get_ui_xml", _xml_pages(MSG_XML, TIKTOK_FG_XML))
```

**Second pitfall (STT30 fix): mock page-sequence budgeting.** Inserting a NEW
step that calls `get_ui_xml` shifts every subsequent page assignment silently
(the clamp hands out the LAST page from then on) — a new unconditional recapture
between "mail opened" and "transition verify" would make the transition-verify
mock return the wrong page and flip existing tests. `_outlook_magic_link_dismiss_ime`
avoids this by taking the already-fetched xml as a parameter and recapturing
ONLY when IME was detected — zero extra calls on the common path, existing
tests' page counts stay valid. Also: `AdbClient(...).run(["forward", ...])`
host-side adb is NOT intercepted by mocking module `shell`; the CDP path needs
the `_outlook_magic_link_cdp_websocket_url` seam mocked (→ None or fake ws URL)
or tests reach real adb.

Distinguish pre-existing failures by running the affected files BEFORE your
edit (baseline) — this session: 28 passed / 1 failed before, same single
pre-existing failure after (60 passed / 1 failed with the new suite added).
Do not "fix" the fragile old test unless the new contract requires it.

## Docs entry

`docs/ui-compatibility.md` entry `tiktok-reg-outlook-magiclink-branch-20260811`
documents: UI signature + redacted STT30 evidence, ordered selector/fallback
(IME dismiss → semantic viewport-gated → CDP anchor rect + `window.scrollBy`
re-probe → visual URL-label fallback bỏ, no bare "here", no numeric entry),
safety bounds, post-action verification, regression test list (incl. 4 test
STT30-fix mới), old branches preserved, consumer-only (`social_reg_v1.py`, no
automation-core change). The docs file was already dirty at HEAD — preserve the
pre-existing sections, append only your own entry. NOTE 2026-08-11 STT30 fix:
the whole magic-link branch + test file were UNCOMMITTED working-tree state
(HEAD predates the branch) — `git diff` vs HEAD shows the previous worker's
work as your delta; verify increments against the working tree and do not
commit.

## Second wave (same day): transition state-wait + `[9]` success guard

Live STT30 (serial `ce0217126cd4bc640c`) 19:48 + 20:05 — SAME DAY as the
first-wave fix, NEW failure mode: tap link OK → TikTok foreground NHƯNG vẫn
màn "Kiểm tra hộp thư của bạn" (SignUpOrLoginActivity). `_post_auth_ui_state`
classifies that screen **"unknown"** (NOT success/registration_entry/
password_required), yet the helper returned MAGIC_LINK immediately after the
visual transition check (which only proves TikTok is foreground). Downstream
`wait_login_success` `[9]` then logged `✓ Thanh cong ... hint='Kiểm tra hộp
thư của bạn'` (false success) → `[10]` kẹt profile → STOPPED `[02_profile]`.

### Fix (a): state-change wait inside `_read_outlook_magic_link_with_evidence`

After `_verify_visual_magic_link_transition` verified (and open-with handled),
REPLACE the immediate `return "MAGIC_LINK"` with:

```python
try:
    activity_dump = shell(device_id, "dumpsys", "activity", "activities")
except Exception:
    activity_dump = ""
resume_component = None
component_match = re.search(
    rf"(?:mResumedActivity|topResumedActivity).*?"
    rf"({re.escape(APP_PACKAGE)}/[A-Za-z0-9_.$]+)", activity_dump or "")
if not component_match:
    component_match = re.search(
        rf"({re.escape(APP_PACKAGE)}/[A-Za-z0-9_.$]+)", activity_dump or "")
if component_match:
    resume_component = component_match.group(1)
try:
    _return_to_tiktok_after_magic_link(device_id,
        resume_component=resume_component, timeout=90)
except Exception as exc:
    log(f"   [otp-magiclink] State không đổi thật sau tap link "
        f"({type(exc).__name__}: {exc}) -> fail closed")
    return None
log("   [otp-magiclink] MAGIC_LINK verified transition -> return MAGIC_LINK")
return "MAGIC_LINK"
```

- `resume_component` = the same `dumpsys mResumedActivity` regex the caller 7c
  (`handle_tiktok_email_otp`) uses for `otp_component`; None fallback is fine
  (helper falls back to Recents). Wrap the dumpsys shell call in try/except so
  tests that don't mock `shell` stay safe.
- `_return_to_tiktok_after_magic_link` (helper Gmail path) waits for
  `_post_auth_ui_state` ∈ {success, registration_entry, password_required} OR
  `_is_tiktok_signup_transition_xml`, with open-with + Recents handling; it
  RAISES `[7c][MAGIC_LINK_TIKTOK_RETURN_UNVERIFIED]` (never TikTok) or
  `[7c][MAGIC_LINK_TIKTOK_TRANSITION_TIMEOUT]` (state never changed). Only a
  no-raise return counts as verified.

### Fix (b): `wait_login_success` `[9]` guard

- **Remove** `"Hộp thư", "Hop thu"` from `success_hints` (they substring-match
  the node text "Kiểm tra hộp thư của bạn" → false success).
- **Add** a guard immediately BEFORE the success-hint node check
  (`find_node_in_xml(xml, *success_hints, ...)`), AFTER the `tiktok_fg` gate:

```python
if any(marker in flat for marker in (
    "kiem tra hop thu", "gui lai email", "gui lai ma",
    "resend email", "resend code",
)):
    log("   [login-success] magic-link/email-verify screen -> chưa success, tiếp tục chờ")
    time.sleep(1.5)
    continue
```

- Placement matters: AFTER the L4919 `xac minh email`/`gui lai ma` OTP-entry
  branch (that branch legitimately fetches+enters a code and continues — the
  guard must not pre-empt it) and BEFORE the hints check. "gui lai ma" is
  already caught upstream; the guard is belt-and-braces per the contract.
- Keep the remaining hints (Hồ sơ/Trang chủ/Bạn bè/Dành cho bạn/Đề xuất/
  Following) — they are real success signals.

### Fixture facts (probe classifiers BEFORE writing tests)

Verified with `python -c` probes against candidate fixture XMLs — cheap and
catches wrong assumptions before any test is written:

- magic screen → `_post_auth_ui_state` = **"unknown"** (fail-closed
  precondition: never in the verified set).
- `registration_entry` = flat contains "dang nhap vao tiktok" + APP_PACKAGE.
- `password_required` = exact label "Tạo mật khẩu"/"Nhập mật khẩu" (via
  `_tiktok_exact_ui_label_present`) AND an EditText with **`password="true"`**
  — an EditText without the password attr does NOT classify (got "unknown").
- `success` (profile) = `_is_profile_screen_xml` needs ≥2 profile markers
  (e.g. "sua ho so" + "follower"); a lone "Hồ sơ" node → "unknown".
- `find_node_in_xml` **skips any node without a `bounds` attribute** — fixture
  XML must include bounds or the node never matches (also true for
  success-hint matching: the real STT30 node had bounds).

### Test delta + regression list

Baseline 36 → 43 (7 new): `test_magic_link_foreground_magic_screen_waits_real_state_transition`
(magic screen + helper raise → None; helper called once with timeout=90),
`test_magic_link_returns_only_after_real_state_transition` (parametrized
registration_entry/password_required/profile_success → MAGIC_LINK),
`test_wait_login_success_never_true_on_magic_link_screen` (find_node_in_xml
mock RAISES to prove the guard runs first; magic screen + "Hộp thư" text →
False), `test_wait_login_success_still_true_on_real_hint_with_app_package`
(parametrized "Đề xuất"/"Hồ sơ" + bounds → True).

Existing tests that reach the new code path MUST mock
`_return_to_tiktok_after_magic_link` (harmless pre-patch, required post-patch):
`test_outlook_magic_link_helper_returns_magic_link_only_on_verified_transition`,
`test_outlook_magic_link_dismisses_ime_before_tap`, and the two CDP anchor
tests via `_mock_link_io`. Verified `test_login_identifier.py` hang is
pre-existing (scoped-stash proof: it only imports `tiktok_login_v1`, never
`social_reg_v1`).
