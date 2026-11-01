# Kỷ Luật WinRT OCR Primary vs XML Dump & Fail-Safe Xóa Tài Khoản (31/10/2026)

## 1. Bài Học Xương Máu Về Đọc UI Trên Phone Farm
- **Sự cố:** Coordinator dùng script ad-hoc gọi `dumpWindowHierarchy` XML của `atx-agent` (port 7912) và hardcode tọa độ `[540, 1810]` sát đáy màn hình. Khi TikTok mở trang Tài khoản, tọa độ này bấm trúng ngay dòng "Hủy kích hoạt hoặc xóa tài khoản", sau đó báo cáo sai là Captcha.
- **Quy chuẩn bắt buộc:**
  1. Cổng duy nhất: `automation_core.ui_extract.ocr_screen_boxes` / `extract_ui` (chạy WinRT OCR trên CPU máy tính trong <0.3s).
  2. Bấm đúng tâm bounds của text do WinRT OCR trả về (`hit.center`), tuyệt đối cấm tọa độ pixel cứng.
  3. Fail-Safe bất biến: Trước khi tap, nếu OCR phát hiện text chứa các từ khóa nguy hiểm (`xóa`, `hủy kích hoạt`, `xoa tai khoan`, `delete`, `deactivate`) thì lập tức bấm Back (`keyevent 4`) và dừng luồng ngay.
