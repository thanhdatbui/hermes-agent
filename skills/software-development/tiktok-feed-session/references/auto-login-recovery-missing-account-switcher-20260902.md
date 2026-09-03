# Auto-Login Recovery Khi Account Switcher Thiếu Tài Khoản (Case 74, Máy 10, 2026-09-02)

## 1. Bối cảnh & Hiện tượng
- Khi chạy `multi-machine-feed-session` hoặc `feed_session_smoke`, runner thực hiện `verify_and_switch_profile` để kiểm tra tài khoản hiện tại trên profile và chuyển đổi tài khoản theo đúng slot ca nuôi.
- Nếu tài khoản mong đợi chưa được đăng nhập trên máy (máy đang có < 6 nick), Account Switcher bung lên không có tên tài khoản đó $\rightarrow$ báo lỗi `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.

## 2. Anti-Pattern cần tránh
- **CẤM TỰ Ý ĐÔN SLOT / SWAP MÁY**: Tuyệt đối không tự ý đôn nick có sẵn ở slot khác lên hay chuyển nick thiếu sang máy khác khi máy chưa full 6 nick.
- Chỉ thực hiện swap khi máy đã full đủ 6 nick mà dính nick thừa ở slot phụ (7/8).

## 3. Cơ chế Auto-Recovery (Case 74 trong `feed_swipe_smoke.py`)
1. **Phát hiện `account-switcher-missing-expected`**:
   - Hàm `_is_account_switcher_missing_expected_reason(last_reason)` nhận diện lỗi thiếu tài khoản trong switcher.
2. **Kích hoạt Subprocess Reconcile**:
   - Gọi `_maybe_recover_missing_account_via_login(ctx, expected_account)`:
     * Chạy `D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py` qua `D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe`.
     * Tham số: `--workbook "taikhoan_run_safe.xlsx" --machines <machine_id> --adb-path ... --allow-live-reconcile --full-scope-takeover`.
3. **Cơ chế chống lặp vô hạn (Bounded Recursion)**:
   - Sử dụng set `ctx.config["_auto_login_recovered_accounts"]` ghi nhận các tài khoản đã kích hoạt reconcile trong phiên (chỉ thử tối đa 1 lần/nick).
   - Truyền `allow_auto_reconcile=False` khi đệ quy gọi lại `verify_and_switch_profile` để ngăn chặn đệ quy sâu nếu reconcile hoàn tất nhưng nick vẫn không xuất hiện.
4. **Retry & Tiếp tục phiên nuôi**:
   - Khi reconcile thành công (exit code 0), hàm re-verify profile và switch sang nick vừa login để tiếp tục lướt feed bình thường mà không dừng phiên giữ hiện trường.
