# Quy định Thẩm định Review & Phân vai Sol vs Claude CLI

## 1. Nguyên tắc tối cao về quyền gọi Claude CLI
- **Claude CLI (`claude -p`)**: CHỈ ĐƯỢC PHÉP GỌI KHI USER TRỰC TIẾP RA LỆNH ĐÍCH DANH (ví dụ: *"gọi claude cli lên tư vấn..."*, *"dùng claude code check..."*).
- **CẤM TUYỆT ĐỐI**: Agent/Coordinator tự ý kích hoạt Claude CLI để review, kiểm thử hay thẩm định tự động trong các phiên làm việc thông thường.

## 2. Thẩm định viên mặc định: Sol Auditor
- Mọi tác vụ review code, kiểm tra tính đúng đắn logic, nghiệm thu test evidence, và closeout scorecard BẮT BUỘC dùng **Sol Auditor** qua script `D:/Taadaa/tools/sol_auditor.py` hoặc API port `:20129` model `chatgpt-web/gpt-5.6-sol-high`.
- Ngưỡng đạt chuẩn (Production Ready): Overall Scorecard phải đạt **>= 85 - 90 điểm** và verdict `APPROVED`.

## 3. Kiến trúc Preflight Validator chống lỗi lặp (Consensus 17/09/2026)
- Bất kỳ can thiệp nào vào cấu hình Excel (`Tik1..Tik8.xlsx`, `taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`) đều phải tuân thủ 5 Invariant Rules và được bảo vệ bởi `D:/Taadaa/tools/excel_preflight_validator.py`.
- Tích hợp chốt chặn preflight trực tiếp vào launcher đồng bộ (`hermes_taikhoan_sync_cron.py`): Nếu vi phạm Invariant -> HỦY NGAY đồng bộ runtime để bảo vệ farm.
