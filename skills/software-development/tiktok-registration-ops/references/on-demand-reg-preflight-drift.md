# On-Demand TikTok Registration Preflight & Source-of-Truth Drift

## 1. Thiết Kế Chuẩn Của Farm: On-Demand Reg Theo Ca (Row)
- **Không còn Cron Reg độc lập / ban đêm:** Toàn bộ batch reg dồn ban đêm đã bị gỡ bỏ để tránh spam tập trung, nghẽn tài nguyên và rực IP farm.
- **Nguyên tắc vận hành song song độc lập:** Khi tới giờ Ca nuôi (Row 1..8):
  - Máy nào **ĐÃ CÓ nick** ở Row đó: Tiếp tục chạy lướt feed / tương tác / follow / upload video bình thường.
  - Máy nào **CHƯA CÓ nick** ở Row đó: Tự động kích hoạt luồng reg bù (`ensure_row_accounts.py` gọi `Tiktok_Reg` qua `_detect_clean.py` / `_run_all_targets.py`), máy nào thiếu tự reg độc lập trên máy đó, hoàn toàn không ảnh hưởng máy khác.
- **CẤM TUYỆT ĐỐI ngụy biện / bịa nguyên tắc:** Cấm Coordinator tự suy diễn "reg tốn 5-10 phút làm kẹt ca nuôi nên fail-safe bỏ qua". Thiết kế chuẩn của hệ thống là tự động phát hiện trống và reg bù On-Demand.

## 2. Pitfall: Điểm Mù Khi Detect Máy Thiếu Tài Khoản (Source-of-Truth Drift)
### Triệu chứng:
- Watchdog báo hàng chục máy bỏ qua đăng video với lý do `Khác` (`missing_account_id` trong `upload_result.json`).
- Nhưng khi kiểm tra `ensure_row_accounts.py <Row>`, script lại báo chỉ thiếu 0-3 máy và in: `Toàn bộ máy đã đầy đủ tài khoản! Không cần reg`.

### Nguyên nhân gốc:
- `ensure_row_accounts.py` quét danh sách máy thiếu bằng cách đọc `taikhoan_run_safe.xlsx` (`SAFE_WORKBOOK`):
  - Trên các dàn máy mới khởi tạo động (như Admin M201–M280) hoặc sau các đợt populate, cột ID của `taikhoan_run_safe.xlsx` có thể bị điền sẵn username cũ, placeholder, hoặc nick gán nhầm từ slot khác.
  - Script thấy ô không rỗng (`val is not None and val != 'None'`) liền ngộ nhận máy đó đã có nick ở Row hiện tại.
- Nhưng khi sang bước Đăng Video (`multi_machine_feed_session.py`), script lại đọc từ `Tik{Row}.xlsx` (được sync chuẩn 1-chiều từ Master `taikhoan_dat_v2_updated .xlsx`):
  - Trong `taikhoan_dat_v2_updated .xlsx`, slot đó thực chất chưa từng được reg tài khoản (ví dụ Admin Row 6 chỉ có 21/80 máy có nick trong Master).
  - Cột ID trong `Tik{Row}.xlsx` bị trống (`None`) -> văng lỗi `missing_account_id` -> bị đẩy vào nhóm `Khác`.

## 3. Quy Tắc Đối Soát Khắc Phục (Dual-Audit Preflight)
1. **Kiểm tra theo Master Source of Truth:**
   - Khi quét máy thiếu cho Row N trong `ensure_row_accounts.py`, BẮT BUỘC phải đối soát với `Tik{N}.xlsx` hoặc `taikhoan_dat_v2_updated .xlsx`.
   - Một máy chỉ được coi là "đã có nick hợp lệ ở Row N" khi và chỉ khi:
     (a) Có ID hợp lệ trong `taikhoan_run_safe.xlsx` ở slot N, VÀ
     (b) Có ID hợp lệ trong `Tik{N}.xlsx` (hoặc Master `taikhoan_dat_v2_updated .xlsx` ở slot N).
2. **Kích hoạt Reg Bù Ngay Khi Thấy Lệch:**
   - Nếu `taikhoan_run_safe.xlsx` có ID nhưng `Tik{N}.xlsx` rỗng (hoặc ngược lại), coi máy đó là **THIẾU NICK Ở ROW N** và đưa vào danh sách target cần reg bù.
