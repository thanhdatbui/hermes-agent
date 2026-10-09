# Pitfall: Missing Tracking Slots vs Deferred Registration Results (2026-09-27)

## Bối cảnh & Hiện tượng
Khi batch reg TikTok hoàn thành, tài khoản tạo thành công được lưu dưới dạng file JSON `tracking_result_stt<STT>_<email>.json` tại:
`D:/Taadaa/runtime/admin/artifacts/runs/social-batch-all/<run_id>/batch_1/stt_<STT>/`
để chờ bước ghi đồng bộ tuần tự vào file Excel Master (`taikhoan_dat_v2_updated .xlsx`).

### Triệu chứng lỗi
1. **Lỗi `NO_EMPTY_TRACKING_SLOT`:**
   Module `deferred_tracking_writer.py` (hàm `resolve_tracking_slot`) chỉ tìm kiếm các dòng trống sẵn của STT máy đó trong bảng.
   Khi các máy cụm 201-280 ban đầu chỉ có 4-6 hàng (đã được điền đủ tài khoản từ trước), script kiểm tra thấy không còn ô trống nào sẵn có nên lập tức trả về `BLOCKED_DATA_CONFLICT (NO_EMPTY_TRACKING_SLOT)`.
2. **Hệ quả kẹt tài khoản:**
   - Hàng loạt tài khoản đã tạo thành công bị kẹt ở file JSON (ví dụ 93 tài khoản từ ngày 24/09 đến 27/09) và không được ghi vào Excel.
   - Script lọc email nguồn `_detect_clean.py` khi đọc Excel thấy email chưa có trong file tracking nên tiếp tục chọn ra để chạy reg bù.
   - Khi chạy lại trên thiết bị thật, TikTok phát hiện email đã có tài khoản (chính là tài khoản đã tạo từ lượt trước) -> Mở màn hình OTP/Login -> Script báo lỗi `[07] Tất cả N email của STT đã có TK TikTok`.
3. **Phản hồi của User:**
   "Đéo bh có chuyện bên bán resell chắc chắn là có script chạy reg các mail đó nhưng k lưu. Hôm trc bị 1 lần r" -> User khẳng định mỗi máy phải có đủ 8 hàng (`MAX_TRACKING_ACCOUNTS_PER_MACHINE = 8`).

## Giải pháp kỹ thuật chuẩn hóa
1. **Cấp slot động khi máy chưa đủ 8 hàng (`_allocate_tracking_row`):**
   Trong `scripts/deferred_tracking_writer.py`:
   - Nếu `len(machine_rows) < 8`: Tự động cấp thêm dòng và Tik slot kế tiếp cho máy đó (`insert_at = ws.max_row + 1`).
   - Sao chép định dạng, style, borders, number_format từ hàng trước đó.
   - Tuyệt đối giữ Invariant: Không ghi đè tài khoản cũ (`existing_id` / `existing_pass`).
2. **Kịch bản phục hồi tài khoản kẹt (`scripts/recover_deferred_93_accounts.py`):**
   - Quét toàn bộ `tracking_result_*.json` trạng thái `SUCCESS` trong `runs/social-batch-all/**/`.
   - Lọc email duy nhất mới nhất và đối soát với danh sách email đã có trong `taikhoan_dat_v2_updated .xlsx`.
   - Backup file Excel trước khi ghi (`recovery-backups/`).
   - Gọi `write_deferred_results_sequential` để ghi nhận toàn bộ các tài khoản kẹt vào Excel.
