# NVIDIA NIM API Free-Tier Harvesting & GPM OAuth Playbook

## 1. Overview & Architecture

Để nuôi các AI Coding Agent (OpenCode, Claude Code, Cline, Roo Code, Hermes) mà không bị cạn hạn mức gói cơ bản ($10/tháng bay màu sau 2 ngày), phương án bào tier miễn phí qua **NVIDIA NIM API Catalog** (`build.nvidia.com`) là nguồn GPU enterprise mạnh và ổn định nhất (hạ tầng H100/B200).

- **Hạn mức cấp**: 1.000 credits/tài khoản mới (không tính tiền theo token trực tiếp mà trừ dần theo credits gọi model).
- **Endpoint tương thích OpenAI**: `https://integrate.api.nvidia.com/v1/chat/completions`
- **Key format**: `nvapi-...`
- **Model thế mạnh cho Coding**:
  - `qwen/qwen2.5-coder-32b-instruct` (Đỉnh nhất cho sinh mã và tool-calling)
  - `deepseek-ai/deepseek-r1` / `deepseek-ai/deepseek-v3`
  - `moonshotai/kimi-k3`

---

## 2. Quy trình đăng ký tự động qua GPM v3 & Hotmail

### Bước 1: Khởi động GPM Profile qua Local API
- GPM v3 Local API lắng nghe tại port `19995`.
- Khởi động profile: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`
- Lấy địa chỉ CDP động từ JSON trả về: `remote_debugging_address` (ví dụ `127.0.0.1:62719`).
- Kết nối Playwright: `p.chromium.connect_over_cdp(f"http://{remote_debugging_address}")`.

### Bước 2: Điều hướng & OAuth Microsoft (Hotmail Farm)
- Điều hướng tới `https://build.nvidia.com/explore/discover?modal=signin`.
- Điền email Hotmail có sẵn trong farm vào form đăng nhập NVIDIA.
- Hệ thống điều hướng sang `login.live.com` (Microsoft OAuth).
- Điền mật khẩu Hotmail từ nguồn tracking farm (ví dụ mật khẩu chuẩn `pybzz63684`), xác nhận đăng nhập.

### Bước 3: Hoàn tất Profile NVIDIA & Rào cản hCaptcha
- Sau OAuth thành công, Microsoft redirect về `https://login.nvgs.nvidia.com/v1/create-account` (hoặc `link-account`).
- Điền mật khẩu tài khoản NVIDIA (`input[type='password']`).
- **Rào cản thực tế (Crucial Pitfall)**:
  - NVIDIA triển khai **hCaptcha nâng cao dạng Gamified Challenge**:
    - *"Drag the letter to the place where it fits"*
    - *"Complete the pattern by dragging the correct shape into the empty cell"*
  - Click tọa độ tự động thông thường không giải được câu đố kéo thả hình học này.
  - **Phương án vận hành**:
    - *Hybrid / Manual-assist*: Mở profile GPM lên cho người dùng kéo thả captcha 1 lần trong 5 giây để kích hoạt tài khoản.
    - *Automation API*: Tích hợp solver hỗ trợ hCaptcha coordinates / task puzzle (CapSolver / 2Captcha).

---

## 3. Quy trình lấy API Key sau kích hoạt
1. Truy cập trực tiếp trang model catalog (ví dụ `https://build.nvidia.com/moonshotai/kimi-k3`).
2. Bấm nút **"Generate API Key"** (hoặc **"Get API Key"**).
3. Tại modal điều khoản *"Before You Use AI"*, bấm **"Acknowledge & Continue"**.
4. Chuỗi key `nvapi-...` hiển thị và cho phép Copy.

---

## 4. Tích hợp vào Pool Load-Balancer (9Router / Omni)
- Cấm cắm 1 key đơn lẻ trực tiếp vào agent chạy dài hạn vì 1.000 credits sẽ cạn sau vài ca làm việc nặng.
- Gom batch 10–20 key `nvapi-...` nạp vào **9Router (:20128)** hoặc **Omni (:20129)**.
- Đặt cấu hình Provider `NVIDIA NIM`, fallback tự động khi gặp mã lỗi `402 Payment Required` hoặc `429 Too Many Requests` để agent làm việc liên tục không bị gián đoạn.
