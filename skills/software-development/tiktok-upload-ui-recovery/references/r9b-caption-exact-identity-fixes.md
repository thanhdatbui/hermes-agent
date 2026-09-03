# R9b — Caption exact-identity ONLY (no anonymous/generic EditText fallback)

Round: R9b final caption P1 (2026-08-09) — tiếp nối R8b (xem
`r8b-caption-semantic-only-fixes.md`). Trạng thái: source + tests đã sửa,
docs CHƯA, full suite CHƯA chạy xong, NO commit (bị cắt bởi iteration limit).

## Vấn đề (Sol R8 P1 hole)
`_find_caption_field` sau R8b (allowlist + specific hints) VẪN còn fallback:
EditText vô danh RỘNG (width≥400, height≥60) + composer screen proof
(Đăng/Post/Tiếp/Next hoặc rbp/sh8/shd) → được chọn làm caption field.
Hậu quả thật (test `events` ghi lại): `_handle_caption_fill` tap `search_edit_text`
focus vào generic field, gửi MOVE_END + 432×DEL + KEYCODE_POUND + `input text`
+ clipboard broadcast → nội dung được gõ/xóa vào search/comment control.

## Nguyên tắc R9b — exact caption identity only, trước MỌI side effect
1. Chỉ chọn node có EXACT caption identity: resource-id tail sau `/` (hoặc
   `name`) ∈ `KNOWN_CAPTION_COMPONENT_IDS` (`caption_edit_text`,
   `description_edit_text`, `post_description`, `composer_caption`,
   `g9u`, `gv0`). g9u/gv0 giữ trong allowlist vì CÓ documented evidence
   (composer-surface regression, live-resource tests) — KHÔNG được phát minh
   ID mới.
2. Composer screen proof (Đăng/Post/.../rbp/sh8/shd) KHÔNG BAO GIỜ promote
   EditText anonymous/generic thành caption field — bounds/focus chỉ narrow
   confirm một candidate ĐÃ semantic, không tạo candidate mới.
3. `field is None` là kết quả fail-closed ĐÚNG: caller (clear/typing/tap)
   không được gửi bất kỳ tap/key/input nào khi không có identity.
4. `_xml_has_composer_post_proof` — helper đẻ ra để gate fallback anonymous —
   ĐÃ XÓA (dead code sau R9b). Hints text (Suy nghĩ của bạn/Thêm mô tả/...)
   cũng bị bỏ (không phải component-ID identity, có thể trúng label/view).

## SHAPE mới của `_find_caption_field` (đã splice source, CRLF)
```python
for resource_id in sorted(KNOWN_CAPTION_COMPONENT_IDS):
    field = adapter._find_ui_element(xml_text, resource_id=resource_id)
    if field and field.get("center"): return field
# XML path: CHỈ node EditText pass `_is_caption_field_node` (exact ID)
# + bounds; sort (top, left); trả {"center":..., "bounds":...}
```
No anonymous/generic iteration, no screen-proof gate at all.

## Patterns regression test (đã viết, RED → GREEN)
- `test_caption_field_exact_ids_only_no_anonymous_fallback` — anonymous
  EditText + Đăng → None (trước: (540,1000)).
- `test_caption_field_rejects_wide_focused_generic_ids_with_composer_proof`
  — ADAPTER GHI resource_id được hỏi: `queried ⊆ KNOWN_...` và
  `search_edit_text`/`comment_input` KHÔNG bao giờ xuất hiện — chứng mình
  finder không hỏi generic ID.
- `test_caption_field_selects_exact_caption_edit_text_and_verifier` —
  caption_edit_text exact thắng focused generic; verifier
  (`_caption_field_text_from_xml`/`_caption_chunk_landed`/`_ratio_ok`) nhận
  text từ semantic node.
- `test_caption_field_exact_opaque_ids_documented_evidence_only` — g9u/gv0
  pass khi evidence có; ID phát minh (vd `thumbnail_caption`) không qualify.
- `test_caption_fill_generic_edit_text_never_tapped_or_cleared` — toàn
  màn hình generic + Đăng → `_handle_caption_fill() is False` và
  `events == []` (KHÔNG tap/keyevent/broadcast/input).
- Đổi fixture cũ dance: mọi dump EditText trần dùng trong caption/final-
  composer/clear tests phải gắn `resource-id="caption_edit_text"` (byte-level
  replace, anchor `count==1`); `test_caption_field_text_respects...` đã dùng
  bounds identity nên không đổi.

## Test-harness pitfall mới (đoạn này)
- `_handle_caption_fill` thẳng với `StateContext()` mới: `dry_run=True` mặc
  định — nếu test muốn REAL path NHẤT ĐỊNH set `machine.context.dry_run=False`
  + seed `machine.context.selected_hashtags=[...]` (account_row=None quá →
  `format_hashtag_text(None)` TypeError) + monkeypatch
  `tiktok_workflow.state_machine.time.sleep` (mặc định sleep(2) thật).
- RED xác nhận bằng pytest THẬT trước khi sửa source: chạy
  `pytest -k "caption_field_exact or caption_field_rejects or
  caption_field_selects or caption_fill_generic"` → 4 failed / 1 passed
  (exact-caption test pass-sẵn vì finder allowlist ngay, cái còn lại fail
  vì fallback). Đừng tin brief — xem failure thật.

## EOL pitfall MỚI round này — `Path.read_text()` phá CRLF
`state_machine.py` (CRLF) bị chuyển QUIETLY thành LF: script dùng
`path.read_text(encoding=...)` (universal newline → đọc thành `\n`) rồi
`write_text(..., newline='')` → ghi `\n` → LF. `read_text()` KHÔNG nhận
`newline=` (TypeError) nên dễ lẫn. VERIFY toàn bộ pipeline: quét bytes
trước (`is_crlf = b'\r\n' in raw`) + sau (`"\\r" not in text` cho LF-pure /
`bare LF == 0` cho CRLF-pure). Restore CRLF: đọc bytes → giải mã → patch
trên text đã decode với MARKS `\r\n` → `\n` cho từng thao tác, hoặc
normalize cuối: `data.replace(b"\n", b"\r\n")` CHỈ khi chắc `\r` không sót
(kiểm sau trước khi sửa). Luôn verify `git diff` + đếm EOL sau khi apply.

## TODO remainder (round bị cắt)
- Convert state_machine.py VỀ CRLF (LF hiện tại là corruption từ
  read_text/write_text).
- Chạy lại `pytest -k "caption or final_composer"` → full suite.
- Docs: docs/tiktok-ui-compatibility.md ghi R9b policy — bỏ "fallback
  EditText rộng" còn ở COMPAT-CAPTION-002/004 (~line 178, 225); trộn entry
  exact-ID-only pre-side-effect mới.
- Xóa 2 helper script `_r9b_edit_tests.py`/`_r9b_edit_sm.py` (streamline
  ngoài repo).
- `git diff --check`; NO commit (theo task).