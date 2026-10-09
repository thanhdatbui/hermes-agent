# Codex OAuth Callback Mutex & OpenCode Multi-modal Fallback

## 1. Bản chất nút thắt cổ chai TCP :1455 & Codex OAuth Callback
- **Khác biệt cốt lõi:**
  - `Antigravity OAuth`: Stateless. Script Playwright tự intercept `/callback?code=...` rồi gọi `POST /api/oauth/antigravity/exchange` với `codeVerifier` riêng. Có thể mở song song 10-20 profile đồng thời mà không đụng độ.
  - `Codex OAuth`: Stateful. OpenAI hardcode redirect URI cố định: `http://localhost:1455/auth/callback`.
- **Cơ chế Singleton của OmniRoute:**
  - OmniRoute tạm thời bind port TCP 1455 và lưu `codeVerifier` trong biến toàn cục `globalThis.__pkceCallbackStates["codex"]`.
  - Nếu nhiều worker gọi `start-callback-server` cùng lúc: server trước bị close cưỡng bức, `codeVerifier` bị đè, dẫn đến lỗi `invalid_grant` hoặc ghi đè token chéo giữa các accounts.
- **Giải pháp chuẩn:**
  - Khâu đăng nhập Hotmail / đăng ký ChatGPT trên GPM: Cho phép chạy song song đa luồng tận dụng tối đa proxy và CPU.
  - Khâu đổi token Codex OAuth: Bắt buộc bọc qua `CodexOAuth1455Lock` (dùng `msvcrt.locking` trên file lock chuyên dụng `D:\Taadaa\runtime\kibe\cron-state\codex_oauth_1455.lock`) để tuần tự hóa việc chiếm port 1455.

## 2. Chuỗi Fallback Hermes & Cấu hình OpenCode
- **Cấu hình thứ tự fallback chuẩn trong `~/.hermes/config.yaml`:**
  ```yaml
  fallback_providers:
    - model: muse-spark-1.3
      provider: custom:opencode
    - model: cx/gpt-5.6-luna-high
      provider: custom:omni
  ```
  *(Lưu ý: Không set dạng JSON string bị escape qua `hermes config set` kẻo Hermes parse thành chuỗi string thay vì list; kiểm tra bằng `hermes fallback list`).*

## 3. Kiến trúc OpenCode Bridge (:20130) & Hỗ trợ Multimodal (Vision)
- **Vấn đề:** OpenCode CLI (`muse-spark-1.3-contributor-free`) hỗ trợ Vision nhưng CLI chỉ nhận đường dẫn file qua cờ `-f <image_path>`. Hermes gửi request HTTP dạng standard OpenAI chat completions mang payload base64 (`data:image/jpeg;base64,...`) hoặc URL.
- **Giải pháp trong `D:/Taadaa/tools/opencode_bridge.py`:**
  1. Trích xuất block `image_url` từ messages.
  2. Giải mã base64 ra file ảnh tạm (`NamedTemporaryFile(suffix='.jpg')`) hoặc resolve `file:///` path.
  3. Kẹp tham số `-f <path>` khi gọi `oc_farm.py run --format json --model opencode/muse-spark-1.3-contributor-free`.
  4. Stream SSE chunks ngược về Hermes với heartbeat chunk tức thì (`HTTP 200 + role: assistant`).
  5. Xóa file tạm trong khối `finally`.
- **Cơ chế Auto-Refresh Danh mục Model Free:**
  - Bridge tích hợp cache TTL 300s (5 phút).
  - Khi hết hạn cache, tự động chạy `opencode models` để nạp các model free mới vào catalog `/v1/models` mà không cần cron riêng.
- **Watchdog Tự Hồi Sinh Bridge:**
  - `hermes_stale_watchdog.py` (chạy mỗi 2 phút) thăm dò `http://127.0.0.1:20130/health`. Nếu không phản hồi, tự động dùng `subprocess.Popen` khởi động lại `D:/Taadaa/tools/opencode_bridge.py`.
