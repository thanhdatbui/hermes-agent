# Codex OAuth Singleton Port 1455 & OpenCode Farm Fallback Architecture

## 1. Bản chất Singleton Port 1455 của Codex OAuth
Khác với Antigravity OAuth (stateless web flow, callback chung `:20129/callback` cho phép chạy đa luồng song song không giới hạn), Codex OAuth có kiến trúc bắt buộc tuần tự:
- **Port 1455 hardcoded:** OpenAI gán cứng redirect URI `http://localhost:1455/auth/callback`.
- **OmniRoute Singleton State:** OmniRoute quản lý phiên qua biến toàn cục `globalThis.__pkceCallbackStates["codex"] = { port: 1455, codeVerifier, state }`.
- **Nguy cơ đè token:** Nếu 2 worker cùng gọi `start-callback-server`, worker sau sẽ giết server và xóa sạch `codeVerifier` của worker trước. Khi browser worker trước redirect về `:1455`, server dùng sai verifier dẫn đến lỗi `invalid_grant / PKCE mismatch` hoặc token ghi đè chéo tài khoản.
- **Giải pháp `CodexOAuth1455Lock`:** Sử dụng khóa file `msvcrt.locking` tại `D:\Taadaa\runtime\kibe\cron-state\codex_oauth_1455.lock`.
  - Khâu Reg ChatGPT: Chạy song song 5 luồng qua proxy riêng.
  - Khâu Codex OAuth: Bắt buộc bọc trong `with CodexOAuth1455Lock():` để tuần tự hóa việc chiếm cổng 1455 và nhận token.

## 2. Kỹ thuật vận hành OpenCode Bridge & oc_farm.py
Khi tích hợp OpenCode (đặc biệt là model `muse-spark-1.3`) làm Fallback trực tiếp cho Hermes:
- **Tránh quét ổ đĩa người dùng (`C:\Users\Kibe`):**
  OpenCode khi chạy không có cờ `--dir` sẽ mặc định inspect thư mục hiện tại. Nếu chạy trong `C:\Users\Kibe` (chứa hàng ngàn file/folder cache, venv, git), model sẽ gọi tool `read` và bị đứng treo quá timeout 120s.
  -> Bắt buộc chỉ định sandbox rỗng: `--dir C:\Users\Kibe\AppData\Local\Temp\opencode_sandbox`.
- **Mã hóa ký tự tiếng Việt trên Windows:**
  Gọi qua wrapper shell `opencode` (hoặc `opencode.cmd`) của npm thường làm hỏng mã hóa UTF-8 tiếng Việt (`"Done ch?t phin"`).
  -> Bắt buộc trỏ thẳng vào file thực thi nhị phân gốc: `C:\Users\Kibe\AppData\Roaming\npm\node_modules\opencode-ai\bin\opencode.exe`.
- **Quản lý Proxy Farm & Per-attempt Timeout:**
  Trong `oc_farm.py`, lệnh con gọi `opencode` qua proxy phải đặt `timeout=35s` cho mỗi attempt. Nếu một proxy trong pool (như DuckDNS/Khoalee) bị chết mạng, script phải ngắt ngay để chuyển sang proxy khác, tránh để dồn ứ làm chết bridge.
- **Hỗ trợ Native Vision:**
  Để model như `muse-spark-1.3` nhận diện được hình ảnh trong Hermes:
  1. Trong `config.yaml`, model phải có cờ `supports_vision: True` dưới `custom_providers.opencode.models`. Nếu thiếu, Hermes sẽ tự động nuốt ảnh và chuyển sang auxiliary text fallback.
  2. Bridge `:20130` trích xuất `data:image/...` hoặc file path và truyền qua cờ `-f <image_path>` vào OpenCode CLI.
