# RE-AUDIT v2 fixes — Sol audit P1-01..08 + P2-01 (Tiktok-video, 2026-08-09)

Nguồn: `Sol RE-AUDIT` (vòng 2) trên `D:\Taadaa\Tiktok-video`. 9 findings về
`scripts/tiktok_workflow/state_machine.py` (CRLF THUẦN), `tests/test_tiktok_workflow.py`
(LF THUẦN), `docs/tiktok-ui-compatibility.md` (CRLF THUẦN).

## TRẠNG THÁI (resume point — cập nhật 2026-08-09, phiên test round)

- ✅ `state_machine.py`: 21 replacements ĐÃ áp (script `C:\Users\Kibe\fix_v2_edits.py`),
  `py_compile` OK, EOL pure CRLF giữ nguyên.
- ✅ ĐÃ verify bằng pytest thật (KHÔNG tin brief): đúng **4 fail**:
  `test_adb_input_text_escapes_hash_spaces_and_backslashes`,
  `test_clear_caption_input_uses_single_long_delete`,
  `test_clear_caption_input_taps_field_when_visible`,
  `test_sanitize_adb_input_text_whitelists_and_chunk_landed_fallback`
  (322 pass còn lại; lệnh chạy: `PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -m pytest tests/test_tiktok_workflow.py -q -k "..."`).
- ❌ `tests/test_tiktok_workflow.py`: CHƯA áp edit (4 test cũ + 8 test mới đã soạn xong
  snippet, phiên bị cắt trước khi splice).
- ❌ `docs/tiktok-ui-compatibility.md`: CHƯA update COMPAT-OPEN-TIKTOK-002 +
  COMPAT-CAPTION-002 + COMPAT-CAPTION-004 (đã xác định đúng đoạn cần sửa: CAPTION-002
  còn ghi "MOVE_END + 256 DEL" + "verify `end_result.ok`" → phải thành 432 DEL +
  UI-verified dump-lại; OPEN-TIKTOK-002 thiếu marker reboot_action_started, P1-08
  checkpoint restore, P2-01 counter per-signature).
- ❌ Full suite: CHƯA chạy xanh.
- Không commit/push (user rule cho vòng audit này).
- Helper script nằm NGOÀI repo: `C:\Users\Kibe\fix_v2_edits.py` (đừng commit).

## 8 test mới — tên + thiết kế (phiên test round 2026-08-09, đã soạn, chưa splice)

Vị trí: P1-01/P1-02 vào `TestStateMachine` (sau `test_open_tiktok_coordinate_fallback_gated_by_soft_reboot_outcome`);
P1-03/P1-04/P1-05/P1-06 vào `TestCaptionFill`; P1-08/P2-01 vào `TestAdapter`
(sau `test_wait_for_feed_atx_kill_budget_per_signature_two_error_codes`).

- `test_p1_01_reboot_fail_outcome_attempted_and_coordinate_called` — integration qua
  `_handle_open_tiktok` THẬT: mock `prepare_app_for_automation` ok, `_wait_for_feed` False,
  `_capture_soft_reboot_artifact`→path, `_reserve_proxy_recovery_handoff`→(None,None),
  `_soft_reboot_recovery`→False; assert outcome `ATTEMPTED_FAILED` +
  `checkpoint["soft_reboot_recovery"]["reboot_action_started"] is True` +
  mock `_coordinate_fallback_after_ladder_exhausted` được gọi. Cần
  `machine.current_state = WorkflowState.OPEN_TIKTOK` (default INIT → NOT_ELIGIBLE) +
  `adb_client`/`device_transport` set (điều kiện `_soft_reboot_recovery_allowed`).
- `test_p1_02_reboot_action_started_marker_gates_outcome` — unit `_soft_reboot_recovery_outcome`
  với checkpoint variations: RECOVERY_RESERVED+marker False → NOT_RESERVED (cấm),
  +marker True → ATTEMPTED_FAILED (được), RECAPTURED → VERIFIED, các outcome khác → cấm.
- `test_p1_03_hashtag_caption_survives_sanitize_and_escape` — `#duet #fyp #mùa hè` giữ
  nguyên (dropped==[]); emoji 🎉 → space + dropped `["🎉"]`; escape `\#duet%s\#fyp`.
