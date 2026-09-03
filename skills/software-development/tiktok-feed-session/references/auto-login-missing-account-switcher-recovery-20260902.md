# Case 74 (02/09/2026): Tự Động Kích Hoạt Auto-Login Reconcile Khi Account Switcher Báo Thiếu Tài Khoản (`account-switcher-missing-expected`) Trong Feed Session Preflight (Sự Cố Máy 10)

## 1. Hiện tượng & Triệu chứng (Máy 10)
- **Script:** `multi-machine-feed-session` chạy preflight tài khoản chuyển sang `lyndiaschles21` trên Máy 10.
- **Lỗi dừng phiên:** `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.
- **Hiện trường:**
  - Máy 10 hiện chỉ có một số nick đã đăng nhập (< 6 nick), chưa có tài khoản `lyndiaschles21`.
  - Switcher mở lên và kiểm tra danh sách tài khoản hiện có, không thấy `lyndiaschles21`.
  - Runner trước đây lập tức fail-closed dừng phiên giữ hiện trường, làm đứt quãng kế hoạch nuôi acc của toàn ca.

## 2. Phân tích Nguyên nhân & Anti-Pattern
1. **Lỗi quy trình xử lý thiếu nick trên máy:**
   - Khi tài khoản được phân bổ vào máy nhưng chưa được đăng nhập trước đó, việc dừng phiên mà không kích hoạt nạp tài khoản tự động làm chậm tiến độ toàn farm.
2. **Anti-Pattern vận hành nghiêm trọng:**
   - Tự tiện đôn slot tài khoản khác lên chạy thay hoặc chuyển nick sang máy khác khi máy hiện tại chưa đủ 6 nick.
   - **Quy tắc bất biến:** Chỉ chuyển/swap máy khi máy đã full 6 nick. Nếu máy < 6 nick, BẮT BUỘC phải chạy login nạp nick còn thiếu vào máy.

## 3. Giải pháp Chuẩn hóa (Code Fix)
1. **Hook Phục hồi Tự động qua Login Reconcile:**
   - Trong `feed_swipe_smoke.py`, tại `verify_and_switch_profile`, khi `_is_account_switcher_missing_expected_reason(last_reason)` trả về `True` và `allow_auto_reconcile=True`:
   - Kích hoạt `_maybe_recover_missing_account_via_login(ctx, expected, ...)` gọi subprocess chạy `reconcile_tiktok_accounts.py` (`tiktok-log-in`) với các cờ:
     - `--machines <machine_id>`
     - `--allow-live-reconcile`
     - `--full-scope-takeover`
   - Tự động nạp tài khoản thiếu từ master workbook (`taikhoan_run_safe.xlsx` / `taikhoan_dat_v2_updated .xlsx`) vào máy mục tiêu.
2. **Cơ chế Chống Lặp Vô Hạn (Bounded Recursion Guard):**
   - Sử dụng set `_auto_login_recovered_accounts` để theo dõi các nick đã trigger login.
   - Khi retry `verify_and_switch_profile` sau login thành công, truyền `allow_auto_reconcile=False` để đảm bảo subprocess login chỉ được gọi tối đa 1 lần duy nhất cho mỗi tài khoản trong một phiên chạy.
   - Nếu sau login tài khoản vẫn không xuất hiện trong switcher, runner dừng phiên an toàn với `manual-needed:account-switcher-missing-expected`.
3. **Môi trường & Config Fallbacks linh hoạt:**
   - Cung cấp fallback qua biến môi trường (`TIKTOK_RECONCILE_PYTHON`, `TIKTOK_RECONCILE_SCRIPT`, `TIKTOK_SAFE_WORKBOOK`, `TIKTOK_ADB_PATH`, `TIKTOK_LOGIN_PROJECT`, `TIKTOK_DAT_WORKBOOK`, `TIKTOK_PROXY_MAPPING`) giúp linh hoạt cấu hình theo từng máy chủ farm.
