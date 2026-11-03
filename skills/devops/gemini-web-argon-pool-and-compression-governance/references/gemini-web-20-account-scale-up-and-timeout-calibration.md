# Invariants & Runbook: Gemini-Web 20-Account Scale-up & Timeout Calibration (2026-11-03)

## 1. Hard Invariant: Cách Ly Tuyệt Đối 2 Tài Khoản IP Direct
Trong kiến trúc OmniRoute của Taadaa Farm, 2 tài khoản Google sau đây thuộc sở hữu quản trị cá nhân và BẮT BUỘC KHÔNG ĐƯỢC PHÉP nạp vào pool xoay vòng công cộng `gemini-web`:
- `thanhdatbui19951@gmail.com`
- `jinrakal@gmail.com`

**Quy tắc tuyển chọn tài khoản mở rộng:**
- Nguồn cấp duy nhất: GPM Group 10 (`Google_Live_Ready`).
- Chỉ chọn các tài khoản có trạng thái Pro Web và đã được gán qua cổng **MobiProxy 4G** (`test.taadaa.click:51xx`).
- Kiểm tra liveness bằng Playwright CDP: xác nhận đồng thời có cả `__Secure-1PSID` và `__Secure-1PSIDTS` trước khi nạp vào CSDL `storage.sqlite`.

## 2. Giải Phẫu Sự Cố 503 "Maximum combo retry limit reached"
- Phân tích 688 cuộc gọi lịch sử trên CSDL OmniRoute cho thấy 6 lần dính lỗi 503 đều có chung một kịch bản:
  - Khi payload tóm tắt nén lớn (~30k–60k tokens) đi qua đường truyền proxy 4G, thời gian phản hồi thực tế từ Google Gemini Web dao động từ 25s đến 35s.
  - Phía Client (Hermes hoặc watchdog) trước đây cấu hình timeout mặc định 30s hoặc 45s.
  - Khi chạm 30s, Client tự ý ngắt kết nối (HTTP 499). OmniRoute ghi nhận target bị hủy/ngắt và đưa vào danh sách cooldown tạm thời (transient cooldown).
  - Cơ chế Combo Router tự động nhảy sang account thứ 2, thứ 3, thứ 4... Mỗi account tiếp tục bị ngắt ở giây thứ 30.
  - Sau 5 lần retry ($5 \times 30\text{s} \approx 150\text{s}$), trần an toàn `COMBO_LOOP_SAFETY_TIMEOUT_MS` (150.000ms) của OmniRoute bị kích hoạt và trả về lỗi 503 cho toàn pool.
- **Biện pháp dứt điểm:** Nâng trần `auxiliary.compression.timeout = 300` giây trong `config.yaml`. Với timeout 5 phút, mọi request nặng đều hoàn thành thành công trong vòng 10–25 giây mà không bị đứt gãy.

## 3. Kiến Trúc Tỉa Khôn Cơ Học Tại Client (Hermes Pre-pass)
- CẤM can thiệp chỉnh sửa file `open-sse/services/compression/lite.ts` trên OmniRoute:
  - Lệnh `npm run build:backend` trên Windows sử dụng kỹ thuật stub trang để tăng tốc, làm mất 126 trang dashboard frontend dẫn đến việc người dùng mở web bị trắng trang hoặc lỗi 404.
- Toàn bộ cơ chế tỉa khôn đã được cơ giới hóa an toàn tại `D:\Taadaa\Hermes\agent\context_compressor.py`:
  - Rút ruột cơ học các lệnh terminal cũ (thay thế 50.000 dòng log bằng 1 dòng tóm tắt ngắn exit code).
  - Nếu sau khi rút ruột mà `estimate_messages_tokens_rough(messages) < self.threshold_tokens`, hệ thống lập tức bỏ qua bước gọi LLM tóm tắt, trả về tin nhắn ngay để bảo tồn 100% Prefix Prompt Cache của Google Gemini.