- `test_p1_04_chunk_verify_dump_fail_stops_typing_cleanup_fail_closed` — caption
  `"a"*(chunk_size+5)`, dump raise sau chunk 1 → `input text` đúng 1 lần; 2 case
  clear_ok True/False → residue False/True.
- `test_p1_05_clear_returns_false_when_ui_still_has_text` — dump lại còn text → False;
  dump không EditText (None) → False; vẫn tap field trước (assert calls[0]).
- `test_p1_06_empty_field_text_never_falls_back_to_whole_screen` — EditText focused rỗng +
  node khác có text → field_text `""`, chunk/ratio verifier False (KHÔNG fallback);
  không EditText → None → fallback whole visible → True.
- `test_p1_08_checkpoint_round_trip_restores_atx_budget_no_second_kill` — Reporter fake
  (save_checkpoint/load_checkpoint); run 1 kill NULL_ROOT → save → machine2 load →
  signatures/evidence restore → poll lại cùng signature → recover==0.
- `test_p2_01_alternating_dump_signatures_never_reach_consecutive_threshold` —
  `[null, idle, null, idle]` → recover==0 + `atx_kill_signatures == {}` (counter reset khi
  đổi signature, không cộng dồn).

4 test cũ sửa: escape (assert `\#fyp%s\#tiktok`, `\#a\\\\b`, metachar), clear single
delete (dump 2 lần + EditText `text=""` + DEL `2+432` + không tap khi field mất), clear
taps field (dump 2 lần, class EditText, DEL `2+432`), sanitize whitelist (assert GIỮ
`#@!` + `dropped == ["💥"]`).

## Từng finding — before → after

### P1-01 — outcome thật sau action (không cache stale)
- Bug: `_maybe_soft_reboot_recovery()` set `context.soft_reboot_recovery_outcome` ở
  ĐẦU hàm (trước khi reserve/reboot), các terminal branch sau action KHÔNG cập nhật →
  `_handle_open_tiktok` đọc NOT_RESERVED stale dù reboot đã chạy → coordinate fallback bị
  chặn oan.
- Fix: cập nhật field ở MỌI terminal branch: handoff fail → `NOT_RESERVED`, reboot action
  fail → `ATTEMPTED_FAILED`, post-verifier fail → `ATTEMPTED_FAILED`, verifier pass →
  `VERIFIED`. `_handle_open_tiktok` vẫn đọc field (không đổi code ở đó).
- Test: reserve → `_soft_reboot_recovery` mock False → assert
  `context.soft_reboot_recovery_outcome == "ATTEMPTED_FAILED"` +
  `SoftRebootRecoveryOutcome.allows_coordinate_fallback(...) is True` + `reboot_action_started is True`.

### P1-02 — ATTEMPTED_FAILED chỉ khi reboot_action_started
- Bug: `_soft_reboot_recovery_outcome` trả ATTEMPTED_FAILED chỉ vì attempt count +
  recovery state `RECOVERY_RESERVED` — dù reboot action chưa bao giờ gửi.
- Fix: context field `reboot_action_started: Optional[bool]` + persist
  `checkpoint["soft_reboot_recovery"]["reboot_action_started"]=True` TRƯỚC khi gọi
  `self._soft_reboot_recovery(...)` (thêm `_record_soft_reboot_recovery("RECOVERING",
  signature, reboot_action_started=True)` + `_save_checkpoint(status="RECOVERING")`).
  Classifier mới:
  ```python
  reboot_action_started = bool(recovery.get("reboot_action_started") or False)
  if same_signature and recovery_state in {"RECAPTURED", "RETRYING"}: return VERIFIED
  if same_signature and recovery_state and reboot_action_started: return ATTEMPTED_FAILED
  if consumed or (same_signature and recovery_state): return NOT_RESERVED
  ```
- Test: checkpoint `{"signature": sig, "state": "RECOVERY_RESERVED"}` + attempts[sig]=1 →
  `NOT_RESERVED`; `{"state": "RECOVERY_FAILED", "reboot_action_started": True}` →
  `ATTEMPTED_FAILED`.

### P1-03 — sanitizer GIỮ hashtag
- Bug: `_ADB_INPUT_TEXT_SAFE_RE = r"[^A-Za-z0-9\s\u00C0-\u024F\u1E00-\u1EFF]"` — `#` (và
  `@.,!?&_-`) bị thay bằng space → typing fallback gõ caption hashtag mất mọi `#`.
