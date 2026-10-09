# Account Switcher Placeholder Alias & Stale Post Receipt Triage

## Bối cảnh & Hiện tượng (Case Máy 3, 2026-09-20/21)
- Khi thực thi quy trình đăng video TikTok (Tik6), runner ném lỗi:
  `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found`.
- Đồng thời khi retry canary sau đó lại gặp lỗi:
  `[POST_SUBMISSION_UNKNOWN] post_submission_state=UNKNOWN: không có bằng chứng TikTok ACCEPTED submission; không được ghi workbook hay báo success (COMPAT-POST-VERIFY-004)` và bị loop tại `VERIFY_POST`.

---

## 1. Cơ chế TikTok Account Switcher Placeholder Alias
1. **Bản chất**:
   - Khi tài khoản TikTok mới được đăng nhập hoặc chưa đồng bộ kịp hiển thị username, TikTok hiển thị nhãn tạm (placeholder alias) dạng `user<digits>` (ví dụ: `user9274263485158`) trên danh sách Account Switcher thay vì username thật (ví dụ: `verasdhkn0r`).
   - Hàm `select_exact_account` trong `automation_core.tiktok.account_switcher` tìm exact match string hoặc prefix theo username thật nên không nhận diện được placeholder node, dẫn đến exception `ACCOUNT_MISSING`.
2. **Kỹ thuật điều tra O(1) không xâm lấn**:
   - Dùng script đối soát inventory có sẵn:
     ```bash
     python "D:/Taadaa/tiktok-log-in/scripts/compare_tiktok_accounts.py" \
       --workbook "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" \
       --machines <M> \
       --adb-path "C:/Users/Kibe/.GemPhoneFarm/app/adb-tool/adb.exe" \
       --allow-live-device-read
     ```
   - Script sẽ đọc switcher trên máy thật, bốc các nhãn `user<digits>`, tap vào từng nhãn để mở Profile đọc username thật và ghi ánh xạ vào sheet `user_alias` trong file kết quả `tiktok-account-comparison-*.xlsx`.
   - Đối chiếu sheet `user_alias` để xác định chính xác placeholder `user...` nào thực sự là nick cần tìm.

---

## 2. Xử lý Stale Post Receipt & Fingerprint Reservation
1. **Triệu chứng**:
   - Chạy retry upload nhưng runner không thực hiện push video mà chuyển thẳng sang `VERIFY_POST` rồi văng `POST_SUBMISSION_UNKNOWN` và giữ `MANUAL_REVIEW`.
2. **Nguyên nhân**:
   - Tồn tại file receipt cũ trong `D:/CodexRuntime/tiktok-video/idempotency/post-attempts/machine_<M>_account_<target>_video_<N>.json` với trạng thái `status: intent_pending` hoặc `post_submission_state: UNKNOWN` từ một run crash trước đó (chưa hoàn tất `post_tapped_at` / `ACCEPTED`).
   - Runner upload có cơ chế chống post trùng (`_route_existing_post_receipt_to_verification`), phát hiện receipt dở dang sẽ chặn `MEDIA_PUSH` và ép verify post trước.
3. **Cách khắc phục an toàn**:
   - Di dời/lưu trữ file receipt cũ và file reservation fingerprint dở dang:
     ```bash
     mv "D:/CodexRuntime/tiktok-video/idempotency/post-attempts/machine_<M>_account_<target>_video_<N>.json" "...\*.json.bak-<timestamp>"
     mv "D:/CodexRuntime/tiktok-video/idempotency/media-fingerprints/<key>.json" "...\*.json.bak-<timestamp>"
     ```
   - Dọn sạch các file media tạm trên thiết bị:
     ```bash
     adb -s <serial> shell rm -f /sdcard/DCIM/Camera/codex_* /sdcard/_ss*.png
     ```
   - Sau khi dọn sạch, runner sẽ bắt đầu từ đầu: `MEDIA_PUSH` $\rightarrow$ `VIDEO_PICK` $\rightarrow$ `CAPTION_FILL` $\rightarrow$ `POST` $\rightarrow$ `VERIFY_POST`.

---

## 3. Lệch cột Cột 10 & 11 trong Master DAT
1. **Triệu chứng**:
   - `compare_tiktok_accounts.py --plan-only` báo lỗi:
     `CONFIG_ERROR: machine <M> has conflicting serials in workbook`.
2. **Nguyên nhân**:
   - Dòng tài khoản bị dán ngày (vd: `23/08/2026`) vào Cột 10 (`device ID`), đẩy serial thật sang Cột 11 không header.
3. **Khắc phục**:
   - Quét regex các dòng có serial tại Cột 11, đưa serial về Cột 10 và set `cell(r, 11).value = None`.
   - Chạy `compare_tiktok_accounts.py --workbook "..." --machines 1-80 --plan-only` xác nhận 80/80 máy đạt `PLAN_OK`.
   - Đồng bộ sang safe sheet bằng `sync-safe-workbook.py` và `hermes_taikhoan_sync_cron.py`.
