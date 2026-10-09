# Omniroute Healer Watchdog & Business Tier Pool Tuning

## 1. Bẫy Hiểu Nhầm Trạng Thái Connection (Toggle vs Broken)
- **`isActive: false` (Toggle Switch):** Chỉ là cờ bật/tắt thủ công hoặc tự động trên UI của OmniRoute để gác tài khoản ở trạng thái Standby. Token OAuth vẫn được làm mới ngầm định kỳ (`tokenExpiresAt` liên tục renew).
- **`testStatus != 'active'` (Broken):** Token thực sự chết, lỗi xác thực 401/403 không refresh được.
- **Nguyên tắc Healer Watchdog:**
  - Tuyệt đối KHÔNG gộp điều kiện `not (isActive and testStatus == 'active')` để đòi mở browser GPM OAuth lại.
  - Nếu `isActive == false` nhưng `testStatus == 'active'`: Chỉ cần `UPDATE provider_connections SET is_active=1` bằng SQL trong 1ms.
  - Chỉ mở GPM automation khi `testStatus != 'active'`.
  - Đối với tài khoản ĐÃ TỒN TẠI trên OmniRoute, van an toàn 7 ngày tuổi profile GPM (`is_profile_aged_7_days`) KHÔNG áp dụng (chỉ áp dụng khi nạp mới từ Farm).

## 2. Kỷ Luật Silent Watchdog (`no_agent: True`)
- Hermes cronjob chạy với `no_agent: True` sẽ đọc toàn bộ `sys.stdout` của script để làm nội dung gửi về Telegram.
- **Quy tắc vàng:**
  - Chuyển toàn bộ print debug/thông tin quét tiến trình sang `sys.stderr`.
  - `sys.stdout` BẮT BUỘC RỖNG HOÀN TOÀN khi hệ thống 100% bình thường hoặc không có lỗi mới cần xử lý.
  - Tuyệt đối cấm dùng thẻ raw HTML (`<b>`, `<code>`, `<i>`) gây vỡ giao diện hoặc lỗi render Telegram; dùng Markdown chuẩn (`**`, `` ` ``, `*`).

## 3. Bản Chất Nhãn "Business" trong Antigravity OAuth
- Khi OAuth Antigravity, Google API trả về `tier: "standard-tier"` / `subscriptionTier: "Antigravity (Restricted)"`.
- OmniRoute (`open-sse/services/usage/antigravity.ts`) map nhãn `STANDARD` hoặc `BUSINESS` thành `Business`.
- Đây là các tài khoản đã từng kích hoạt thực thể developer (Google Cloud Console, AI Studio, Cloud Shell), trâu hơn dàn Starter Free rất nhiều, không bị bóp trần 3-5 RPM.
- Khi cần tận dụng: Nạp vào `ag-gemini-free-pool` (chiến lược `p2c`, model `antigravity/gemini-3.8-flash-tiered`) và `ag-claude` (model `antigravity/claude-sonnet-4-6`).
