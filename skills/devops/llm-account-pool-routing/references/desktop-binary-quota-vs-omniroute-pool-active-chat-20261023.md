# Phân Biệt Quota Desktop Binary (agy.exe) vs Pool Hoạt Động Trên OmniRoute (:20129) (2026-10-23)

## 1. Tín Hiệu Người Dùng & Sự Cố Thực Tế
- **Tình huống:** Coordinator kiểm tra pool 28 tài khoản Google Antigravity thông qua `ag_cli.py ask` và vội vàng kết luận: *"Toàn bộ 28/28 account Google đều đã cạn sạch quota ngày (429 Individual quota reached), hệ thống kẹt cứng."*
- **Phản ứng gay gắt của Operator:** 
  > *"Xàm l hết quota sao t vẫn chat vs mày đc đang chat vs mày = model omni worker chạy pool gemini đấy"*
- **Sự thật hiện trường:** 
  Phiên chat Telegram của Operator với Coordinator đang đi qua combo `omni-worker` $\rightarrow$ trỏ trực tiếp vào combo `ag-gemini-pool-3` (28 accounts Antigravity) trên OmniRoute (`:20129`). Request hoàn tất với mã **`HTTP 200 OK`**, latency ~500ms, tiêu thụ 177k tokens cache mượt mà. Pool Gemini hoàn toàn khỏe mạnh, không hề hết quota!

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### A. Sự Khác Biệt Giữa Client Binary CLI và Router Proxy API
1. **Desktop Binary CLI (`agy.exe`):**
   - File nhị phân `C:\Users\Kibe\AppData\Local\Programs\Antigravity IDE\bin\agy.exe` là client desktop cá nhân.
   - Khi chạy `agy.exe --model "gemini-3.8-flash-high"`, client gọi trực tiếp đến API Google Cloud Code bằng OAuth token local của từng profile `D:\Taadaa\agy_profiles\acc_XX`.
   - Google áp đặt hạn ngạch "Individual Quota" khắt khe đối với client cá nhân khi gọi model High/Pro:
     ```text
     RESOURCE_EXHAUSTED (code 429): Individual quota reached. 
     Please upgrade your subscription to increase your limits. Resets in 15h16m35s.
     ```
2. **OmniRoute Proxy Engine (`:20129`):**
   - OmniRoute sử dụng OAuth token được tự động làm mới (refresh token mỗi 55 phút) và định tuyến thông minh qua model ID chuẩn nội bộ: **`gemini-3.8-flash-tiered`** (hoặc family `gemini`).
   - Khi request đi qua OmniRoute, Google phân bổ hạn ngạch doanh nghiệp/tiered hợp lệ, trả về `HTTP 200 OK` và xoay tua 28 tài khoản trơn tru.

### B. Bẫy Static Cache của Endpoint `GET /api/usage/provider-limits`
- Endpoint `GET /api/usage/provider-limits` trên OmniRoute là **bản ghi cache tĩnh trong RAM/SQLite, KHÔNG tự động live-probe Google**.
- Các tài khoản hiển thị `remainingPercentage: 100%` nhưng có `fetchedAt` từ nhiều ngày trước (chưa được sync lại) sẽ gây ảo giác rằng còn nguyên quota, hoặc ngược lại cache cũ 0% gây phán đoán nhầm rằng tài khoản đã chết.
- Muốn live-probe thực tế một kết nối, OmniRoute cung cấp endpoint on-demand:
  `GET /api/usage/[connectionId]` (tự động gọi Google API và lưu lại cache mới).

---

## 3. Quy Tắc Bất Biến Khi Chẩn Đoán Quota Pool (Invariant Rules)

1. **CẤM KẾT LUẬN CẢ POOL CHẾT KHI ROUTER ĐANG HOẠT ĐỘNG:**
   - Tuyệt đối không bao giờ được suy diễn toàn bộ pool sập hay hết quota chỉ dựa vào lỗi của một script CLI local (`ag_cli.py` / `agy.exe`).
   - BẮT BUỘC kiểm tra bảng `usage_history` gần nhất trong `storage.sqlite` hoặc gửi test request trực tiếp vào `http://127.0.0.1:20129/v1/chat/completions` để lấy bằng chứng thực tế.
2. **Ưu Tiên Gọi Qua Router Thay Vì Binary Desktop:**
   - Đối với các tác vụ worker tự động (như `dispatch_worker.py` Tier 2), ưu tiên gửi HTTP request qua cổng OmniRoute `:20129` (model `omni-worker` hoặc combo `ag-gemini-pool-3`) thay vì spawn tiến trình binary desktop `agy.exe`.
3. **Model ID Chuẩn Xác:**
   - CẤM hardcode `gemini-3.8-flash-high` khi gọi Antigravity qua script tự động. Bắt buộc dùng `gemini-3.8-flash-tiered` hoặc `gemini-3.8-flash-medium` để tránh kích hoạt bẫy chặn subscription cá nhân của Google.
