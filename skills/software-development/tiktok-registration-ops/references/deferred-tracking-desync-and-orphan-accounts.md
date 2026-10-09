# Deferred Tracking vs Workbook Desync (TikTok Reg)

## Bối cảnh & Nguyên nhân gốc rễ
Khi chạy batch reg hàng loạt máy qua `_run_all_targets.py`:
- Runner truyền cờ `--defer-tracking-write` cho child process `social_reg_v1.py` để tránh tranh chấp lock/hỏng file Excel tracking `taikhoan_dat_v2_updated .xlsx`.
- Mỗi máy reg thành công sẽ sinh file kết quả `tracking_result_stt<N>_<email>.json` lưu tạm dưới thư mục run batch (`artifacts/runs/social-batch-all/<timestamp>/batch_<B>/stt_<N>/`).
- **Hố sâu (Pitfall)**: `_run_all_targets.py` tự đánh dấu `workbook_write = "NOT_ATTEMPTED_BY_LOCAL_LAUNCHER"`. Sau khi kết thúc batch, nếu không có bước đồng bộ (reconcile / sync) từ các file JSON này vào `taikhoan_dat_v2_updated .xlsx`:
  1. Nick đã được tạo thật và lưu trên máy S7 (đạt trần cứng 8 nick).
  2. File Excel vẫn trống slot ID tương ứng.
  3. Khi đến ca nuôi, script đọc Excel thấy thiếu slot -> kích hoạt trigger reg bù.
  4. Script reg bù mở TikTok trên máy thật -> máy đã đủ 8 nick -> nút "Thêm tài khoản" bị ẩn -> nảy sinh lỗi `[04_add_account] Không tìm thấy: ('Thêm tài khoản')` hoặc `MACHINE_FULL_8_ACCOUNTS`.

## Dấu hiệu nhận diện
1. User thắc mắc: "Vấn đề đủ 8 tài khoản trên excel sao còn đòi reg nữa" hoặc "Này là đến ca nuôi bị thiếu acc nó ms đòi chạy reg mà".
2. Khám hiện trường XML thấy đủ 8 nick trên dropdown, nhưng Excel cột C (ID) bị trống 1-2 dòng của máy đó.
3. Kiểm tra file `tracking_result_stt<N>_*.json` trong `artifacts/runs/` có tồn tại với `status: SUCCESS` và `tiktok_id`.

## Quy tắc xử lý
- **Không vội reg bù**: Kiểm tra đối soát 3 bên: (1) UI XML máy thật, (2) File Excel `taikhoan_dat_v2_updated .xlsx`, (3) `tracking_result_*.json` tồn đọng.
- **Sync bù**: Chạy script map dữ liệu từ `tracking_result_*.json` vào slot trống của máy tương ứng trên Excel trước khi kích hoạt bất kỳ tiến trình reg hay nuôi nào.
