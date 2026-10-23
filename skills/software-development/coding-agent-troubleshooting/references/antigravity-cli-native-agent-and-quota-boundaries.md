# Antigravity CLI Native Agent & Quota Architecture Reference

## 1. Native Agent Capabilities vs OmniRoute Proxy Trap
- **Nguyên tắc bất biến**: `ag_cli.py` được thiết kế để kích hoạt **Native Google Antigravity Agent CLI (`agy.exe`)**.
  - `agy.exe` cung cấp đầy đủ khả năng của một Coding Agent: duyệt workspace, đọc/sửa file, thực thi bash/terminal, multi-turn reasoning và quản lý diff/patch độc lập.
  - **CẤM TUYỆT ĐỐI** biến `ag_cli.py` thành wrapper gọi OmniRoute REST API (`:20129`) khi gặp lỗi quota. Việc bọc REST proxy làm mất hoàn toàn năng lực agent native của `agy.exe`.
  - Nếu `agy.exe` bị Google áp trần quota (429), `ag_cli.py` phải trả về mã lỗi quota chuẩn (`RC_QUOTA_BLOCKED` / exit code 3) để Gateway cấp trên (`dispatch_worker.py`) tự động chuyển giao luồng sang **Tier 2: Claude Haiku CLI (`claude_worker.py`)**.

## 2. Command Flags & Arguments Chuẩn Của `agy.exe`
```bash
agy.exe \
  --dangerously-skip-permissions \
  --model "gemini-3.8-flash-medium" \
  --project "aicode-consumers" \
  -p "<task_prompt>"
```
- **`--model`**: Bắt buộc dùng `gemini-3.8-flash-medium` cho Worker (Reasoning Medium). Cấm tự ý nâng lên `high`. Danh mục model hỗ trợ:
  - `gemini-3.8-flash-high`
  - `gemini-3.8-flash-medium`
  - `gemini-3.8-flash-low`
  - `claude-sonnet-4-6-thinking`
  - `claude-opus-4-6-thinking`
  - `gpt-oss-120b-medium`
- **`--project`**: Bắt buộc truyền `--project aicode-consumers`. Nếu bỏ trống, `agy.exe` mặc định dùng `default-cli-project` hoặc đọc tên folder cục bộ trong `projects.json` (vd `"taadaa"`). Server Google sẽ trả về delayed 429 `RESOURCE_EXHAUSTED` vì project ID không hợp lệ.
- **Cấu hình Sandbox Project Mapping**:
  - `D:/Taadaa/agy_profiles/<profile>/.gemini/projects.json`:
    ```json
    {
      "projects": {
        "d:\\taadaa": "aicode-consumers",
        "c:\\users\\kibe": "aicode-consumers",
        "d:\\taadaa\\benchmark_arena": "aicode-consumers"
      }
    }
    ```
  - `D:/Taadaa/agy_profiles/<profile>/.gemini/antigravity-cli/cache/default_project_id.txt`:
    ```text
    aicode-consumers
    ```

## 3. Kiến Trúc Phân Tách Quota Của Google Code Assist
Server Google quản lý 2 tầng hạn mức tách biệt:
1. **Quota API Stream / 5-Hour Rolling Window (`retrieveUserQuotaSummary`)**:
   - `gemini-weekly`: Hạn mức tuần.
   - `gemini-5h`: Hạn mức cửa sổ trượt 5 giờ.
   - Endpoint: `https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary`.
   - Headers: Bắt buộc kèm `User-Agent: antigravity/cli/...` (nếu thiếu sẽ dính HTTP 403 Forbidden).
2. **Quota Gemini CLI Agent Mode (`loadCodeAssist`)**:
   - Endpoint: `https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist`.
   - Google phân biệt `currentTier` và `paidTier`:
     - `paidTier: "g1-pro-tier"`: Tài khoản có gói trả phí Google AI Pro.
     - `currentTier: "free-tier"`: Trạng thái kích hoạt hiện tại trong IDE/CLI.
   - Nếu tài khoản chưa kích hoạt liên kết Pro cho CLI, Google vẫn tính lượt gọi của `agy.exe` theo trần Free Tier (~50 requests/ngày).
   - Khi chạm trần, Google trả về:
     ```text
     RESOURCE_EXHAUSTED (code 429): Individual quota reached. 
     Please upgrade your subscription to increase your limits. Resets in XhYm.
     ```
     (Thời điểm reset cố định là **06:36 AM** sáng ngày hôm sau).
   - **Kích hoạt Pro**: Phải mở link đăng nhập liên kết Google One:
     `https://accounts.google.com/AccountChooser?Email=<email>&continue=https://one.google.com/ai`.

## 4. Quy Tắc Sandbox Token Refresh Qua Farm Proxy
- **Vấn đề**: Google OAuth endpoint (`https://oauth2.googleapis.com/token`) sẽ cấp token bị gắn cờ / hạn chế (gây HTTP 401 trên Google Cloud Code API) nếu request `refresh_token` được gửi từ host IP trực tiếp thay vì qua Farm Proxy của tài khoản đó.
- **Giải pháp**: Script `setup_agy_profile_creds.py` BẮT BUỘC đọc mapping proxy từ `profiles_config.json` và truyền `proxies={'http': proxy_url, 'https': proxy_url}` vào `requests.post()` khi refresh access token.

## 5. Tinh Chỉnh Jitter & Pool State Recovery
- `FAILOVER_JITTER_MIN` = 0.5s, `FAILOVER_JITTER_MAX` = 1.5s (giữ dưới 2s để tránh làm Gateway điều phối cấp trên bị timeout 30s/60s).
- `max_attempts` trong pool nên giới hạn tối đa 2 profiles. Nếu 2 profiles liên tiếp đều dính 429, ngắt sớm với exit code 3 để nhả quyền cho Claude Haiku CLI thay vì quét cả 28 profiles gây treo 15 phút.
