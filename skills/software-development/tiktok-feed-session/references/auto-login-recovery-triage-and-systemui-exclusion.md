# Auto-Login Recovery Triage & SystemUI Switcher Anchor Exclusion

## 1. Triage Luồng Auto-Login Recovery Khi Thiếu Tài Khoản (`account-switcher-missing-expected`)

Khi nhận alert:
- `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found`
- hoặc `stop_reason: manual-needed:account-switcher-missing-expected: expected account not found in account switcher`

### Quy trình điều tra thực tế O(1) (CẤM suy đoán mò):
1. **Kiểm tra `log.jsonl` tại step `auto_login_recovery`**:
   - Đọc trực tiếp các bản ghi JSON có `step="feed-session-smoke/auto_login_recovery"` trong `log.jsonl` của máy:
     + **Tầng 1 (Fast Login)**: `action="start_fast_login"` -> gọi `tiktok_login_v1.py <STT> --email <expected_user>`.
       Xem kết quả `action="fast_login_failed_fallback_reconcile"` và `stdout`:
       * Kẹt sai mật khẩu / rate limit: `WRONG_TIKTOK_PASSWORD`.
       * Kẹt OTP: `[7c] Không lấy được OTP từ <email>`. TikTok không nhả OTP về hộp thư dù Gmail vẫn LIVE -> fail-closed sau ~5 phút để bảo vệ nick.
     + **Tầng 2 (Fallback Reconcile)**: `action="start_reconcile"` -> gọi `reconcile_tiktok_accounts.py`.
       BẮT BUỘC kiểm tra lệnh gọi có `--expected-username <expected_user>` hay không.
       Nếu thiếu `--expected-username` trên máy có nhiều nick gán trong workbook, runner sẽ văng lỗi ngay:
       `CONFIG_ERROR: machine N: ambiguous machine-wide reconcile; explicit expected username is required`.

2. **Giới hạn số lượng tài khoản đăng nhập trên app TikTok (7-8 Nick)**:
   - TikTok giới hạn tối đa 7-8 tài khoản đăng nhập đồng thời trên một máy.
   - Khi switcher đã hiển thị 7 nick, nút `+ Thêm tài khoản` có thể bị khuất ở đáy danh sách hoặc bị TikTok từ chối đăng nhập thêm.
   - Phải kiểm tra ảnh chụp switcher (`soft-reboot-account_switcher-before.png`) để đếm chính xác số nick hiện có.

---

## 2. Loại Trừ SystemUI Status Bar Node Khỏi Switcher Anchor Matching

### Hiện tượng:
- Runner / UploadHook dừng với lỗi: `[ACCOUNT_SWITCHER_FAILED] open_switcher failed: SWITCHER_NOT_CONFIRMED: switcher markers were not confirmed`.
- Hiện trường màn hình profile vẫn còn nguyên vẹn, không có bottom-sheet switcher nào bung ra.

### Nguyên nhân cốt lõi:
- Trên Android (đặc biệt Samsung S7 1080x1920), UiAutomator dump chứa cả các node thuộc thanh trạng thái `com.android.systemui` ở mép trên màn hình (`y=0..72`).
- Icon Wi-Fi (`com.android.systemui:id/wifi_combo`, bounds `[733,14][783,56]`, center `(758, 35)`) có `content-desc="Tín hiệu Wi-Fi đủ."`.
- Vùng header profile tiêu chuẩn tìm kiếm trong dải `[300 <= x <= 780, y <= 320]`. Tọa độ `(758, 35)` rơi trọn vào dải này.
- Khi profile chưa cuộn và không có sticky header `:id/pke`, hàm `find_switcher_anchor` với cờ `allow_generic_header=True` sẽ nhận nhầm icon Wi-Fi là switcher anchor, tap vào icon Wi-Fi thay vì gọi `adapter.prepare_switcher_anchor()` để tap display name.

### Quy tắc bất biến:
- Trong mọi thuật toán tìm kiếm switcher anchor trên profile root, BẮT BUỘC lọc bỏ triệt để các node hệ thống:
  ```python
  nodes = [
      node
      for node in _nodes(xml_text)
      if node.attributes.get("package") != "com.android.systemui"
      and not (node.resource_id and node.resource_id.startswith("com.android.systemui"))
  ]
  ```
- Đảm bảo khi profile root không có anchor ngữ nghĩa, hệ thống sẽ rơi an toàn vào `adapter.prepare_switcher_anchor()` để tap display name hoặc ratio-tap chính giữa header.