- Fix: thêm `#@.,!?&_-` vào whitelist.
  `_escape_adb_input_text` giờ escape `#` + shell metachar TRƯỚC space→`%s`:
  ```python
  escaped = text.replace("\\", "\\\\")
  escaped = re.sub(r"([#&;!?$()'`<>|])", r"\\\1", escaped)
  return escaped.replace(" ", "%s")
  ```
  (device sh coi `#` là comment → `\#` literal; `&`/`;`/`|`/`$`/... là control operator.
  Không dùng `"` trong escape set — nó đã bị sanitizer loại.)
- Test cũ `test_sanitize_adb_input_text_whitelists_and_chunk_landed_fallback`: assert
  `"#" not in cleaned` + `dropped == {"!", "@", "#", "💥"}` → SAI theo v2 → sửa thành
  assert GIỮ `#@!` + `dropped == {"💥"}`.
- Test mới: `_sanitize_adb_input_text("#duet #fyp")` → `("#duet #fyp", [])`; typing
  fallback payload = `\#duet%s\#fyp` (decode `\#`→`#`, `%s`→space ra đúng caption).

### P1-04 — dump-fail sau typing → cleanup fail-closed
- Bug: chunk-verify dump raise → `chunk_xml=None` → điều kiện `if chunk_xml is not None
  and not chunk_landed(...)` bỏ qua verify → tiếp tục gõ chunk kế (fail-open).
- Fix: `chunk_xml is None` → log + dừng ngay, `_clear_caption_input()` → residue
  True/False, `return False` (KHÔNG gõ chunk kế). Hậu-kiểm `final_xml` dump fail cũng đi
  cleanup path (trước là `return False` trần).
- Test: caption >400 ký tự (2 chunk), dump raise sau chunk 1 → chỉ 1 lần `input text`,
  `caption_typing_residue is True` khi `_clear_caption_input` mock False.

### P1-05 — clear caption UI-verified
- Fix `_clear_caption_input` (đầy đủ):
  (a) `field = _find_caption_field(adapter, adapter.dump_ui())`; `tap_ok = adapter.tap(...)`;
      `tap_ok is False` → fail-closed;
  (b) `delete_count = self.CAPTION_TYPING_CHUNK_SIZE + 32` (=432) DEL;
  (c) `verify_xml = adapter.dump_ui()` → `_caption_field_text_from_xml(root)` → `None`
      (không có EditText) → False; `field_text.strip() == ""` → True; còn text → False.
- Test cũ: `test_clear_caption_input_uses_single_long_delete` +
  `test_clear_caption_input_taps_field_when_visible` — fake dump phải có
  `<node class="android.widget.EditText" ... text=""/>`; assert DEL count `2 + 432`.
- Test mới: field còn text → False; dump không EditText → False; tap trả False → False.

### P1-06 — field rỗng vs không có field
- Fix `_caption_field_text_from_xml`: bỏ vòng `for ... if text: return text`;
  `return candidates[0][2]` (text của candidate tốt nhất — focus trước, area sau — kể cả `""`).
- Hệ quả: `_caption_chunk_landed`/`_caption_typing_ratio_ok` dùng `""` → không match
  whole-screen (không fallback). `None` chỉ khi không có EditText nào.
- Test: EditText focused rỗng + node text khác có nội dung → `_caption_field_text_from_xml
  == ""`, `_caption_typing_ratio_ok(xml, "caption") is False`, `<hierarchy/>` → None.

### P1-07 — immutable frame (screenshot/tọa độ/verdict cùng observation)
- Fix `_coordinate_fallback_after_ladder_exhausted` (thứ tự mới):
  1. `if not self._enforce_portrait_rotation(): return False` (FINAL_BLOCKED, không chụp);
  2. `screenshot_path = self._capture_coordinate_fallback_artifact()` (1 frame duy nhất);
  3. visual accept (`_package_is_foreground is True` + `_visual_feed_surface_visible`);
  4. `point = self._bottom_nav_home_point_scaled(adapter)` (SAU orientation) + strip gate
     dùng CHÍNH `screenshot_path`; checkpoint `screenshot` = path đó.
- Test: `_enforce_portrait_rotation` mock False → fallback False + `shots == []`; mock True
  → `len(shots) == 1` và `checkpoint["coordinate_fallback"]["screenshot"] == shots[0]`.

