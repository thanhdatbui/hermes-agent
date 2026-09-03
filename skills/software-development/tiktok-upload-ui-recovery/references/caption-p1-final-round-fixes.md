# Final caption P1 batch — production FIXED (2026-08-09, 3 RED → GREEN)

Round sau `caption-evidence-r3-p1-proofs.md`: 3 RED regressions giờ GREEN trên production
(`scripts/tiktok_workflow/state_machine.py`), full suite `tests/test_tiktok_workflow.py` =
**364 pass / 1 fail** (fail cuối là fixture gap `tap_long`, xem cuối file). EOL-safe script
pattern (CRLF normalize → assert count → restore) theo §13 — áp cho cả SM (CRLF) lẫn tests (LF).
NO commit. Không đụng docs.

## P1-1 — missing `focused` attr KHÔNG còn là bằng chứng focus

**Bug cũ**: `_clear_caption_input` post-tap loop dùng `node.attrib.get("focused", "true") == "false"`
→ attr missing default thành focused → gửi MOVE_END + 432×DEL vào control đang focus.

**Fix**: `if node.attrib.get("focused") != "true": log + return False` (repo chỉ literal
`focused="true"` mới được gửi keyevent; missing/false đều fail-closed 0 keyevent).

**Fixture legitimation** (bắt buộc — không đổi assertion/không nới gate):
thêm `focused="true"` vào caption node trong các dump fixture của:
`test_clear_caption_input_uses_single_long_delete`, `test_clear_caption_input_taps_field_when_visible`,
`test_clear_caption_input_tap_not_acked_fails_closed`, `test_clear_caption_input_tap_none_fails_closed`
(các test này assert keyevent/verification flow — dump thiếu attr giờ fail-closed đúng thiết kế,
nên fixture phải explicit `focused="true"`).

## P1-2 — exact-node-first: back/hình từ NODE EXACT, không từ adapter substring

Bug cũ: adapter `_find_ui_element` (substring resource-id) trả geometry impostor
(`caption_edit_text_backup` đứng đầu dump) dù `_xml_has_caption_at_center` (center-containment)
pass vì node exact chồng bounds — backup center được chọn.

Fix trong `_find_caption_field` (structure 3 bước):
1. Dump có EditText (`_xml_has_any_edit_text`) → parse trực tiếp: node đầu tiên có class
   `EditText` + `_is_caption_field_node` + bounds hợp lệ → trả `{"center": ..., "bounds": (l,t,r,b)}`
   **tuples** (canonical). Đây là "direct parsed exact node / never backup".
2. Nếu không có node exact: adapter allowlist CHỈ khi dump KHÔNG có EditText (gv0 live-resource
   compat). Dump có EditText nhưng không node exact → fail-closed None (không tin adapter substring).
3. Helper mới `_node_bounds(node)` cho parse bounds canonical; `_xml_has_caption_focused(xml)`
   cho P1-3 (node caption exact phải focused literal).

Hệ quả assertion: `test_caption_field_selects_exact_caption_edit_text_and_verifier` giờ nhận
bounds TUPLE `(30,200,1050,300)` (cùng geometry, form khác dict adapter) → cập nhật assertion
(cho phép — nghĩa giống hệt). Test F6/P1-2 mới giữ `center == exact_center` (không thể phân biệt
impostor bằng VALUE trong fixture chồng bounds) + **`bounds == (100,300,300,500)`** chứng minh
selected là NODE EXACT, không phải dict adapter.

## P1-3 — paste gate = identity AND focused trên CÙNG dump

Fix `_fill_caption_clipboard`: cả 2 paste gate (tìm `Dán`/`Paste` trực tiếp VÀ sau tap_long
`xml_text2`) đổi từ `_xml_has_caption_field(xml)` sang
**`_xml_has_caption_field(xml) AND _xml_has_caption_focused(xml)`** — generic search focused +
exact caption unfocused/missing-attr → KHÔNG tap paste (paste vào generic = side effect sai).

Test fixture legit: `test_caption_unicode_uses_clipboard_and_verifies_paste` caption node +
`focused="true"`.

## PITFALL cuối — fixture gap lộ qua gate mới, KHÔNG phải production regression

Sau khi sửa xong 3 RED → full suite còn 1 fail:
`test_tokenized_caption_token_fail_clears_field_before_fallback` với
`'FakeAdapter' object has no attribute 'tap_long'` — ASCII token-fail path giờ chạm nhánh
long-press real (gate mới bắt paste-first phải có focus; fixture thiếu `tap_long`).
**Đây là test-fixture gap**: thêm `tap_long(x, y, duration_ms=1200)` vào FakeAdapter của test đó
(hoặc cho paste gate của fake trả success sớm) → chạy lại full suite (kỳ vọng 365/365).
Đừng sửa production để né — flow phải long-press là đúng.

## Recipe đã dùng (verified)

- Edit script python: đọc bytes → assert EOL type (CRLF/LF) → normalize `\r\n`→`\n` cho file CRLF →
  `must_replace(old, new, count=1)` với count-assert TỪNG khối → restore CRLF → write `newline=""`.
- **Pitfall 2026-08-09 lần này**: docstring `"""` lồng trong `"""` → write_file lint bắt SyntaxError
  NGAY (bổ sung §13 R8b pitfall (8)) — dùng `'''` cho anchor/new chứa `"""`.
- Run: `pytest tests/test_caption...` theo node id; confirm RED trước, GREEN sau.