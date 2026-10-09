# Batch Aggregator Safe-Skip Integration for Farm Batch Jobs

Khi chạy các batch farm nhiều máy (VD: feed session / lướt nuôi acc 80 máy, TikTok upload, add 2FA):
1. **Hiện tượng safe-skip**:
   - Máy không có tài khoản ở hàng chỉ định (workbook slot trống: `account row X is empty (no username)`).
   - Máy bị khóa màn hình được defer an toàn (`deferred_locked` / `skipped-device-locked`).
2. **Cơ chế phân loại của `batch_aggregator.py`**:
   - `skipped_count` được tách biệt hoàn toàn khỏi `failed_count`.
   - Các trường hợp safe-skip sẽ **không** tính vào tỷ lệ lỗi và **không** kích hoạt cảnh báo lan rộng (`🚨 [BATCH ALERT: LỖI HỆ THỐNG]`).
   - Scale line báo cáo Telegram sẽ hiển thị rõ:
     `• Quy mô batch: 80 máy | Thành công: 30 | Bỏ qua: 45 | Thất bại: 5` thay vì đếm 50 máy thất bại.
