# TikTok Deferred Tracking Sync & Chained Night Pipeline (2026-08-28)

## 1. Bắt Buộc Merge Deferred Tracking Vào Excel Ngay Sau Batch
- Khi `_run_all_targets.py` hoặc `social_reg_v1.py` chạy với cờ `--defer-tracking-write`, kết quả thành công chỉ được ghi tạm vào `tracking_result_*.json` trong thư mục artifact `social-batch-all/<batch>/stt_<XX>/`.
- **HẬU QUẢ NẾU KHÔNG MERGE:** 
  - `taikhoan_dat_v2_updated .xlsx` không có dữ liệu tài khoản vừa tạo.
  - `_detect_clean.py` quét thấy slot máy trống sẽ nhặt lại các tài khoản Hotmail/Gmail này để đem đi reg lại.
  - Khi reg lại tài khoản đã tồn tại, TikTok chuyển sang màn hình **Đăng nhập (Nhập mật khẩu)** thay vì Đăng ký mới. Script gõ pass random mới ➔ TikTok báo "Mật khẩu sai" ➔ Script fallback lấy OTP 6 số gõ nhầm vào ô mật khẩu ➔ Kẹt lỗi luẩn quẩn.
- **QUY TẮC BẮT BUỘC:**
  - Ngay khi Phase 2 (Reg TikTok) kết thúc, launcher `run_night_chain_pipeline.py` BẮT BUỘC gọi `apply_tiktok_deferred_results()` để:
    1. Chạy `scripts/apply_deferred_tracking_results.py` nạp toàn bộ `tracking_result_*.json` vào `taikhoan_dat_v2_updated .xlsx`.
    2. Gọi `sync-safe-workbook.py` đồng bộ sang `taikhoan_run_safe.xlsx` (với `TIKTOK_SAFE_EXPECTED_WRITER_ID` và `TIKTOK_FEED_WRITER_ID`).

---

## 2. Quy Tắc Báo Cáo Chuỗi Đêm (Gmail ➔ TikTok) & Pitfall Hermes Cron `no_agent`
- **Pitfall Hermes Cron `no_agent: true` (Non-Zero Exit Suppression):**
  - Scheduler của Hermes chỉ chuyển tiếp `stdout` về Telegram khi script thoát với **exit code 0**.
  - Nếu script trả về exit code khác 0 (kể cả khi batch chỉ lỗi vài máy con), Hermes sẽ hủy toàn bộ stdout, coi là cron job bị sập và kích hoạt `_summarize_cron_failure_for_delivery`. Khi output có chữ `"timed out"` (từ proxy timeout của máy con), Hermes sẽ báo nhầm: `⚠️ Cron failed: provider timeout...`.
  - **Quy tắc code:** Launcher chuỗi đêm và các script batch watchdog BẮT BUỘC thoát với `return 0` khi đã xuất xong báo cáo tổng kết; toàn bộ log tiến trình đẩy ra `stderr`, chỉ in đúng báo cáo ra `stdout`.
- **Định dạng báo cáo chuẩn (khớp form TikTok nuôi acc, không emoji):**
  1. Header: `[BÁO CÁO CHUỖI ĐÊM] Gmail -> TikTok` kèm thời gian chạy.
  2. Tách rõ `• Phase 1 (Reg Gmail - Code X):` và `• Phase 2 (Reg TikTok - Code Y):`.
  3. Cấu trúc mỗi Phase:
     - `+ Tổng máy: <N>`
     - `+ Success (<Số lượng>): <Danh sách STT máy 2 chữ số: 02, 06...>`
     - `+ Fail (<Số lượng>): <Danh sách STT máy>`
     - `- Máy XX: <lý do ngắn gọn>` (chỉ liệt kê nếu có máy fail).