### P1-08 — ATX budget restore khi checkpoint resume
- Fix: `_save_checkpoint` persist `atx_kill_signatures` + `atx_kill_evidence` (dict copies);
  `_load_checkpoint` restore với type-validate (`isinstance(dict)`, evidence chỉ nhận list);
  `_recover_wait_feed_uiautomator` cũng persist signatures inline.
- Test: Reporter fake save → machine2 `_load_checkpoint` → `atx_kill_signatures[sig] is True`
  → `_wait_for_feed` cùng signature dump fail ×3 → recover == 0 (không kill lần 2).

### P2-01 — counter dump-fail per-signature
- Fix `_wait_for_feed`: `current_dump_signature: Optional[str] = None`;
  khi signature đổi → reset counter; valid dump → reset + `current_dump_signature = None`.
- Test: `DumpAdapter([null_root, idle_state])` → recover == 0 (trước đây 2 lần liên tiếp
  bất kể signature → kill ở IDLE); `[null_root, null_root]` → 1.
  Test cũ `test_wait_for_feed_atx_kill_budget_per_signature_two_error_codes` vẫn pass
  ([null,null,idle,idle] → 2 kill).

## Edit-script recipe (đã verify)

1. Script chạy bằng Windows path THẬT: `python "C:/Users/Kibe/fix_v2_edits.py"` (MSYS
   `/c/...` bị bash convert sai).
2. Load file: bytes → decode utf-8 → `replace("\r\n","\n")` → assert `"\r" not in lf`.
3. Mỗi replacement: `assert text.count(old) == 1` TRƯỚC khi replace; abort khi 0/>1.
4. Save: `out = lf.replace("\n","\r\n").encode("utf-8")`.
5. Verify: `count(b"\r\n")` vs `count(b"\n")` (LF-only == 0), `py_compile.compile(path,
   doraise=True)`, chạy `pytest -k` liên quan.
6. OLD không match → debug bằng `ast.literal_eval` các old-string (parse script, lấy args
   của mọi `rep(...)`) rồi char-diff với file — in 2 bên ±20 ký tự quanh diff đầu.

## Snippet-splice cho payload CODE LỚN (LF test file — verified 2026-08-09)

Viết test mới/code mới inline trong edit-script = mắc 2 lần liên tiếp (raw triple-quoted
vẫn bị mangle: `\\#` thành `\#`, mất quote, typo copy-paste, emoji/Vietnamese vỡ giữa
chừng). Pattern đã chạy ổn:

1. **Payload = file snippet riêng**, bọc trong dummy class để `write_file` syntax-check:
   ```python
   class _SNIP:
       def test_p1_03_hashtag_caption_survives_sanitize_and_escape(self):
           ...
   ```
   (method 4-space indent + `self` là valid module-level syntax → lint OK; nếu viết thẳng
   method không bọc class → `IndentationError: unexpected indent` từ linter, đó là dấu
   hiệu cần bọc.)
2. **Editor script đọc snippet, bỏ dòng `class _SNIP:`, splice vào anchor**:
   ```python
   def load_snip(path):
       lines = open(path, encoding="utf-8", newline="").read().split("\n")
       assert lines[0] == "class _SNIP:"
       return "\n".join(lines[1:]).lstrip("\n")
   # test file LF: open(newline="") read + write (không translate), assert "\r" not in src
   assert src.count(old_anchor) == 1
   src = src.replace(old_anchor, old_anchor + "\n" + load_snip("_snip_t3.py"))
   ```
3. Anchor chọn dòng kết thúc DUY NHẤT của test trước (vd `assert len(fallback_calls) == 1`)
   — ngắn, ít lỗi hơn chép cả block cũ. Insert = `old_anchor + "\n" + snippet`.
4. Sau splice: `py_compile`, verify LF (`"\r" not in src`), chạy `pytest -k` mới.
5. Xoá snippet files + edit-script trước khi bàn giao (untracked ở repo root).

## Test run

```bash
cd /d/Taadaa/Tiktok-video
PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" \
  -m pytest tests/test_tiktok_workflow.py -q -k "soft_reboot or clear_caption or sanitize or caption_typing or wait_for_feed_atx or coordinate_fallback or open_tiktok or checkpoint"
```
