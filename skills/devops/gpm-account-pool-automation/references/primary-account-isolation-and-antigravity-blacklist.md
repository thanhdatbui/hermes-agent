# Cô lập tài khoản chính & Cơ chế Blacklist chống Re-OAuth Antigravity

## 1. Nguyên tắc an toàn tối thượng
- **Gmail chính chủ / cá nhân**: TUYỆT ĐỐI KHÔNG cấp quyền OAuth Antigravity qua OmniRoute (:20129) hay proxy farm.
  - OmniRoute giả lập client IDE Antigravity (`clientProfile: "ide"`, scopes `cclog`, `cloud-platform`) gửi request tần suất cao, ngữ cảnh dày qua IP proxy.
  - Nguy cơ: Google siết bản quyền, cắm cờ vi phạm điều khoản (ToS violation), thu hồi Pro hoặc khóa vĩnh viễn hệ sinh thái Google (Drive, Gmail, Mail ngân hàng).
- Chỉ sử dụng Gmail farm/phụ cho pool Antigravity xoay vòng.

## 2. Quy tắc xóa Profile GPMLogin có điều kiện
Khi rút một tài khoản khỏi pool Antigravity:
1. **Kiểm tra trạng thái Codex**:
   - Đối soát file `~/.codex/auth.json` (hoặc kiểm tra token OpenAI Codex).
   - Nếu tài khoản **ĐÃ CÓ OAUTH CODEX**: **BẮT BUỘC GIỮ NGUYÊN PROFILE GPM** để không làm đứt gãy session Codex đang chạy.
   - Cập nhật ghi chú (note) trên profile GPM: `CODEX_SESSION_ONLY__DO_NOT_OAUTH_ANTIGRAVITY`.
2. **Nếu chưa từng OAuth Codex**:
   - Có thể xóa profile an toàn bằng GPM API (`mode=2` để xóa sạch dữ liệu profile trên đĩa).

## 3. Cơ chế 3 tầng chống Watchdog / Cron tự ý Re-OAuth
Khi một tài khoản đã bị rút khỏi pool, các cronjob định kỳ (`run_oauth_s7_pipeline.py`, `post_evening_gpm_login_watchdog.py`, `sync_gpm_lifecycle.py`) có thể vô tình quét thấy trong `master_gmail_manager.xlsx` hoặc GPM DB rồi đem đi login lại. Bắt buộc triển khai khóa cứng 3 tầng:

### Tầng 1: Lưu trữ cấu hình trạng thái (`oauth_pipeline_status.json`)
- Xóa email khỏi key `omniroute_success`.
- Thêm email vào danh sách loại trừ chung: `excluded_khoalee`.
- Thêm email vào danh sách blacklist chuyên biệt:
  ```json
  "antigravity_blacklist": [
    "thanhdatbui19951@gmail.com",
    "jinrakal@gmail.com"
  ]
  ```

### Tầng 2: Bộ lọc ứng viên trong Watchdog (`post_evening_gpm_login_watchdog.py` & `sync_gpm_lifecycle.py`)
- Khi nạp các danh sách loại trừ từ status json:
  ```python
  for k in ["omniroute_success", "excluded_khoalee", "antigravity_blacklist", "wrong_password_or_checkpoint"]:
      val = sdata.get(k, {})
      if isinstance(val, dict):
          status_exclusions.update(x.lower() for x in val.keys())
      elif isinstance(val, list):
          status_exclusions.update(x.lower() for x in val)
  ```
- Tài khoản nằm trong `antigravity_blacklist` sẽ bị gạch tên ngay từ vòng quét candidate, không bao giờ được chọn để kích hoạt login.

### Tầng 3: Khóa cứng tại Pipeline thực thi (`run_oauth_s7_pipeline.py`)
- Tại đầu hàm `process_account(acc)`, ngay sau khi đọc `status_data`:
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
- Dù có trigger thủ công, pipeline sẽ từ chối tức thì, không bao giờ gửi HTTP request lấy `authUrl` hay mở trình duyệt.

## 4. Quy trình dọn dẹp OmniRoute Combo Pool & Backups
1. **Xóa connection**:
   - Gọi `DELETE http://localhost:20129/api/providers/<connection_id>`.
2. **Cập nhật Combos**:
   - Lọc bỏ model có Connection ID hoặc email bị rút khỏi tất cả combo (`ag-gemini-pool-3`, `ag-sonnet`, `ag-opus`, `ag-opus-pool`, `ag-opus-78`).
   - Gửi `PUT /api/combos/<id>` để lưu cấu hình sạch.
3. **Đồng bộ file backup**:
   - Ghi đè vào `C:/Users/Kibe/.omniroute/combos_backup.json` và `D:/Taadaa/AI-Tools/tools/omniroute/combos_backup.json`.
4. **Thẩm định focused**:
   - Chạy test kiểm tra cấu hình pool Pro:
     ```bash
     pytest D:/Taadaa/AI-Tools/tests/test_omniroute_combos.py -k "test_ag_gemini_pro_pool_structure" -v
     ```
   - Chạy test toàn vẹn Connection ID:
     ```bash
     pytest D:/Taadaa/AI-Tools/tests/test_omniroute_combos.py -k "test_all_combo_models_have_valid_connection_id" -v
     ```
