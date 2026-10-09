# Kỷ Luật Cách Ly Từng Account Khi Ghi Kết Quả Reg (Per-Account Isolation) & Cơ Chế Sync Master -> Safe (2026-09-14)

## 1. Bối cảnh sự cố
Đêm 14/09/2026, đợt reg TikTok bù lúc 00:02 (`20260914-000204`) đã reg thành công hoàn chỉnh tài khoản TikTok cho 12 máy (M1, M2, M4, M5, M13, M20, M24, M59, M66, M69, M71, M80). Tuy nhiên, khi vào ca nuôi Ca 4 lúc 01:30, toàn bộ 76 máy bị watchdog báo bỏ qua vì "Trống slot/chưa có nick".

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lỗi gom batch fail-closed (All-or-Nothing Trap):**
   - `apply_deferred_tracking_results.py` gom toàn bộ 12 file kết quả nạp vào `write_deferred_results_sequential`.
   - Máy M4 bị dính chuỗi rác `'mailto:Lapdrnjgi@Tk2'` ở cột Password từ trước trên master sheet, khiến hàm resolve slot không tìm thấy ô trống hợp lệ, sinh ra kết quả `RESULT_MISSING_ROW_OR_TIK`.
   - Cơ chế gom batch kiểm tra thấy 1 file có lỗi `BLOCKED_DATA_CONFLICT` liền chặn đứng toàn bộ flow, khiến **11 máy reg thành công còn lại cũng bị vạ lây và không được ghi vào workbook**.
   - User phản hồi gay gắt: *"Ủa ít nhất có lỗi thì lỗi acc đó thôi mắc gi acc khác k ghi vào"*.
2. **Bẫy chọn thư mục run gần nhất (`latest_run = dirs[0]`):**
   - Đợt retry lúc 01:46 thất bại 0 máy tạo ra thư mục rỗng `20260914-014603`.
   - Hàm `apply_results()` lấy `dirs[0]` bốc trúng thư mục retry rỗng này, bỏ rơi hoàn toàn 12 file kết quả của đợt chạy 00:02 trước đó.
3. **Kiến trúc đồng bộ Master -> Safe (`taikhoan_run_safe.xlsx`):**
   - Bot nuôi feed chỉ đọc file Safe (`taikhoan_run_safe.xlsx`). File này được đồng bộ từ Master (`taikhoan_dat_v2_updated .xlsx`) qua cron `taikhoan-run-safe-sync` (mỗi 5 phút).
   - Khi khâu apply vào Master bị chặn đứng, Master không đổi hash $\rightarrow$ Cron không có dữ liệu mới để bốc sang Safe $\rightarrow$ Bot nuôi vào thấy trống slot và safe-skip.

## 3. Quy chuẩn bắt buộc (Invariants)
1. **Per-Account Isolation (Cách ly tuyệt đối từng Account khi Merge):**
   - Mọi script merge kết quả (Reg, Đổi pass, Cấp nick) BẮT BUỘC duyệt qua từng file kết quả độc lập trong khối `try/except`.
   - Acc nào thành công và hợp lệ: Ghi ngay vào master workbook (`TRACKING_WORKBOOK`).
   - Acc nào dính conflict/lỗi: Bỏ qua (skip) hoặc log cảnh báo riêng cho acc đó, **CẤM TUYỆT ĐỐI để lỗi của 1 máy làm dừng hoặc hủy bỏ việc ghi của các máy khác trong mẻ**.
2. **Quét tìm Run Directory có kết quả thật:**
   - Khi tìm thư mục run để merge, CẤM TUYỆT ĐỐI chỉ lấy `dirs[0]` mù quáng. Bắt buộc duyệt qua các thư mục run gần nhất và chỉ chọn thư mục nào thực sự có file kết quả (`glob("batch_*/stt_*/tracking_result_*.json")`).
3. **Kích hoạt Sync Safe Workbook tức thì sau khi ghi Master:**
   - Ngay sau khi `wb.save(TRACKING_WORKBOOK)` hoàn tất, script BẮT BUỘC kích hoạt ngay `taikhoan_sync_cron_launcher.py` (cả trên host Kibe lẫn Admin) để đẩy dữ liệu sang `taikhoan_run_safe.xlsx` tức thời, không để ca nuôi phải chờ cron chu kỳ 5 phút.
