# Quy Trình Xử Lý Lệnh "Fix Đi", Single-Machine Canary & Fix Popup Bảo Mật Không Nhãn

## 1. Kỷ Luật Phản Ứng Khi Nhận Lệnh "Fix Đi" Từ Người Vận Hành
- **Tín hiệu cảnh báo (`?????`):**
  Khi báo cáo farm có máy lỗi (ví dụ: 46 máy Kibe fail do verify dialog, cụm Admin fail do ATX socket) và người vận hành lệnh ngắn gọn: `"Fix đi"`, TUYỆT ĐỐI CẤM dừng lại ở mức "sửa code xong rồi báo cáo lý thuyết" (kiểu: *đã commit fix, các phiên chạy sau sẽ tự nhận diện*).
  Người vận hành cần thấy hành động can thiệp và kiểm chứng ngay lập tức trên máy thật.
- **Quy trình 5 bước bắt buộc:**
  1. **Triage O(1):** Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` đọc hiện trường, inspect log/xml của máy bị lỗi.
  2. **Soạn Patch Contract & Dispatch Worker:** Worker subagent sửa code trong context riêng, chạy pytest focused <30s.
  3. **Chạy Single-Machine Canary Test:** Kiểm chứng ngay trên máy thật đại diện (ví dụ: Máy 1) bằng lệnh:
     ```powershell
     powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row <R> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
     ```
  4. **Nghiệm thu màn hình đích (Capture-Before-Cleanup):**
     - Đợi máy chạy qua bước kẹt cũ, xác nhận máy vào đến màn hình mục tiêu (ví dụ: Trang chủ / Đề xuất).
     - Chụp screencap hiện trường máy thật qua ADB.
     - Kiểm tra OCR / UI Dump có chứa các từ khóa đích (`Trang chủ`, `Đề xuất`).
  5. **Báo cáo kèm MEDIA:** Đính kèm `MEDIA:<path_anh>` dòng riêng trong báo cáo, sau đó mới thực hiện teardown đưa máy về màn hình chính (Launcher).

---

## 2. Kỹ Thuật Xử Lý Popup Bảo Mật Không Nhãn (Quick Security Popup)
- **Hiện tượng lỗi:**
  Sau khi chuyển đổi tài khoản (Account Switcher) trên các dòng máy Samsung S7 (Android 7), TikTok xuất hiện bottom-sheet popup:
  `"Hãy cùng kiểm tra bảo mật nhanh nhé"`.
  Nút đóng `X` ở góc trên phải modal (`bounds [936,866][1056,998]`) là một `android.widget.Button` nhưng có `text=""` và `content-desc=""`.
- **Anti-pattern:**
  Bộ lọc cũ chỉ tìm kiếm nhãn có từ `"Đóng"`, dẫn đến không tìm thấy nút đóng, hệ thống phân loại nhầm thành `manual-needed:verification` và dừng phiên oan với lỗi `verify dialog not dismissed`.
- **Giải pháp chuẩn (`automation-core/src/automation_core/tiktok/benign_popup.py`):**
  Trong `detect_quick_security_popup`, nếu không có nút nhãn `"Đóng"`, kích hoạt cơ chế fallback tìm nút đóng X không nhãn:
  - Element là clickable (`attrib.clickable == "true"` hoặc Button/ImageView).
  - Bounds hợp lệ ở góc trên phải: `bounds[0] >= 800` (x1 >= 800), kích thước nút `50px <= width <= 200px` và `50px <= height <= 200px`.
  - Không có text/content-desc gây hiểu lầm.
  - Tự động tap dismiss và ghi nhận marker `"close_x_unlabeled"`.

---

## 3. Remote ADB Host Cho Cụm Máy Từ Xa (Admin Cluster)
- **Hiện tượng lỗi:**
  Cụm Admin (`192.168.110.119:5037`) khi chạy cron feed session bị dừng hàng loạt với lỗi:
  `ui_dump_error: ATX_SESSION_UNAVAILABLE` hoặc `URLError: [WinError 10061]`.
- **Nguyên nhân cốt lõi:**
  1. Môi trường cron shell có thể thiếu đường dẫn `adb` trong `PATH`, khiến `shutil.which("adb")` trả về `None`. Cần auto-fallback về `C:\Program Files (x86)\xiaowei\tools\adb.exe`.
  2. Khi tạo forward port qua Remote ADB server socket (`tcp:192.168.110.119:5037`), request HTTP gửi tới atx-agent daemon nếu mặc định tới `127.0.0.1` sẽ bị refused.
- **Giải pháp chuẩn (`automation-core/src/automation_core/adb.py` & `persistent_ui.py`):**
  - `AdbClient`: Tự động fallback tìm `C:\Program Files (x86)\xiaowei\tools\adb.exe` khi `adb_path == "adb"` nhưng không có trong PATH.
  - `persistent_ui.py`: Hàm `_resolve_host` và `_request` phân giải đúng IP từ xa từ `adb.host` hoặc `ADB_SERVER_SOCKET` (ví dụ: `192.168.110.119`) để kết nối trực tiếp đến daemon atx-agent.
