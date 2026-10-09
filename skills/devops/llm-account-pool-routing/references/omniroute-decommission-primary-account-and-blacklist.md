# Runbook: Decommission & Blacklist Personal / Primary Gmail from OmniRoute Pool

## 1. Ngữ cảnh & Triệu chứng
- Khi một tài khoản Gmail cá nhân / Gmail chính (chứa tài sản quan trọng, YouTube, Drive, OTP ngân hàng) bị đưa nhầm vào pool LLM (như Antigravity OAuth qua OmniRoute).
- Nguy cơ: Google siết telemetry (`cclog`) và truy quét request IDE của bên thứ 3. Nếu tài khoản chính bị cờ vi phạm hoặc thu hồi OAuth/ban tài khoản thì thiệt hại rất lớn.
- Yêu cầu vận hành:
  1. Gỡ hoàn toàn tài khoản khỏi OmniRoute (xóa connection, gỡ khỏi mọi combo: `ag-gemini-pool-3`, `ag-sonnet`, `ag-opus`, `ag-opus-pool`, `ag-opus-78`).
  2. Xử lý Profile GPM: Nếu profile GPM tương ứng **đã có OAuth Codex** (kiểm tra `~/.codex/auth.json` hoặc token OpenAI) thì **BẮT BUỘC GIỮ LẠI PROFILE GPM**, không được xóa vì sẽ làm mất session Codex của user. Nếu chưa có Codex OAuth thì mới xóa profile GPM.
  3. Cập nhật Note profile GPM: `CODEX_SESSION_ONLY__DO_NOT_OAUTH_ANTIGRAVITY`.
  4. Cơ chế chống Cron tự động OAuth lại: Phải cài đặt blacklist vào hệ thống config và cron để các watchdog/pipeline không tự động nhặt lại tài khoản đó đem đi OAuth Antigravity.

---

## 2. Các bước xử lý chuẩn (Standard Procedure)

### Bước 1: Rà soát & Cập nhật Combos OmniRoute (:20129)
1. Lấy danh sách toàn bộ combo: `GET http://localhost:20129/api/combos`.
2. Định vị các combo chứa `connectionId` của tài khoản cần rút.
3. Lọc bỏ model chứa `connectionId` đó khỏi mảng `models` của từng combo.
4. Gửi `PUT http://localhost:20129/api/combos/<combo_id>` với payload chứa danh sách `models` đã làm sạch.
5. Đồng bộ cấu hình backup:
   - `C:/Users/Kibe/.omniroute/combos_backup.json`
   - `D:/Taadaa/AI-Tools/tools/omniroute/combos_backup.json`

### Bước 2: Xóa Connection khỏi OmniRoute
1. Gọi `DELETE http://localhost:20129/api/providers/<connection_id>`.
2. Kiểm tra lại `GET http://localhost:20129/api/providers` để đảm bảo connection đã được dọn sạch.

### Bước 3: Kiểm tra Profile GPM & Session Codex
1. Tra cứu profile trên GPM API: `GET http://127.0.0.1:19995/api/v3/profiles?per_page=300`.
2. Kiểm tra file auth của Codex: `C:/Users/Kibe/.codex/auth.json` hoặc danh sách kết nối `codex` trong OmniRoute.
3. **Quy tắc bất di bất dịch**:
   - Nếu profile GPM gắn với email đang dùng cho Codex session -> **GIỮ NGUYÊN PROFILE GPM**.
   - Cập nhật ghi chú (note) trên profile GPM (trực tiếp qua DB SQLite `profile_data.db` bảng `Profiles` trường `JsonData` hoặc API) thành:
     `CODEX_SESSION_ONLY__DO_NOT_OAUTH_ANTIGRAVITY`.
   - Chỉ xóa profile GPM (`DELETE /api/v3/profiles/delete/<id>?mode=2`) khi xác nhận 100% không có session Codex nào liên quan.

### Bước 4: Thiết lập Chặn Cứng (Anti-Reauth Blacklist) 3 Tầng
Để ngăn các cronjob nền (`post_evening_gpm_login_watchdog.py`, `run_oauth_s7_pipeline.py`, `sync_gpm_lifecycle.py`) tự ý lấy mail từ Excel quét và OAuth lại:
1. File trạng thái pipeline: `D:/Taadaa/GPM auto/config/oauth_pipeline_status.json`:
   - Xóa email khỏi `omniroute_success`.
   - Thêm email vào mảng `excluded_khoalee` (danh sách loại trừ 100%).
   - Thêm mảng `antigravity_blacklist` chứa email cần chặn vĩnh viễn:
     ```json
     "antigravity_blacklist": [
       "thanhdatbui19951@gmail.com",
       "jinrakal@gmail.com"
     ]
     ```
2. Cập nhật guard clause trong các script watchdog (Tầng 2 - Candidate Filter):
   - `post_evening_gpm_login_watchdog.py`: Bổ sung `excluded_emails.update(k.lower() for k in data.get("antigravity_blacklist", []))`.
   - `sync_gpm_lifecycle.py`: Thêm `antigravity_blacklist` vào danh sách `status_exclusions`.
3. Cập nhật guard clause trong execution pipeline (Tầng 3 - Execution Guard):
   - `run_oauth_s7_pipeline.py`:
     ```python
     ag_bl = status_data.get("antigravity_blacklist", [])
     if isinstance(ag_bl, list) and email in ag_bl:
         logger.warning(f"[M{mid:02d}] 🛡️ Bỏ qua {email}: TÀI KHOẢN NẰM TRONG ANTIGRAVITY BLACKLIST (Bảo vệ tài khoản chính)!")
         log_telemetry_metric("antigravity_blacklist_skipped", {
             "mid": mid,
             "email": email,
             "reason": "main_account_protection"
         })
         return {"mid": mid, "email": email, "status": "SKIPPED_ANTIGRAVITY_BLACKLIST"}
     ```
   - Trả về status telemetry độc lập `SKIPPED_ANTIGRAVITY_BLACKLIST` và phát metric có cấu trúc `[TELEMETRY_METRIC]`. Tuyệt đối không gọi network lấy `authUrl`.

### Bước 5: Thẩm định Focused Test (< 30s)
1. Kiểm tra cấu hình pool Pro:
   ```bash
   pytest D:/Taadaa/AI-Tools/tests/test_omniroute_combos.py -k "test_ag_gemini_pro_pool_structure" -v
   ```
2. Kiểm tra tính toàn vẹn của blacklist và regression:
   ```bash
   pytest D:/Taadaa/GPM auto/tests/test_antigravity_blacklist.py -v
   ```
