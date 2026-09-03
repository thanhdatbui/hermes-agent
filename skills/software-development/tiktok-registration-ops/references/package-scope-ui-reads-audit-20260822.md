# Package-scoping UI reads in TikTok registration (social_reg_v1.py)

Reusable technique + audit checklist for keeping `com.android.systemui`
notifications from causing false positives / wrong taps in the reg flow.

## The core fix (Android UI dump scoping)

UI dumps from `get_ui_xml` include ALL packages on screen — notification
shade (`com.android.systemui`), GMS re-login, etc. A whole-XML
`strip_accents(xml).lower()` scan or `root.iter("node")` walk therefore
matches notification text ("Đăng nhập", "Số điện thoại", "Tiếp tục",
"Continue", "Bỏ qua", "Skip", "Xác nhận") and taps the wrong node.

The patch in `D:/Taadaa/Tiktok_Reg/social_reg_v1.py` introduced these helpers:

- `_package_flat_text(xml, package)` — flatten ONLY text/content-desc/
  resource-id of nodes whose `package` attr == package (inherited from
  parent if a node omits it).
- `_iter_package_nodes(root, package)` — generator yielding only those nodes.
- `_tiktok_flat_xml(xml)` = `_package_flat_text(xml, APP_PACKAGE)`.
- `_tiktok_login_modal_present(xml)` — login-signup detection on TikTok
  scope only.

Usage patterns:
- Replace `flat = strip_accents(xml).lower()` with `flat = _tiktok_flat_xml(xml)`,
  BUT only when the surrounding markers are TikTok-owned. If a helper also
  needs to match non-TikTok packages (e.g. GMS re-login), keep the
  `APP_PACKAGE not in xml` guard and pass the right package.
- Replace `for node in root.iter("node")` with
  `for node in _iter_package_nodes(root, APP_PACKAGE)`.
- Pass `package=APP_PACKAGE` to `find_text_tap(...)` / `wait_for_text(...)`
  / `find_node_in_xml(...)` so they only match TikTok-owned nodes.

Pitfall: `_package_flat_text` drops text for nodes that have NEITHER a
`package` attr NOR an ancestor with one. Real dumps always set it, but if a
future layout omits package on a TikTok node, that text becomes invisible to
the scope filter (miss, not false positive). Verify against a real dump.

## Remaining unscoped reads after the patch (audit 2026-08-22, read-only)

Severity = likelihood a systemui notification hits the marker.

HIGH (can tap the wrong node directly):
- `flat_7c` loop — social_reg_v1.py ~7432 & ~7436 still use
  `strip_accents(xml_7c).lower()` while ~7400 uses `_tiktok_flat_xml`. Fix:
  both loop refreshes → `_tiktok_flat_xml(xml_7c)`.
- `find_text_tap` generic words in `handle_post_auth_screens` / step 9:
  ~7151 ("Bỏ qua"/"Skip"), ~7153 ("Tiếp tục"/"Continue"/"Next"),
  ~7158 & ~7174 ("Xác nhận"/"Confirm"), ~7214 & ~7216 ("Tiếp tục"/"Continue").
  Add `package=APP_PACKAGE`.
- `find_node_in_xml` ~7357 ("Chuyển sang dùng email", step 7a) — add
  `package=APP_PACKAGE`.
- `_profile_tab_node` ~2013 `root.iter("node")` (used to TAP Profile and in
  `_is_profile_screen_xml` / `_post_auth_ui_state`). Convert to
  `_iter_package_nodes(root, APP_PACKAGE)`.

MEDIUM:
- `_post_auth_ui_state` ~3987 `flat = strip_accents(xml)...` (called step 7b).
  Scope its `flat` comparisons via `_tiktok_flat_xml`; also fix
  `_registration_login_node` (~4063) and `_profile_tab_node` it calls.
- `find_node_in_xml` ~4269 `success_hints` (step 9) → `package=APP_PACKAGE`.
- `find_node_in_xml` ~6830 "Gửi lại mã" (step 7c) → `package=APP_PACKAGE`.
- `dismiss_add_phone_prompt` ~2678 + ~2682 (flat + tap "Đóng"/"Close") →
  `_tiktok_flat_xml` + `package=`.
- `fill_email_and_next` OTP/registered fallback ~3097 (`flat2`) & ~3118
  (`flat_backup`) → `_tiktok_flat_xml`.

LOW:
- `flat_7d` ~7456 (step 7d birthday) → `_tiktok_flat_xml`.
- `_dob_text_from_xml` ~3569 `root.iter("node")` + `fill_birthday` SeekBar
  regex ~3703 — low risk (EditText/SeekBar rarely in systemui) but tag
  `APP_PACKAGE`.
- `wait_for_text` ~3887 (step 8 "Mật khẩu"/"Password") → `package=APP_PACKAGE`.
- `is_tiktok_captcha_xml` ~3981 already guarded by `APP_PACKAGE in xml`
  (safe). `maybe_save_login_info_prompt` ~1146 low risk.

## Non-regression notes from the same audit

- Dead variable: `flat_b2 = _tiktok_flat_xml(xml_b2)` at ~7313 is assigned
  but never read (only `has_login_modal = _tiktok_login_modal_present(xml_b2)`
  is used). Remove it.
- Test weakness: `test_choose_email_login_...` mocks `wait_for_text` to
  return `package != APP_PACKAGE` so it raises at `[06]` — it proves
  "no tap when no login methods", NOT that the `package=` scoping is correct
  on the actual `find_text_tap` calls. Add fixtures (systemui + TikTok) for
  `_profile_tab_node`, `flat_7c`, `_post_auth_ui_state`. The real scope proof
  is `test_tiktok_text_scope_excludes_system_login_and_phone_notifications`.
- `py_compile` passed; new generator helpers (`yield from`) valid.
