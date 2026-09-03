# Round-3 RED evidence: Sol P1 proof paths (2026-08-09)

Phase mode: **RED-only evidence** (KHÁC round 1 `f1-evidence-caption-round.md` — round 1
fix source; round 3 CHỈ thêm/run 3 test RED trong `TestCaptionEvidencePhase`, KHÔNG sửa
production/docs, KHÔNG commit). Kết quả: **3 RED = CONFIRMED candidates** (production
chưa đúng như design kỳ vọng), old 4 F-tests giữ GREEN, sẵn sàng làm target cho next
source change. Chạy: `python -m pytest tests/test_tiktok_workflow.py::TestCaptionEvidencePhase -v`
→ `4 passed, 3 failed` (file dùng PYTHONPATH=scripts convention).

## Convention (đã thiết lập từ round này — round sau giữ nguyên)

- Mỗi proof path là 1 test method riêng + section marker tiếng Anh `# --- P1-N (round-3) ----`
  theo đúng style F1/F2/F3/F6 cũ. Docstring: mô tả điểm mù current code + hành vi an toàn kỳ vọng.
- Fake adapter CHỈ emulate adapter transport (`dump_ui` / `_tap_if_found` / `_find_ui_element` /
  `tap` / `tap_long`) — KHÔNG được monkeypatch method state_machine; production flow giữ nguyên
  (rule trong header block của class).
- Mỗi RED test chứa 1 **control GREEN component** (assert nhánh đúng vẫn chạy được) để chứng
  minh fail chỉ ở đúng proof path, không phải helper hỏng chung.
- Assertion phải DISCRIMINATING (chỉ fail đúng khi vulnerability hiện diện): đo bằng side-effect
  thật (`keyevents == []`, `paste_coords not in taps`, `selected["center"] != backup_center`)
  chứ không phải "không crash".

## RED#1 — F2/P1-1: missing `focused` attr vẫn gửi keyevents

`test_f2_p1_1_clear_omits_keys_when_caption_focused_attr_missing` (~L9978):
post-tap dump = exact caption node tại identity bounds/center, attr `focused` OMIT hoàn toàn
(không phải `focused="false"`), không generic node nào. Assert: `result is False` +
`keyevents == []`.

FAILED thật: current code gửi `['input','keyevent','KEYCODE_MOVE_END']` + `['input','keyevent',
'KEYCODE_DEL' ×432]` (CAPTION_TYPING_CHUNK_SIZE 400 + 32 margin). Root:
`node.attrib.get("focused", "true") == "false"` — missing attr default thành focused nên nhánh
P1-1 (explicit false) không kích hoạt. Đây là gap đã biết từ round 1 (xem
`f1-evidence-caption-round.md` — quyết định "missing attr = OK" để giữ 362 green); giờ có
executable RED regression cáo buộc fail-closed đúng design.

## RED#2 — F6/P1-2: backup impostor overlap center vẫn được chọn

`test_f6_p1_2_backup_impostor_center_never_selected_as_caption_field` (~L10195):
- dump: `caption_edit_text_backup` ĐẦU + exact `caption_edit_text` SAU, bounds KHÁC NHAU nhưng
  CẢ 2 chứa center adapter trả về (backup center, overlap).
- fake adapter substring-selector trả `{"center": backup_center, "bounds": ...}`.
- Control GREEN: exact node vẫn phải thắng (`selected is not None`), assert
  `selected["center"] != backup_center`.

FAILED thật: `_find_caption_field` trả `{'center': (200,400), ...}` — candidate BACKUP.
`_xml_has_caption_at_center` (center-containment correlation, fix round 1) PASS vì backup
bounds chứa center → impostor lọt qua. Khác với RED test backup-only (đã GREEN): ở đó dump
KHÔNG có exact node nên `_xml_has_exact_resource_id_tail` chặn; ở đây overlap làm containment
correlation vô dụng.

## RED#3 — F3/P1-3: paste tap dù exact caption node unfocused

`test_f3_p1_3_no_paste_tap_when_exact_caption_node_unfocused` (~L10096):
- dump: exact caption node `focused="false"` + generic search `focused="true"` + menu Dán hiện.
- `_fill_caption_clipboard("#việt nam")` (non-ASCII → thẳng clipboard path).
- Assert: `result is False` + `paste_coords not in taps`.

FAILED thật: tap (500,650) Dán được gửi. `_xml_has_caption_field` là global witness KHÔNG
đòi focus (chỉ cần exact caption node bất kỳ trong dump) → `_tap_if_found("Dán")` chạy →
paste vào generic đang focus = side effect sai. Identity cần bằng chứng FOCUS, không phải
"có mặt".

## Pitfalls khi soạn RED tests (mắc 2026-08-09)

1. **Class-body scope gotcha (Python)**: `class FakeX: _re = _re` với `import re as _re`
   trong method → `NameError: name '_re' is not defined`. Class body KHÔNG read enclosing
   function locals khi tên được gán ngay trong class body (LOAD_NAME semantics: class ns →
   global → builtins). Không gán biến import của method làm class attribute; fake không
   cần `_re` thì đừng thêm.
2. **Iterator fake = artifact**: `_dumps = iter([pre, post])` + dump thứ 3 trong `_clear_caption_input`
   (verify sau DEL) → `StopIteration` làm `result is False` TRÙNG ngẫu nhiên → RED evidence
   lẫn lộn. Fake dump đơn giản: `def dump_ui(self): return post_xml` (pre/post có thể cùng
   dump khi chỉ cần field tồn tại ở identity).
3. **Patch tool arg quá lớn (>~8K tokens) → stream timeout** giữa chừng (patch bị cắt, file
   có thể thành nửa câu). Tách mọi patch thành nhiều call nhỏ
   (docstring riêng, body riêng); sau mỗi patch RE-READ vùng đã sửa.
4. **Patch chèn trước 1 class: phải giữ class declaration trong new_string** — old_string
   dạng `\n\nclass TestPostHandler:` bị thay thành "" đã clobber dòng class → toàn bộ
   method bên dưới lệch indent (mắc thật turn này). Sau mọi patch vào file test 11.5k dòng:
   AST parse + chạy 1 test của class kế cận để bắt clobber.
5. **Verify RED-only phase**: script ad-hoc (thể `scripts/verify-caption-evidence-phase.py`)
   assert: AST parse, LF pure, `git diff --check` clean, old F-tests PASS, new tests FAIL với
   đúng assertion text, neighbors (`TestPostHandler`, `TestCaptionFill`) pass. Với RED phase
   pytest exit 1 là KẾT QUẢ ĐÚNG (suite không green) — đừng sửa test để "pass".

## Trạng thái cuối
- Chỉ `tests/test_tiktok_workflow.py` đổi (LF pure 0 CRLF, 11757 dòng, +181). `state_machine.py`
  / `adapter.py` / docs untouched (chỉ đọc). Không commit.
- TestCaptionEvidencePhase: 4 pass (F1/F2/F3/F6 old) + 3 fail (P1-1/P1-2/P1-3) — đúng sản
  phẩm RED. Neighbors smoke 3 pass.
- Next step khi user cho phép source change: fix 3 điểm — (a) P1-1: missing attr →
  fail-closed (cần đổi luôn test `test_clear_caption_input_*` dump lên có `focused` attr —
  xem round 1 note về cục chế 362); (b) P1-2: `_xml_has_caption_at_center` thêm điều kiện
  phải là node NHỎ NHẤT/innermost chứa center hoặc khớp bounds exact; (c) P1-3: thêm gate
  focus vào `_xml_has_caption_field` hoặc dùng caption node focused trước khi tap paste.