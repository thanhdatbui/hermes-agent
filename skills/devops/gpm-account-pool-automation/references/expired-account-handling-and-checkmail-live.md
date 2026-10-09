# Xử lý Tài khoản Hết hạn (Expired) & Quy trình Check-Live bằng checkmail.live

## 1. Bản chất sự cố và quy tắc bắt buộc
- **CẤM TỰ Ý XÓA TÀI KHOẢN KHỎI COMBO KHI THẤY EXPIRED:**
  Khi tài khoản trên OmniRoute (:20129) báo trạng thái `expired` / `401 Token invalid or revoked`, **CẤM TUYỆT ĐỐI** tự động xóa connection khỏi combo.
  - Phải vào GPM Browser mở lại profile tương ứng để đăng nhập lại / OAuth lại lấy token mới.
  - Trước khi re-OAuth, BẮT BUỘC kiểm tra trạng thái sống chết của tài khoản qua công cụ check-live web.

## 2. Vị trí công cụ Check-live Gmail trên Web
- Công cụ check-live nằm ngay trong repo GPM:
  - `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py`
  - `D:/Taadaa/GPM auto/scripts/run_master_gmail_checklive.py`
- Cơ chế: Dùng Playwright với Chromium core GPM (`gpm_browser_chromium_core_142`) đăng nhập vào trang `https://checkmail.live/` để kiểm tra theo batch (Live / Die / Disabled).
- **Quy tắc bất di bất dịch:** Check live BẮT BUỘC dùng checkmail.live qua web, CẤM thực hiện check trên thiết bị Android S7.

## 3. Bản chất nhãn "Business" (Vàng) trên OmniRoute
- Trên dashboard OmniRoute (:20129), các tài khoản hiện badge màu vàng `Business` thực chất là các tài khoản Google cá nhân onboarding theo gói `standard-tier` (hạn ngạch Antigravity / Code Assist).
- Quy tắc UI: Chuỗi chứa `BUSINESS`, `STANDARD`, `BIZ` được map vào `variant: "warning"` (màu vàng).
- **Lưu ý kiểm tra routing:** Khi thấy tài khoản không tụt quota, không kết luận vội là tài khoản vĩnh viễn/không giới hạn; phải kiểm tra `consecutiveUseCount` và chiến lược routing (như `reset-aware`) để xác định xem tài khoản có thực sự nhận request hay đang đứng sau các target ưu tiên cao hơn.
