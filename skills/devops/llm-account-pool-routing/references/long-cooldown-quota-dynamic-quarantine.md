# Long-Cooldown Quota Dynamic Quarantine & Sticky Proxy Binding

## 1. Nguyên Tắc Cách Ly Động Theo Thời Gian Cooldown (Dynamic Quarantine)
- **CẤM TUYỆT ĐỐI xoá tài khoản vĩnh viễn:** Khi tài khoản LLM (Codex, OpenAI, Claude, Gemini) chạm hạn mức quota nặng dẫn đến thời gian chờ hàng trăm giờ (ví dụ: `400h+ cooldown` trên OpenAI free tier):
  - Tuyệt đối KHÔNG xóa tài khoản ra khỏi bảng `provider_connections` hay loại bỏ vĩnh viễn khỏi danh sách model/target của các combo (`codex-terra`, `codex-luna`).
  - Xóa tài khoản làm mất dữ liệu OAuth và cấu hình proxy gắn kèm, biến tài khoản tạm thời hết quota thành tài khoản chết.
- **Cơ chế Dynamic Quarantine chuẩn:**
  - Lưu mốc thời gian hết hạn vào trường chuyên biệt: `codexScopeRateLimitedUntil` hoặc `rateLimitedUntil` (chuẩn ISO 8601).
  - Tầng lựa chọn tài khoản (`auth.ts` / `accountSelector.ts`):
    - Đánh giá trạng thái tại thời điểm request: $\text{unavailable} \iff \text{cooldown\_until} > \text{now}$.
    - Nếu còn trong thời gian cooldown: Gắn cờ `scopeLimited` / `rateLimited`, tự động **bỏ qua (skip)** tài khoản đó trong lượt chọn để ưu tiên các tài khoản còn quota khác trong pool.
    - **Tự động mở khóa (Auto-unquarantine):** Khi thời gian thực tế vượt qua mốc cooldown ($\text{now} \ge \text{cooldown\_until}$), hàm kiểm tra tự động trả về `available`, tài khoản tự động được đưa trở lại phục vụ request bình thường mà không cần bất kỳ can thiệp cấu hình thủ công nào.

## 2. Invariant Gắn Kết Proxy Vật Lý Theo Thiết Bị (Physical Device Sticky Proxy)
- **Không suy diễn map bừa:** Khi một cổng proxy gánh nhiều tài khoản (ví dụ cổng `5113` có cả Google, Hotmail, GPM Web):
  - BẮT BUỘC đối soát trước với bảng phân bổ vật lý của dàn thiết bị thật (`PROXYgandienthoai.xlsx` và `master_gmail_manager.xlsx` / `taikhoan_dat_v2_updated .xlsx`).
  - Nếu tài khoản Google / Hotmail được tạo lập hoặc đăng ký dịch vụ (TikTok reg) trên máy vật lý cụ thể (ví dụ Máy 49 / Máy 11), proxy của tài khoản đó BẮT BUỘC phải giữ nguyên theo cổng proxy của máy đó để chống checkpoint / lệch ASN.
  - CẤM tự ý re-balance chuyển proxy của tài khoản gắn với thiết bị sang dải IP khác khi chưa đối soát nguồn gốc device.
