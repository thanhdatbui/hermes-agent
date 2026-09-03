# Canary máy 2 (SM-G930F, serial 9885e6303951513337) — 2026-08-15

Row 1 `thanh.h.dng00`, Mode 1, random, budget 7. **7/7 follow thành công**:
`lm.ngc.dip0, ngohaaenexi, hongggg.yn, thoanvrr5n8, l.thanh.ngn311,
cao.m.phng7, m.ngc4624` (FOLLOW_RESULT status OK, exit 0, budget 7/7, state
máy 2 sạch). Trước đó 1 UID `phannhung1710` đã follow thành công nhưng
popup quyền danh bạ chặn verify → bị báo MANUAL_REVIEW (fix popup xong thì
coi như đã follow — UI cho thấy nút Nhắn tin).

## Chuỗi lỗi máy 2 → fix từng cái (TDD mỗi vòng)
1. `prepare_device fail` → backend UI wedge (Splash + XML rỗng) → đợi
   ~20-30s cho app settle + recover persistent UI, chạy lại.
2. `MANUAL_REVIEW: exact profile identity không khớp UID` → máy 2 handle
   ở `id/sj8` (máy 1: `id/sf5`). Fix: identity gate bỏ phụ thuộc resource-id,
   chỉ cần `profile_identity_from_xml` username + đúng 1 `@`-node.
3. `search navigation fail sau ladder (lần 2)` → handle bị bọc ký tự ẩn
   `\u200e\u2068dianavmoorep9\u2069` (LTR mark + isolate) → normalize không
   khớp. Fix: `_normalize_search_value` strip bidi/isolate/ZWJ/BOM.
4. Cùng lỗi → Top results lặp username (tv_username + zpf + bdu + EditText
   echo). Fix: `_exact_search_result_from_xml` ưu tiên đúng 1 `id/tv_username`.
5. `không thấy đúng một nút Follow trên exact profile` → máy 2 action button
   `id/ff8` (máy 1: `id/fds`), stat `id/shq` (máy 1: `id/sdn`). Fix:
   `_ACTION_BUTTON_IDS = ("id/fds","id/ff8")`.
6. `OPEN_TIKTOK_FAILED` / `identity không khớp sau tap` → sau relaunch máy 2
   hiện popup quyền danh bạ "Cho phép TikTok truy cập vào danh bạ của bạn?"
   + checkbox "Không hỏi lại" + TỪ CHỐI/CHO PHÉP. Fix: PopupHandler thêm
   `contacts_permission()` delegate automation-core `dismiss_popup` (tick
   checkbox TRƯỚC rồi TỪ CHỐI — user bắt buộc), thêm vào dismiss_all.
7. `search navigation fail` lại khi UI đang ở màn "Tìm Liên hệ" (suggested
   contacts) → chạy lại sau khi máy về Feed thì OK (tình trạng tạm).

## Lần chạy sau (vuốt xác nhận, state 7→10)
- `m2-follow7k`: **3 UID mới follow thành công qua nhả-follow confirm gate**:
  `tovy0402780, ngc.anh.phm33, hng.lee679` (state 7→10, budget 10/30) — mỗi
  cái: tap Follow → nút "Nhắn tin" → vuốt 1 lần → dump lại → vẫn "Nhắn tin"
  → success. Không UID nào bị nhả.
- Dừng ở UID thứ 4: `exact profile identity không khớp UID` → **user chửi:
  "fail search k ra thì bỏ qua id khác làm tiếp chứ dừng lại"** → chuyển
  identity mismatch thành skip-continue + `failed_ids` riêng (xem SKILL.md).

## Selector mới phát hiện lần này
- **Hai nút action cạnh nhau**: profile `@mautuoi08` (máy 2) render CẢ HAI
  `id/ff8` — "Follow" (114,789) + "Nhắn tin" (474,789). `classify_button` thấy
  2 action_nodes → unknown (dừng sai). Fix: nút **Follow quyết định** — đúng 1
  nút Follow → not_followed; không còn Follow (toàn Nhắn tin) → followed.
  Test: `test_classify_side_by_side_follow_and_message_buttons`.

## Root-cause dump-consume trong verify (bug lệch queue khi test)
- `_confirm_not_released` gọi `swipe_feed` → `_screen_size` → `adapter.dump_ui()`
  tiêu thụ 1 dump; `_dismiss()` → `dismiss_all` → các handler dump_ui() tiêu
  thụ tiếp. Trong FakeAdapter (queue cố định) → dump lệch → UID kế tiếp nhận
  dump của UID sau → false "trạng thái nút không xác định sau vuốt".
- Fix: `swipe_feed(..., xml_text=current_dump)` (dump vừa classify) + BỎ
  `_dismiss()` khỏi nhánh success confirm. Live không lộ (dump thật luôn mới).

## Bài học
- Máy khác = layout khác: LUÔN dump UI trước khi kết luận selector, mở rộng
  danh sách id thay vì giả định máy 1.
- Popup quyền hệ thống (danh bạ/notification) sau relaunch là chuẩn trên máy
  farm — dùng core `dismiss_popup` (đã handle checkbox + deny đúng thứ tự).
- Profile action button sau follow hiện " Nhắn tin" (khoảng trắng đầu) —
  normalize whitespace đã cover, không cần strip riêng.

## Config máy 2 dùng
`C:/Users/Kibe/AppData/Local/Temp/tiktok-follow-m2-follow7.yaml` (mode '1',
budget_per_session 7, order random) — copy từ m1 config, đổi budget.
