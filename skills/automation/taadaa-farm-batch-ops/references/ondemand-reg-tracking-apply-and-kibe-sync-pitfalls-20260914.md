# Pitfalls & Quy Chuẩn: On-Demand Reg Bù, Deferred Tracking Apply & Kibe Sync (2026-09-14)

## Bối cảnh
Khi cơ chế `ensure_row_accounts.py <row>` tự động chạy trước ca nuôi để reg bù các máy thiếu nick ở Row mục tiêu:
1. Script mua Hotmail OAuth2 (`buy_hotmail.py`) và chạy `_run_all_targets.py` thành công.
2. Các worker xuất file `tracking_result_stt<M>_<email>.json` chứa username, password, email, proof screenshot.
3. Hàm `apply_results(row)` quét thư mục kết quả để cập nhật vào master workbook `taikhoan_dat_v2_updated .xlsx` và đồng bộ sang `taikhoan_run_safe.xlsx`.

## 3 Điểm Nghẽn Cốt Lõi (Triệu chứng & Nguyên nhân)

### 1. Dữ liệu rác chặn `find_deferred_tracking_slot` (`RESULT_MISSING_ROW_OR_TIK`)
- **Triệu chứng:** Kết quả reg trả về `status: "SUCCESS"`, nhưng file JSON có `tracking_row: ""` và `tik: ""`. Khi chạy `apply_deferred_tracking_results.py` bị lỗi `BLOCKED_DATA_CONFLICT: RESULT_MISSING_ROW_OR_TIK`.
- **Nguyên nhân:** Hàm `resolve_tracking_slot` / `find_deferred_tracking_slot` chỉ coi một ô là trống khi thỏa mãn:
  `all(_cell_blank(v) for v in (id_value, pass_value, gmail_value))`.
  Nếu một dòng phôi trống trước đó bị dính dữ liệu rác (ví dụ: cột Password dính chuỗi link `mailto:Lapdrnjgi@Tk2`), hàm coi dòng đó không trống và bỏ qua, dẫn đến không tìm được slot và để rỗng `tracking_row`.
- **Khắc phục:** Định kỳ rà soát và dọn dẹp các chuỗi rác trên master tracking sheet; đảm bảo các hàng phôi trống hoàn toàn sạch ở các cột ID, Pass, Gmail.

### 2. Thiếu hook đồng bộ sang `taikhoan_run_safe.xlsx` trên host Kibe
- **Triệu chứng:** Sau khi `apply_deferred_tracking_results.py` ghi thành công tài khoản vào `taikhoan_dat_v2_updated .xlsx`, các phiên feed tiếp theo vẫn báo thiếu nick và safe-skip hàng loạt.
- **Nguyên nhân:** Trong `ensure_row_accounts.py`, nhánh host Admin có gọi `taikhoan_sync_cron_launcher.py`, nhưng nhánh fallback Kibe chỉ gọi `APPLY_SCRIPT` mà không gọi `sync-safe-workbook.py`. Do đó `taikhoan_run_safe.xlsx` không nhận được nick mới.
- **Khắc phục:** Trong `ensure_row_accounts.py`, sau khi thực thi `apply_deferred_tracking_results.py` thành công, BẮT BUỘC gọi ngay:
  `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py"`
  để đồng bộ tức thì sang `taikhoan_run_safe.xlsx`.

### 3. Bẫy bốc thư mục mồ côi rỗng do lượt retry sau (`dirs[0]`)
- **Triệu chứng:** Một đợt reg trước đó có kết quả thành công chưa kịp apply, nhưng nếu có một tiến trình retry chạy sau và kết thúc với 0 máy thành công (thư mục rỗng `tracking_result_*.json`), `latest_run = dirs[0]` sẽ trỏ vào thư mục rỗng này và bỏ quên toàn bộ file kết quả của đợt chạy trước.
- **Khắc phục:** `apply_results()` không nên chỉ quét duy nhất `dirs[0]`. Cần lặp qua các thư mục run gần nhất (trong vòng 2-4 giờ gần đây) và quét tất cả các file `tracking_result_*.json` chưa được đánh dấu đã apply.
