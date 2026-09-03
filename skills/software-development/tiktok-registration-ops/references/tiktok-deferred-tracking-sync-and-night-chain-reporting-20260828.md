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

## 2. Quy Tắc Báo Cáo Chuỗi Đêm (Gmail ➔ TikTok) — User Phạt Nặng 2026-08-28
- CẤM báo cáo 1 dòng tóm tắt chung chung (vd: "Code 1 | Không có summary").
- BÁO CÁO BẮT BUỘC theo chuẩn:
  1. Tách rõ **Phase 1 (Reg Gmail)** và **Phase 2 (Reg TikTok)**.
  2. Liệt kê tổng số máy, số lượng & STT máy **Thành công** (padding 2 chữ số: 02, 06...).
  3. Liệt kê số lượng & STT máy **Thất bại** kèm lý do/blocker cụ thể của từng máy.
