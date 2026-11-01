# Hotmail Replacement & Farm Idle Watchdog Invariants

### 1. KỶ LUẬT TUYỆT ĐỐI VỀ TIẾN TRÌNH NUÔI ACC (FEED SESSION PROTECTION)
- **CẤM TUYỆT ĐỐI tự ý kill/dập các tiến trình farm đang chạy (`run_tiktok.py`, `multi-machine-feed-session`)** hoặc xóa device locks để tranh chấp thiết bị cho task đổi mail.
- Khi dính ca nuôi hoặc batch job farm, **BẮT BUỘC chạy Watchdog đa luồng (`max_workers=10`) canh máy rảnh nhả lock mới nhảy vào thi công**.
- Tranh chấp lock làm crash tiến trình nuôi acc bị coi là phá hoại hệ thống farm nghiêm trọng.

### 2. KỶ LUẬT CHỐNG KHÓC LÓC & BẠI LIỆT KHI THI CÔNG HÀNG LOẠT (ANTI-PARALYSIS)
- **CẤM thói quen làm từng con nhỏ giọt rồi chat dông dài/khóc lóc/phân trần**.
- Task đổi email hàng loạt toàn farm **BẮT BUỘC phải tổ chức thành worker chạy ngầm tự động xuyên suốt, cuốn chiếu dứt điểm trước ca làm việc tiếp theo**.
- Không dừng lại sau mỗi tài khoản để chat phân trần hay xin ý kiến. Chỉ báo cáo bảng tổng kết cuối cùng khi toàn bộ danh sách đã hoàn thành hoặc có bằng chứng blocked thực tế.

### 3. QUY TRÌNH KỸ THUẬT CHUẨN THI CÔNG ĐỔI HOTMAIL TRÊN SAMSUNG S7
1. **Bộ đệm chờ App Ready (S7 Splash Screen Delay):**
   - Samsung S7 phần cứng yếu, app TikTok khởi động mất 8–12 giây màn hình splash logo TikTok màu đen.
   - BẮT BUỘC có hàm kiểm tra `wait_app_ready()` bằng WinRT OCR (chờ thấy các keyword `hö sd`, `trang ch`, `live`, `đề xuất`) trước khi tap Hồ sơ hoặc mở Switcher. Tap mù khi app chưa load xong sẽ gây lỗi false positive `khong tim thay @username trong switcher`.
2. **Thao tác bung Switcher chuẩn xác:**
   - Đảm bảo đang ở tab Hồ sơ (`tap(972, 1881)`).
   - Tap chính xác tên tài khoản ở góc trên trái `tap(200, 320)` để mở bottom sheet "Chuyển đổi tài khoản".
   - Dùng WinRT OCR tìm tọa độ dòng username cần đổi, tính tâm `(cx, cy)` và tap chuyển acc.
   - Sau khi chuyển acc, BẮT BUỘC tap lại tab Hồ sơ `tap(972, 1881)` để vào trang cá nhân mới.
3. **Điều hướng Menu -> Cài đặt -> TT tài khoản bằng OCR:**
   - Mở Menu 3 gạch `tap(1005, 150)`.
   - OCR tìm đúng dòng "Cài đặt và quyền riêng tư" (tránh tap trúng TikTok Studio hay QR code).
   - Vào Cài đặt, OCR tìm đúng mục "Tài khoản" ở nhóm dưới (Y > 1000).
   - Vào "Thông tin tài khoản" `tap(300, 326)`.
4. **Nhận diện dòng Email & Nút Thay đổi Email:**
   - Dùng WinRT OCR tìm chính xác dòng Email (chứa text `email` hoặc `@`), lấy tọa độ Y thực tế để tap vào.
   - Khi modal popup "Email của bạn: ..." xuất hiện, OCR tìm đúng nút "Thay đổi email" (Y > 1200) để tap, tuyệt đối không tap nhầm dòng "Hủy liên kết email" hoặc khu vực khác.
5. **Điền Mail Sạch & Rút OTP Graph API:**
   - Clear text cũ (gửi lặp lại keyevent 67 Delete 35 lần).
   - Nhập email Hotmail sạch có OAuth token hợp lệ, tap "Tiếp tục".
   - Rút OTP qua Microsoft Graph API (polling 6-8 attempts, 3s/lần), tự động nhập OTP.
6. **Đồng bộ SSOT kép:**
   - Ngay sau khi nghiệm thu WinRT OCR thấy text hotmail, lập tức update `tiktok_accounts` & `mailboxes` trên SQLite `farm_master.db`, đồng thời ghi đè Master Excel `taikhoan_dat_v2_updated .xlsx`.
