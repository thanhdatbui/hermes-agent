# P1-01..P1-07 test + docs update — mapping đầy đủ (verify 2026-08-09, full suite 326 pass)

Task: hoàn thiện test + docs cho code ladder OPEN_TIKTOK / typing fallback CAPTION_FILL đã sửa
(commit `2e0b530` + `f4e4520`, P1-01..07 + P2-01). Không commit/push. EOL: test LF thuần,
docs CRLF thuần.

## Invocation chuẩn (git-bash, Windows)

```bash
cd /d/Taadaa/Tiktok-video
PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" \
  -m pytest tests/test_tiktok_workflow.py -q -k "<selector>"
# full suite: bỏ -k → 326 passed (75.9s)
```

## 4 test cũ — failure thật trước khi sửa (chạy trước, đừng tin brief)

Brief nói "4 fail" nhưng thực tế **1 đã pass sẵn** (`test_caption_fill_typing_fallback_when_clipboard_times_out` —
dump không expose EditText → `_caption_chunk_landed` fall back visible text, final verify `_caption_is_visible`
pass). 3 test còn lại fail với assert thật:

| Test | Failure thật | Fix |
|---|---|---|
| `test_handle_open_tiktok_accepts_visual_feed_after_recovery_ladder_exhausted` | `assert _handle_open_tiktok() is True` → False; log `Soft-reboot outcome=NOT_ELIGIBLE` | `machine.context.soft_reboot_recovery_outcome = "VERIFIED"` (sau khi gán StateContext) + `machine._package_is_foreground = lambda *a, **k: True` |
| `test_handle_open_tiktok_coordinate_tap_scaled_by_wm_size_after_ladder_exhausted` | `transport.taps == []` (không có tap) | set outcome VERIFIED **sau** `machine.context = StateContext(...)` (lần đầu đặt trước → bị context mới wipe — mắc thật) + mock `_package_is_foreground=True` + icon tối fixture phóng to 300×20 (P1-04 dark≥0.05) |
| `test_wait_for_feed_atk_kill_consumed_per_signature_across_relaunch` | `atx_kill_signatures.get('WAIT_FEED:UIAUTOMATOR_DUMP_FAIL') is None`; dict thật = `{'WAIT_FEED:DUMP_UNKNOWN': True}` | dump raise 1 tham số `AccountSwitcherError("uiautomator null root node")` → TypeError lúc construct → classifier thấy TypeError → DUMP_UNKNOWN. Sửa: `AccountSwitcherError("UI_DUMP_FAILED", "uiautomator null root node")` + `signature = StateMachine._classify_wait_feed_dump_failure(...)` (== `"WAIT_FEED:NULL_ROOT"`) — bỏ constant cũ |

## 6 regression test mới (đều nằm đúng class chủ)

- `test_open_tiktok_coordinate_fallback_gated_by_soft_reboot_outcome` (TestStateMachine) — P1-01 gate:
  NOT_ELIGIBLE → `_coordinate_fallback_after_ladder_exhausted` KHÔNG gọi, `is_ui_unavailable=True`; VERIFIED → gọi được,
  trả True. ⚠️ Giữa 2 lần gọi `_handle_open_tiktok` phải reset `is_ui_unavailable=False` + `error=None` — guard
  `if self.context.is_ui_unavailable and self.context.error: return False` (state_machine.py ~1851) chặn lần gọi 2.
- `test_wait_for_feed_atx_kill_budget_per_signature_two_error_codes` (TestAdapter) — P1-02/P2-01: dump queue
  `[NULL_ROOT, NULL_ROOT, IDLE_STATE, IDLE_STATE]` trong 1 poll → recover == 2, `atx_kill_signatures` có cả 2 key,
  mỗi key đúng 1 entry `atx_kill_evidence`; `_wait_for_feed` lại với cùng signature → recover vẫn 2.
- `test_screenshot_bottom_nav_strip_requires_foreground_and_white_dark` (TestStateMachine) — P1-04: ảnh 720×1280,
  crop 0.93h..0.995h (1190..1273): white+dark (dark 300×40 tại y 1230..1270 → ~0.16) + foreground=True → True;
  foreground=False → False; toàn trắng → False; portrait mock False → False.
