# Case 92 (04/09/2026) — Máy 69 kẹt màn hình "Tìm Bạn bè" full-screen

Alert: `navigation target profile not found in XML`, hiện trường là trang
Tìm Bạn bè / Find Friends full-screen (title + các dòng "Sử dụng mã QR" /
"Mời bạn bè" / "Tìm bạn bè trong danh bạ" / "Tìm bạn bè trên Facebook",
có nút Back, thanh bottom-nav Hồ sơ bị che).

## Root cause: detector ưu tiên cao ăn chặn nhầm (priority inversion)

- `_detect_facebook_friends_email_permission` (priority 92) match nhầm trang
  search-subpage chỉ vì dòng row label "Tìm bạn bè trên Facebook" chứa chuỗi
  `danh sách bạn bè trên facebook`, cộng thêm điều kiện lỏng
  `or "ok" in combined` ("ok" xuất hiện như substring trong nhiều từ khác).
- Handler đúng `follow_friends_suggestion_popup` (priority 81) không bao giờ
  được gọi vì `find_matching_handler` trả về entry priority cao nhất trước.
- Dismisser sai đi tìm nút "Không cho phép" không tồn tại → fail-closed
  navigation profile.

## Fix chuẩn (áp dụng trong `tiktok-luot nuoi acc`)

1. `flows/benign_popup_registry.py::_detect_facebook_friends_email_permission`:
   yêu cầu dialog-style — chỉ match keyword khi có deny control
   (`không cho phép` / `don't allow` / `deny` / `từ chối`…) HOẶC câu hỏi
   permission explicit (`?` + `cho phép`/`allow`/`quyền truy cập`/`permission`).
   Bỏ `or "ok"` ở nhánh fallback.
2. `flows/benign_popup_registry.py::_detect_follow_friends` + core
   `flows/benign_popup.py::detect_follow_friends_suggestion_popup`: thêm marker
   `Tìm Bạn bè` / `Find Friends` / `Sử dụng mã QR` /
   `Tìm bạn bè trong danh bạ` / `Tìm bạn bè trên Facebook`, so khớp
   không dấu (NFD strip) để bắt cả OCR ASCII dạng "Tim Ban be".
3. Ma trận verify sau fix:
   - alert ASCII `Tim Ban be…` → `follow_friends_suggestion_popup`
   - alert VN có dấu → `follow_friends_suggestion_popup`
   - dialog thật `Cho phép TikTok…email…Facebook? + Không cho phép` →
     `facebook_contacts_email_permission`
4. Regression tests: `test_case92_find_friends_search_subpage_maps_to_follow_friends_handler`,
   `test_case92_facebook_permission_dialog_still_detected`
   (`test_benign_popup_registry.py` → 154 passed).

## Pitfalls tái sử dụng cho case detector mới

- KHÔNG dùng substring ngắn/generic (`"ok"`) làm điều kiện match — luôn kiểm
  tra substring đó có xuất hiện trong từ khác không.
- Detector priority cao PHẢI có gate dương (deny button / `?` / câu hỏi),
  không chỉ keyword chứa đựng; row-label của subpage full-screen rất dễ chứa
  keyword của dialog ("…trên Facebook" ≠ dialog xin quyền Facebook).
- Text Việt có 2 dạng: XML có dấu vs OCR ASCII không dấu — marker mới luôn
  viết dạng có dấu + so khớp qua NFD strip, và test cả 2 dạng.
- Khi thêm marker vào registry detector, mirror sang core detector cùng tên
  (`benign_popup.py`), vì có flow gọi core trực tiếp.
- Trước canary: kiểm tra device-lock
  (`C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`) — canary Máy 69
  đợt này bị `skipped-device-locked` vì sibling agent giữ lock, không phải
  do code.
