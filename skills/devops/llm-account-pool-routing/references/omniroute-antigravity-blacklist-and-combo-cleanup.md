# Quy trình Blacklist Antigravity & Đồng bộ OmniRoute Pool

Khi loại bỏ tài khoản Antigravity (Google) khỏi OmniRoute pool:

## 1. Lưu ý quan trọng về GPM Profile & Codex
- **KHÔNG xóa profile GPM** nếu profile đó đã có Codex OAuth (OpenAI/Codex OAuth live trên profile).
- Luôn kiểm tra tình trạng OAuth khác trên profile trước khi quyết định xoá hay giữ:
  + Đối soát `~/.codex/auth.json`: giải mã JWT payload hoặc kiểm tra email xem có khớp với session Codex đang chạy không.
  + Nếu khớp: **BẮT BUỘC GIỮ NGUYÊN PROFILE GPM**, cập nhật note của profile trong GPMLogin DB thành `CODEX_SESSION_ONLY__DO_NOT_OAUTH_ANTIGRAVITY`.
- Nếu không có OAuth nào khác và chưa dùng cho Codex: Xóa profile GPM an toàn qua API GPM hoặc DB.

## 2. OmniRoute Combo Update Pitfall
- Trong OmniRoute (`storage.sqlite`), một số combo hệ thống như `ag-opus-pool` có `id` trong DB sqlite là `NULL` / `None`, mặc dù API response trả về `id: "combo-ag-opus-pool"`.
- Gọi `PUT /api/combos/combo-ag-opus-pool` sẽ trả về `404 Not Found`.
- **Cách xử lý chuẩn:**
  1. Với các combo có UUID hợp lệ: Gọi `PUT /api/combos/<uuid>` bình thường.
  2. Với `ag-opus-pool` (id is None): Cập nhật trực tiếp cột `data` trong SQLite:
     ```python
     cur.execute("SELECT data FROM combos WHERE name = 'ag-opus-pool'")
     # lọc models bỏ connectionId blacklist
     cur.execute("UPDATE combos SET data = ? WHERE name = 'ag-opus-pool'", (new_json,))
     ```
  3. Xoá connection: `DELETE /api/providers/<connection_id>`
  4. Xuất backup đồng bộ vào cả 2 vị trí:
     - `C:/Users/Kibe/.omniroute/combos_backup.json`
     - `D:/Taadaa/AI-Tools/tools/omniroute/combos_backup.json`

## 3. Blacklist chống Cron tự động re-OAuth
- Cập nhật file trạng thái pipeline: `D:/Taadaa/GPM auto/config/oauth_pipeline_status.json`:
  - Thêm email vào mảng `antigravity_blacklist`
  - Xoá khỏi `omniroute_success`
  - Thêm vào danh sách loại trừ nếu có (ví dụ `excluded_khoalee`)
- Cập nhật bộ lọc trong các pipeline/watchdog runner:
  - `run_oauth_s7_pipeline.py`
  - `post_evening_gpm_login_watchdog.py`
  - `sync_gpm_lifecycle.py`
  Đảm bảo hàm check profile/email kiểm tra `email.lower() in antigravity_blacklist` trước khi kích hoạt flow OAuth Antigravity.

## 4. Chuẩn Telemetry & Test Suite Vượt Closeout Gate (>= 85đ)
- Khi skip account do blacklist, KHÔNG CHỈ return status đơn điệu (`SKIPPED_ANTIGRAVITY_BLACKLIST`), bắt buộc phát structured metric ra `sys.stderr`:
  ```python
  log_telemetry_metric("antigravity_blacklist_skipped", {
      "mid": mid,
      "email": email,
      "reason": "main_account_protection"
  })
  ```
- Bộ unit test hồi quy:
  + BẮT BUỘC gọi trực tiếp hàm xử lý `res = process_account(acc)` cho các trường hợp dữ liệu corrupt (`None`, `[]`, `{}`, chuỗi lạ) để kiểm chứng pipeline không crash và phân biệt đúng status.
  + Dùng `capsys` assert việc phát sinh metric `[TELEMETRY_METRIC]` và xác nhận 0 network call ra ngoài (`requests.get.assert_not_called()`).
- Khi dispatch worker subagent: Chỉ giao nhiệm vụ patch code đơn lẻ, không gộp chạy test nặng (audio/speech libraries) trong subagent để tránh bẫy timeout 600s.

