# Bài Học Thực Chiến & Hậu Kiểm Sự Cố: Cạm Bẫy Dump XML vs WinRT OCR & Nguy Cơ Xóa Tài Khoản (31/10/2026)

## 1. Bối Cảnh Sự Cố
Trong tác vụ nạp Hotmail thay thế 41 Gmail DIE trên farm Samsung Galaxy S7 (cụm Kibe), Coordinator đã mắc phải chuỗi vi phạm nghiêm trọng:
1. Bỏ qua module chuẩn `automation_core.ui_extract.extract_ui` đã được quy hoạch sẵn.
2. Tự chế script ad-hoc `D:/Taadaa/tools/batch_replace_hotmail.py`, gọi RPC `dumpWindowHierarchy` của `atx-agent` (port 7912).
3. Hardcode tọa độ pixel `[540, 1810]` để bấm vào menu "Tài khoản".
4. Dẫn dắt câu hỏi trong `browser_vision` ("Có phải popup Captcha không?") mà không chạy WinRT OCR bóc chữ, dẫn đến báo cáo ảo giác sai sự thật rằng Máy 07 dính Captcha.
5. Thực tế qua WinRT OCR bóc tách sau đó: Màn hình Máy 07 hoàn toàn không có Captcha, mà đang bị bấm nhầm vào trang **"Xóa hoặc hủy kích hoạt tài khoản"**!

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause)

### A. Tọa Độ Cứng [540, 1810] Gặp Menu Đáy Nhạy Cảm
- Trong giao diện *Cài đặt và quyền riêng tư* -> *Tài khoản* của app TikTok Android:
  - Mục *"Thông tin tài khoản"* nằm ở phía trên (`y ≈ 320`).
  - Mục nằm ở sát mép đáy màn hình (`y = 1810`) chính là: **`Hủy kích hoạt hoặc xóa tài khoản`**.
- Khi script hardcode click mù vào `[540, 1810]`, app TikTok mở thẳng vào trang hủy kích hoạt/xóa vĩnh viễn. Rất may mắn là script timeout và thoát ra Launcher, không click tiếp vào "Xóa vĩnh viễn".

### B. Dump XML Làm Đơ Samsung S7 & Nuốt Node
- Lệnh `dumpWindowHierarchy` XML làm quá tải CPU Exynos 8890 trên S7, gây nghẽn binder IPC và rớt kết nối daemon `atx-agent` (`HTTP 502 Bad Gateway`).
- Khi XML bị đơ hoặc trả về rỗng, lập trình viên/agent sinh tâm lý "lách luật", dùng tọa độ pixel phỏng đoán thay vì quay lại với OCR.

### C. Ảo Giác Vision Khi Không Có Bằng Chứng OCR
- Mở file PNG cục bộ qua `browser_navigate file://` sinh trang trống (`snapshot: empty page`).
- Khi đặt câu hỏi đóng kiểu *"Có phải captcha không?"*, model vision bị thiên kiến xác nhận, khẳng định có Captcha trong khi trên ảnh thực tế là chữ *"Xóa hoặc hủy kích hoạt?"*.

---

## 3. Quy Tắc Bắt Buộc Cưỡng Chế (Hard Rules)

1. **CẤM TUYỆT ĐỐI TỌA ĐỘ PIXEL CỨNG:**
   - Cấm mọi lệnh `click` theo tọa độ số cố định như `[540, 1810]`, `[540, 324]`, `[136, 480]` khi thao tác trong các menu cài đặt hệ thống hoặc tài khoản.
   - BẮT BUỘC định vị bằng WinRT OCR: Chụp screencap -> chạy `ocr_screen_boxes` -> lấy tọa độ tâm `( (x1+x2)//2, (y1+y2)//2 )` của đúng text cần bấm ("Thông tin tài khoản", "Email").

2. **CHỐT CHẶN AN TOÀN FAIL-SAFE TRƯỚC KHI CLICK:**
   - Trước khi click bất kỳ vị trí nào trong menu cài đặt/tài khoản, WinRT OCR BẮT BUỘC quét toàn màn hình.
   - Nếu phát hiện bất kỳ từ khóa nguy hiểm nào: `["xóa", "hủy kích hoạt", "delete", "deactivate", "vĩnh viễn"]`, script PHẢI LẬP TỨC bấm phím `Back` (hoặc `Home`) và dừng tiến trình (Fail-Closed).

3. **EVIDENCE-FIRST TRƯỚC KHI KẾT LUẬN MÀN HÌNH:**
   - Cấm kết luận màn hình dính Captcha, Challenge, lỗi nếu chưa chạy WinRT OCR bóc tách văn bản.
   - Báo cáo phải trích dẫn trực tiếp text thực tế do WinRT OCR trả về kèm tọa độ bounding box.
