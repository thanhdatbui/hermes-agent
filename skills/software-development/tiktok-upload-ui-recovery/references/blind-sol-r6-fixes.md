# Blind Sol R6 — 5 P1 findings (2026-08-09)

Task template: "Fix N P1 findings from blind Sol R#: <danh sách>. Add regression tests + docs + run full pytest, no commit."

Files: `scripts/tiktok_workflow/state_machine.py` (CRLF THUẦN), `tests/test_tiktok_workflow.py` (LF THUẦN), `docs/tiktok-ui-compatibility.md` (CRLF THUẦN).

## P1-01 — double soft-reboot/reserve (per-signature one-shot)

Bug: `_soft_reboot_recovery_outcome` trả `NOT_RESERVED` cho checkpoint đã consumed/same-signature, và `_maybe_soft_reboot_recovery` coi `NOT_RESERVED` là tín hiệu "go" → reserve+reboot lại CHÍNH signature đã reserve (double reboot).

Fix (2 chỗ):
- `_soft_reboot_recovery_outcome`: giữ nhánh `if consumed or (same_signature and recovery_state): return NOT_RESERVED` — NOT_RESERVED = blocked (cấm coordinate fallback), KHÔNG phải go.
- `_maybe_soft_reboot_recovery` NGAY TRƯỚC reserve block (trước `_capture_soft_reboot_artifact("before")`): hard-block `return False` khi `attempts[signature] >= 1` HOẶC `checkpoint["soft_reboot_recovery"].signature == signature` (bất kỳ state — kể cả state đã crash-reconcile về NOT_RESERVED). Chỉ signature THẬT SỰ FRESH mới được reserve.

Regression test cần viết: gọi `_maybe_soft_reboot_recovery` 2 lần cùng signature — lần 2 trả False, `attempts`/`total`/`reboot_action_reserved` KHÔNG đổi, outcome NOT_RESERVED, không coordinate fallback. Variant: checkpoint cũ cùng signature (state RECOVERING, reserved-only) → cũng không reserve/reboot.

## P1-02 — VERIFIED chỉ với durable proof

Bug: checkpoint state `RECAPTURED`/`RETRYING` một mình → VERIFIED (legacy/thiếu fields bị nâng sai).

Fix:
- Marker mới `post_reboot_verified=True` persist vào checkpoint tại nhánh RECAPTURED (sau after-artifact + foreground verifier pass — `_record_soft_reboot_recovery("RECAPTURED", ..., post_reboot_verified=True)`).
- `_soft_reboot_recovery_outcome` trả VERIFIED CHỈ khi: same_signature AND state ∈ {RECAPTURED, RETRYING} AND `reboot_action_started` AND `post_reboot_verified`. Legacy/incomplete → rơi xuống NOT_RESERVED blocked (fail-closed).

Tests: RECAPTURED không marker → không VERIFIED; +started nhưng thiếu post_reboot_verified → vẫn không VERIFIED; đủ cả 2 → VERIFIED + allows_coordinate_fallback.

## P1-03 — ATX-kill evidence/persist fail-closed

Bug cũ: `_recover_wait_feed_uiautomator` chạy tiếp dù `before`/`after` artifact None, và nuốt lỗi `_save_checkpoint` (log + continue) — vừa thiếu evidence vừa tiếp tục poll.

Fix: method trả `bool`; fail-closed khi:
- `before` artifact None → return False NGAY (KHÔNG gọi `_recover_uiautomator`, không tiêu thụ budget);
- `after` artifact None → return False (recovery đã chạy nhưng evidence thiếu);
- `_save_checkpoint` raise → rollback (`evidence.pop()`, pop key nếu rỗng, `atx_kill_signatures.pop`) → return False, budget KHÔNG bị tiêu thụ.

Caller `_wait_for_feed`: `if not self._recover_wait_feed_uiautomator(adapter, signature): return False` (FINAL path, không continue).

Tests: pre-artifact None → recover không được gọi + signature unmarked; save raise → signature unmarked + evidence rollback + `_wait_for_feed` False.

## P1-04 — post-tap recapture phải là artifact FRESH

Bug: sau tap coordinate fallback, `_wait_for_feed` nhận `screenshot_path` = ẢNH PRE-TAP → false accept (màn hình đã đổi).

