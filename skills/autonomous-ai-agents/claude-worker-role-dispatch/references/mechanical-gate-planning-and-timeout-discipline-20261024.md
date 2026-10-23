# Mechanical Gate Planning & Timeout Discipline (2026-10-24)

## 1. Dẹp Bỏ Tầng Prompt — Chuyển Toàn Bộ Sang Gate Cơ Học (Mechanical Layer)

### Bản chất bài học
- Lời nhắc trong system prompt hay memory chỉ là "luật mềm". Khi ngữ cảnh hội thoại dài ra, Coordinator (LLM) dễ bị trôi ngữ cảnh (prompt attenuation), nhầm lẫn vai trò, hoặc tự nhận lỗi hoang tưởng / tự ý làm tắt.
- Toàn bộ luồng điều phối BẮT BUỘC phải được code hóa thành **Script / Gateway vật lý**:
  - Không dựa vào LLM tự nhớ hay tự phán đoán.
  - Phân luồng, kiểm tra hạn mức và fallback được thực hiện tự động bằng code Python dựa trên exit code và structured status.

### Luồng Chuẩn Hóa Planner (dispatch_planner.py)
1. **Tier 1 (Primary): Claude Sonnet CLI** (`claude_worker.py --role planner`)
   - Kiểm tra quota trước bằng code (`get_claude_quota_status()`).
   - Nếu Quota 5h < 85%: Gọi Sonnet với timeout 300s.
   - Nếu Quota 5h >= 85%: Code Python tự động ngắt trong 1ms và chuyển thẳng sang Tier 2.
2. **Tier 2 (Fallback 1): Sol Planner** (`sol_planner.py` qua `:20129`)
   - Chạy trên pool 115 accounts ChatGPT-Web (100% Free, không tốn quota Anthropic).
   - Timeout: 300s.
3. **Tier 3 (Fallback 2 — Cứu sinh): Coordinator (Session Main Model)**
   - Khi cả Sonnet (chạm quota) VÀ Sol (lỗi pool / timeout) đều thất bại:
   - Script trả về exit code `100` kèm cờ `[PLANNER_FALLBACK_COORDINATOR]`.
   - Coordinator trong session chính lập tức kích hoạt quyền tự lên Plan / chốt Patch Contract O(1) để đi tiếp, cấm đóng băng task.

### Luồng Chuẩn Hóa Worker (dispatch_worker.py)
1. **Tier 1 (Ưu tiên 1 - Free): Sol Web Worker** (`sol_worker.py` qua `:20129`)
2. **Tier 2 (Fallback 1 - Native Pool): Agy CLI** (`ag_cli.py fix` qua 29 profile Pro native)
3. **Tier 3 (Fallback 2 - Anthropic): Claude Haiku CLI** (`claude_worker.py --role worker`)
4. **Tier 4 (Lối thoát cuối): Coordinator Emergency Surgery (L2)**

---

## 2. Thiết Quân Luật Về Timeout: CẤM TUYỆT ĐỐI SET NGẮN

### Nguyên nhân gây chết chùm
- Các reasoning models (Claude Sonnet 5.5, Sol Web High, Agy CLI Agent) cần 20s - 45s TTFT chỉ để suy nghĩ và 60s - 120s để sinh plan / code / inspect files.
- Việc đặt timeout 25s, 45s, 60s hay 90s là hành vi **tự bóp cổ tiến trình đang hoạt động khỏe mạnh** (ví dụ: agy.exe gửi 15 request stream liên tiếp 200 OK mượt mà nhưng bị Python kill vì chạm 90s).

### Tiêu chuẩn Timeout Cơ Học Bắt Buộc
- **Planner Timeout:** Mặc định $\ge$ **300s (5 phút)**.
- **Worker Timeout:** Mặc định $\ge$ **180s - 300s (3 - 5 phút)**.
- **Cơ chế Idle Streaming Timeout:** Chỉ ngắt kết nối khi socket hoàn toàn im lặng quá 20s không phát sinh token mới. Tuyệt đối cấm dùng trần cứng wall-clock ngắn để chém ngang stream đang nhả dữ liệu.

---

## 3. Native Antigravity CLI (agy.exe) — Windows Credential Manager Sync

### Phát hiện cơ chế xác thực
- Trên Windows, binary Go `agy.exe` sử dụng thư viện `github.com/danieljoos/wincred` để đọc credentials từ **Windows Credential Manager** với `TargetName: gemini:antigravity`.
- `agy.exe` hoàn toàn bỏ qua file JSON token trong profile sandbox (`.gemini/oauth_creds.json`) nếu `wincred` đã tồn tại credential.
- Nếu không đồng bộ `wincred`, `agy.exe` sẽ luôn lấy token của tài khoản host cũ (dễ dính 429 quota giả mạo dù token profile vẫn sống 100%).

### Giải pháp kỹ thuật chuẩn hóa
- Trong `ag_cli.py`, thêm hàm `sync_profile_to_wincred(profile_dir)` gọi Windows API `CredWriteW` để ghi credential của profile được chọn vào `gemini:antigravity` trước khi spawn `agy.exe`.
- Payload credential JSON trong `wincred`:
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
    "id_token_email": "user@gmail.com"
  }
  ```
- **Cờ `--project`:** Trong `agy.exe`, `--project` là local workspace ID (như `default-cli-project`), KHÔNG phải GCP project ID. Cấm ép `--project aicode-consumers` vào CLI command.
