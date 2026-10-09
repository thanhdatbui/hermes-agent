# Kiến Trúc Kiểm Soát Bất Biến Excel Farm (Excel Preflight Invariant Architecture)

## 1. Bản Chất Gốc Rễ Căn Bệnh "Làm Bằng Script Mà Cứ Lỗi Hoài"
- **Write-Without-Read & Triple-Write**: Script ghi đè Excel/State mà không đọc lại hiện trường máy thật (Switcher). Dữ liệu lệch giữa Excel, State DB và Máy thật tích tụ âm thầm qua các đợt reg dồn.
- **Excel Thiếu Schema Validation / Unique Constraints**: Excel chỉ là text tự do. Con người copy/paste hoặc kéo chuột sai 1 dòng là sinh lỗi lan truyền sang downstream mà không hệ thống nào báo lỗi.
- **Chữa cháy tạm thời thay vì fix gốc**: Thay vì tìm nick cũ và enforce bất biến, các phiên làm việc trước đè slot hoặc tạo nick mới, tích tụ nick mồ côi và làm chạm trần 8 nick.

## 2. 5 Invariant Rules Bất Biến Cho Toàn Bộ Kho Excel Farm
Mọi file cấu hình (`Tik1..Tik8.xlsx`, `taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`) bắt buộc phải thỏa mãn:
1. **Rule 1 (Slot Limit per Machine)**: Mỗi máy có tối đa 8 tài khoản (hoặc 8 dòng). Tuyệt đối không xuất hiện 1 máy 2 lần trong cùng 1 file `Tik{slot}.xlsx`.
2. **Rule 2 (No Duplicate Accounts)**: Không có tài khoản nào xuất hiện ở 2 slot khác nhau trong cùng file hoặc xuyên suốt các file `Tik1..Tik8.xlsx`.
3. **Rule 3 (Folder Video Uniqueness & Formula)**: Cột Folder Video phải là số nguyên độc bản (UNIQUE) trên toàn farm và khớp công thức chuẩn:
   $$\text{Folder Video} = (m - 1) \times 8 + \text{slot}$$
   *(Với cụm Admin: $m' = m - 200 \implies (m - 201) \times 8 + \text{slot}$)*.
4. **Rule 4 (Video Gốc Uniqueness & Formula)**: Cột Video Gốc phải độc bản trong cùng 1 file `Tik{slot}.xlsx` (không 2 máy nào trong cùng 1 ca chạy chung video gốc) và khớp công thức chuẩn:
   $$\text{Video Gốc} = (\text{slot} - 1) \times 80 + m$$
   *(Với cụm Admin: $(\text{slot} - 1) \times 80 + (m - 200)$)*.
5. **Rule 5 (taikhoan_run_safe Invariants)**: Mỗi máy tối đa 8 dòng, serial phần cứng không được rỗng, không trùng nick giữa các máy khác nhau.

## 3. Lớp Chốt Chặn Fail-Fast Gate (`excel_preflight_validator.py`)
- Script: `D:/Taadaa/tools/excel_preflight_validator.py`.
- Bộ unit test: `D:/Taadaa/tools/test_excel_preflight_validator.py` (5/5 tests PASS).
- Tích hợp trực tiếp vào **`hermes_taikhoan_sync_cron.py`** (job đồng bộ 5 phút):
  + Trước khi ghi bất kỳ dữ liệu nào sang runtime config (`hermes_cron_source_config.json`), validator chạy kiểm tra toàn bộ thư mục Excel.
  + **NẾU THẤT BẠI (FAIL)**: HỦY NGAY LẬP TỨC bước nạp runtime, văng cảnh báo `[PREFLIGHT_VALIDATOR_FAIL]` để chặn đứng dữ liệu lỗi tràn vào máy thật.

## 4. Kỷ Luật Vận Hành & Review
- **Claude CLI Policy**: Claude CLI CHỈ ĐƯỢC PHÉP GỌI khi User trực tiếp ra lệnh đích danh. CẤM tự ý gọi Claude CLI.
- **Thẩm định thường quy**: Dùng **Sol Auditor (`chatgpt-web/gpt-5.6-sol-high` qua cổng :20129)** để review và chấm điểm scorecard (yêu cầu $\ge 85$ điểm mới được merge/close).