Fix: `_capture_coordinate_fallback_artifact(phase="before"|"after")` (filename theo phase, path unique). Sau tap OK → capture `phase="after"` MỚI rồi truyền ĐÚNG path đó cho `_wait_for_feed`; capture fail → fail-closed FINAL_BLOCKED (checkpoint `recaptured=False`, `post_tap_artifact=None`, reason "post-tap recapture failed (fail-closed)"); checkpoint success ghi `post_tap_artifact`.

Test: pre/post path khác nhau, verification nhận post path, checkpoint ghi post_tap_artifact.

## P1-05 — caption verifier semantic field identity

Bug cũ: `_caption_field_text_from_xml` không identity chọn mọi EditText (kể cả search box focus) theo (focused, -area), rồi caller fallback whole-surface khi None.

Fix:
- `_is_caption_field_node(node)`: resource-id/name casefold chứa marker → caption. Marker: `caption, edit_text, edittext, desc, describe, post_description, text_input, input_edit, g9u, gv0` (g9u/gv0 đồng bộ `_find_caption_field`; `gx_` search box KHÔNG qualify).
- `_caption_field_text_from_xml` không identity: CHỈ caption EditText được chọn (focused thắng trong số caption field); không có caption EditText → None. Identity mode (match_bounds/match_center) KHÔNG đổi.
- `_xml_has_edit_text(root)`: caller fail-closed — có EditText nhưng không phải caption → `_caption_typing_ratio_ok`/`_caption_chunk_landed` return False, KHÔNG fallback whole-surface.

Tests: focused search EditText + nonfocused caption EditText → chọn caption; chỉ unrelated focused EditText + whole-surface khớp → verifier False; resource-id g9u → qualify; bare EditText (không id) → None + verifier False.

## TEST-FIXTURE UPDATES BẮT BUỘC (semantic change phá fixture)

1. `_wait_for_feed` ATX-recovery tests (`test_wait_for_feed_recovers_uiautomator_after_repeated_dump_failures`, `test_wait_for_feed_atx_kill_consumed_per_signature_across_relaunch`, `test_wait_for_feed_atx_kill_budget_per_signature_two_error_codes`): StateContext giờ PHẢI có `device_transport` (screenshot ghi bytes → True) + `reporter` (run_dir=tmp_path + `save_checkpoint=lambda _: None`) — recovery bị gate bởi artifact + persistence.
2. Fixture EditText "trần" (không resource-id) trong `test_sanitize_adb_input_text_whitelists_and_chunk_landed_fallback` (edit_xml, focus_xml) và `test_caption_chunk_landed_cumulative_prefix_duplicate_chunk`: KHÔNG còn qualify là caption → thêm `resource-id="...caption_edit_text"`/`"description_edit_text"` để giữ ý định test (focused-wins cần CẢ 2 node caption-like).

## HANDOFF STATUS (session 2026-08-09 kết thúc GIỮA task)

- state_machine.py: ĐÃ áp 5 fix (splice byte-precise), `py_compile` OK, CRLF thuần (12257 CRLF, bareLF=0).
- tests/test_tiktok_workflow.py: fixture updates + 5 regression test mới CHƯA splice (anchor strings đã verify unique).
- docs: COMPAT entries (COMPAT-OPEN-TIKTOK-003/004/005, COMPAT-FEED-002, COMPAT-CAPTION-005 — kiểm tra số hiện có trước) CHƯA viết.
- Full suite CHƯA chạy. Lệnh: `PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -m pytest tests/test_tiktok_workflow.py -q` (kỳ vọng 342+).
- NO commit (đúng yêu cầu task).

## Edit technique (đã dùng, hoạt động)

- Splice theo unique old-block (trích từ file GỐC theo line-range) + `assert norm.count(old) == 1` cho MỌI block; áp sequential.
- EOL: đọc bytes → decode → normalize `\r\n`→`\n` để matching → write `\n`→`\r\n` → assert pure CRLF (`"\n" not in out.replace("\r\n", "")` — so sánh STR, đừng trộn bytes: `b"\n" not in out.replace(b"\r\n", b"")` TypeError khi out là str).
- Block content (chứa `"""` docstring) để trong FILE .txt riêng qua write_file, splice script đọc file — tránh nested-triple-quote syntax error khi nhúng code vào heredoc/chuỗi.
- `write_file` có thể strip leading whitespace DÒNG ĐẦU của block → splice script chuẩn hóa: `new_lines[0] = " " * indent + new_lines[0].lstrip()`.
- Sau khi áp: `py_compile.compile(path, doraise=True)` + đọc lại verify EOL.