- `test_coordinate_fallback_tap_fail_closed_when_transport_tap_returns_false` (TestStateMachine) — P1-05:
  `transport.tap` trả False → `_coordinate_fallback_after_ladder_exhausted` False, `taps == [(72, 1240)]` đúng 1 lần,
  checkpoint: `tap_ack is False`, `"fail-closed" in reason`, `recaptured is False`, `coordinates == [72, 1240]`.
- `test_caption_typing_ratio_ok_structured_verifier` (TestCaptionFill) — P1-06: `#aaaaa` vs `abc` → False;
  `#travel #fun summer vacation` vs `...vaction` → True (hashtag 2/2 + ratio ~0.93); thiếu `#travel` → False
  (hashtag gate 1/2 < 0.70 chặn dù ký tự khớp); `"đi chơi"` vs `"đi chơ"` (7→6 ký tự, dist 1/7=0.143 ≤ 0.25) → True;
  `"ăn cơm"` vs `"đi chơi"` → False.
- `test_sanitize_adb_input_text_whitelists_and_chunk_landed_fallback` (TestCaptionFill) — P1-07:
  `_sanitize_adb_input_text("abc!@#việt nam💥")` → cleaned chứa `"việt nam"`, mọi ký tự xấu biến mất,
  `set(dropped) == {"!", "@", "#", "💥"}`; ASCII+Việt hợp lệ → dropped `[]` nguyên vẹn; `_caption_chunk_landed`:
  EditText text `"hello chunk"` → True, `"other text"` → False, dump không EditText → visible-text fallback True;
  `_caption_field_text_from_xml` ưu tiên focused hơn diện tích.

## Doc updates (docs/tiktok-ui-compatibility.md, CRLF giữ nguyên)

- **COMPAT-OPEN-TIKTOK-002**: Signature UI → error-code (`WAIT_FEED:NULL_ROOT`/`IDLE_STATE`/`NON_XML`/`DUMP_UNKNOWN`);
  bước 1 → `_recover_wait_feed_uiautomator` + `atx_kill_evidence` (P1-03); bước 3 → outcome lưu `context.soft_reboot_recovery_outcome`;
  bước 4 → gate P1-01 (chỉ VERIFIED/ATTEMPTED_FAILED) + strip detector P1-04 (white≥0.10 AND dark≥0.05 + foreground + portrait)
  + tap fail-closed P1-05; Regression tests list mới (8 tests); "Không được làm" bổ sung.
- **COMPAT-CAPTION-004**: sanitize whitelist P1-07, chunk verify `_caption_chunk_landed` (EditText → visible fallback),
  `caption_typing_residue` chặn append fallback khi clear fail, verifier P1-06 (hashtag ≥70% + ratio ≥60% + short edit ≤25%);
  Regression tests +2.

## Script edit an toàn EOL (pattern đã dùng, 2 lần chạy ổn)

```python
with open(TEST_PATH, "rb") as fh: raw = fh.read()
assert b"\r" not in raw, "test file must be pure LF before edit"
text = raw.decode("utf-8")
def apply(text, old, new, count=1):
    n = text.count(old)
    assert n == count, "anchor count %d != %d for: %r" % (n, count, old[:90])
    return text.replace(old, new)
# ... text = apply(text, old, new) ...
open(TEST_PATH, "wb").write(text.encode("utf-8"))
assert b"\r" not in open(TEST_PATH, "rb").read(), "must stay pure LF"
# docs (CRLF): normalize → edit → re-encode CRLF → assert CRLF==LF
```

- Viết script qua `write_file` (temp ngoài repo), chạy bằng đường dẫn Windows thật:
  `"/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" "C:\Users\Kibe\_tmp_edit_p1.py"`
  (MSYS path `/c/Users/...` bị bash convert sai — xem §13 cũ).
- Sau edit: chạy `-k` nhóm test liên quan (10 passed), rồi full suite (326 passed), verify EOL cả 2 file,
  `git diff --stat` cho từng finding, KHÔNG commit.
