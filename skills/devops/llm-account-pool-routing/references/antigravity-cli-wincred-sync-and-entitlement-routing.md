# Antigravity CLI Wincred Sync & Entitlement Routing (2026-10-24)

## 1. Bản chất cơ chế lưu trữ Auth của agy.exe trên Windows
- Binary Go `agy.exe` (Antigravity CLI) sử dụng thư viện `github.com/danieljoos/wincred` để đọc credentials trực tiếp từ **Windows Credential Manager** với `TargetName: gemini:antigravity`.
- **Cạm bẫy:** Mặc định `agy.exe` bỏ qua hoàn toàn file `.gemini/oauth_creds.json` trong thư mục profile sandbox nếu trong Windows Credential Manager đã có sẵn mục `gemini:antigravity`.
- Nếu không đồng bộ Keyring trước khi chạy, `agy.exe` sẽ luôn lấy credential của tài khoản host (thường là tài khoản cá nhân cũ đã bị cạn quota), dẫn đến lỗi `RESOURCE_EXHAUSTED (code 429): Individual quota reached` giả mạo, dù token của profile Pro vẫn còn sống 100%.

## 2. Giải pháp kỹ thuật: Sync Profile vào Windows Credential Manager
Trước khi spawn tiến trình `agy.exe`, wrapper (`ag_cli.py`) phải gọi Windows API `CredWriteW` (thông qua `ctypes`) để nạp thông tin xác thực của profile vào `TargetName: gemini:antigravity`.

### Cấu trúc Payload Credential Blob chuẩn:
```json
{
  "token": {
    "access_token": "ya29...",
    "token_type": "Bearer",
    "refresh_token": "1//...",
    "expiry": "2026-10-24T06:00:00Z",
    "expires_in": 3599
  },
  "auth_method": "consumer",
  "id_token_email": "quyphuoc090565@gmail.com"
}
```

### Các trường struct StoredToken trong agy.exe:
- `user_tier`: Bắt buộc là `"g1-pro-tier"` cho các tài khoản Google One AI Pro (tránh bị Google server phân loại vào hạn mức Free Tier 50 req/ngày).
- `client_id`: `1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com` (Antigravity IDE OAuth Client ID).
- `token_url`: `https://oauth2.googleapis.com/token`.

## 3. Cạm bẫy cờ `--project` trong agy.exe CLI
- **Sai lầm phổ biến:** Truyền GCP Cloud Project (ví dụ: `--project aicode-consumers`) vào dòng lệnh của `agy.exe`.
- **Thực tế:** Đối với `agy.exe`, cờ `--project` là **Local Workspace Conversation Project ID** (ví dụ: `default-cli-project`, `outside-of-project`), KHÔNG phải Cloud Project.
- Truyền Cloud Project vào `--project` khiến `agy.exe` báo lỗi:
  `Failed to deserialize project file ... recovering with defaults` làm hỏng ngữ cảnh phiên.
- **Khắc phục:** Bỏ cờ `--project aicode-consumers` khỏi dòng lệnh `agy.exe`. Quản lý project thông qua file cache `default_project_id.txt` và để `loadCodeAssist` nội bộ của Google tự động gán project cloud.

## 4. Thiết quân luật Timeout cho agy.exe CLI
- `agy.exe` khi chạy chế độ Agent (`fix`) là một autonomous loop: nó dùng công cụ (`read_file`, `edit_file`, `run_command`), gọi stream LLM nhiều vòng liên tiếp (10 - 20 turns).
- Đặt timeout ngắn (25s, 60s, 90s) sẽ kill tiến trình ngay giữa chừng khi model đang stream code thành công.
- **Quy chuẩn:** Timeout tối thiểu cho `ag_cli.py fix` phải $\ge$ **180s - 240s**.
