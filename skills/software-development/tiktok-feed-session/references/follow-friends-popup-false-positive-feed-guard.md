# Bẫy False Positive Follow Friends Popup trên Main Feed TikTok & Cách Khắc Phục (06/09/2026)

## 1. Hiện Tượng & Triệu Chứng
- **Farm Alert:**
  ```text
  failed_dismiss_overlay_before_navigation: follow_friends_popup_no_close_control
  ```
- **Hiện trường:** Màn hình TikTok Feed chính (tab "Đề xuất" hoặc "Bạn bè"), không hề có modal dialog hay card popup bạn bè nào đang che màn hình.

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Lệch so khớp chuỗi con (False Positive String Matching):**
   - Trong `python_runner/flows/benign_popup.py` (`detect_follow_friends_suggestion_popup`) và `benign_popup_registry.py` (`_detect_follow_friends`), danh sách markers quét các chuỗi như `"Bạn bè với"`, `"Mời bạn bè"`, `"Tìm bạn bè"`, `"Follow lại"`.
   - Trên TikTok hiện đại, top bar của Feed chính hiển thị song song các tab: **"Đang Follow" | "Bạn bè" (kèm badge số) | "Đề xuất"**. Ngoài ra dưới feed có thể có nút "Follow lại" hoặc caption chứa từ khóa bạn bè.
   - Detector quét toàn bộ XML/OCR text và khớp chuỗi con `"Bạn bè"`, dẫn đến kết luận sai rằng UI đang có popup gợi ý bạn bè.
2. **Kẹt vòng lặp Dismiss:**
   - Hàm `dismiss_follow_friends_suggestion_popup` tìm kiếm nút đóng ngữ nghĩa (`X`, `Đóng`, `Không quan tâm`).
   - Do đây là màn hình Feed bình thường chứ không phải modal popup, không có nút X nào tồn tại.
   - Dù có fallback nhấn phím `BACK`, màn hình vẫn là Feed có tab "Bạn bè", detector tiếp tục trả về `True`.
   - Script fail-closed và ném lỗi dừng phiên: `follow_friends_popup_no_close_control`.

---

## 3. Bản Vá Chuẩn Hóa (Feed Guard Pattern)
Trong `detect_follow_friends_suggestion_popup`:
1. **Kiểm tra dấu hiệu Feed chính (Main Feed):**
   - Các top tab đặc trưng: `"Đề xuất"`, `"Dành cho bạn"`, `"For You"`.
   - Hoặc thanh điều hướng đáy: `"Trang chủ"` / `"Home"` kết hợp với các nút tương tác video: `"Đăng lại"` (`repost`), `"Bình luận"` (`comment`), `"Chia sẻ"` (`share`).
2. **Loại trừ khi không có Modal Dialog:**
   - Nếu xác định UI đang ở Feed chính:
     + Chỉ match `True` nếu thực sự có container modal (`android.app.Dialog` hoặc class chứa `dialog`).
     + Hoặc thực sự tìm thấy close control ngữ nghĩa của popup (`_find_follow_friends_semantic_close_control(root) is not None`).
     + Nếu không có dialog hoặc close control -> **Lập tức `return False`**.

---

## 4. Cạm Bẫy Khi Chạy Canary Test Sau Sửa Lỗi
1. **Fast-Fail Device Reservation Lock:**
   - Khi máy farm gặp lỗi dừng phiên, hệ thống giữ lock blocked 1h (`C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`) để phục vụ inspect.
   - Khi chạy canary test `run-feed-session.ps1 -Machines <N>`, script sẽ báo `device lock active: path=... pid=...`.
   - **Xử lý:** Kiểm tra tiến trình PID trong lock file. Nếu PID cũ là runner đã kết thúc/chết, xóa file `.lock.json` trước khi kích hoạt lệnh canary.
2. **Môi Trường Subshell Xung Đột `PYTHONPATH`:**
   - Khi gọi PowerShell / Python từ agent subshell, `$env:PYTHONPATH` có thể kế thừa thư mục Hermes Agent, gây lỗi nạp binary C-extension như `ImportError: DLL load failed while importing _imaging`.
   - **Xử lý:** Luôn cô lập môi trường trước khi chạy runner:
     ```powershell
     powershell.exe -ExecutionPolicy Bypass -Command '$env:PYTHONPATH = ""; & "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run'
     ```
