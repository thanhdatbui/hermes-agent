# Phân Biệt Safe-Skip (Row X is Empty) vs Systemic Blocker Trong Batch Aggregator & Farm Alert

## 1. Bối cảnh & Hiện tượng (2026-09-17)
- **Hiện tượng:** Khi chạy batch ca đêm/chiều ở các slot cao (ví dụ: Ca 4 Row 7, Ca Row 8), hệ thống giám sát bắn cảnh báo đỏ:
  `[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG`
  với signature `script-blocker:account row 7 is empty (no username) for <device>, skipping` trên 45/80 máy (tỷ lệ lỗi 56.2% - vượt ngưỡng kép).
- **Thực tế:** Fleet có nhiều máy chỉ mới được nạp từ 1–6 account trong file Excel workbook (`taikhoan_dat_v2.xlsx`). Tại ca Row 7, các máy chưa có nick ở Slot 7 được runner skip an toàn (`feed_session_workbook.py:354`) — đây là **đúng thiết kế**, không phải lỗi.

## 2. Nguyên nhân cốt lõi (Anti-Pattern)
- Trong bộ tổng hợp batch (`automation_core.batch_aggregator` hoặc script parse kết quả):
  - Kiểm tra trạng thái máy: `succeeded = st in ("completed", "success", "ok")`.
  - Toàn bộ máy không có status trên (bao gồm cả `skipped`, `skipped-empty`, và `reason: account row X is empty`) đều bị gán `succeeded = False` và đưa vào danh sách `failed`.
  - Kết hợp với `normalize_error_signature`, 45 máy skip bị chuẩn hóa thành 1 signature lỗi hệ thống duy nhất `script-blocker:account row 7 is empty (no username) for <device>, skipping`.
  - Dẫn đến vi phạm ngưỡng kép (`min_rate >= 10%` và `min_count >= 3`), kích hoạt cảnh báo giả (False Positive Alert), khóa toàn bộ fleet và làm lu mờ các lỗi P0 thực sự.

## 3. Quy tắc phân loại chuẩn (Discipline Rule)
1. **Kỷ luật bóc tách Skip:**
   - **BẮT BUỘC** bóc tách các máy có trạng thái `skipped`, `skipped-empty` hoặc stop reason chứa:
     - `is empty (no username)`
     - `does not have valid row`
     - `batch-config-error` (ngoài expected machines)
     ra khỏi danh sách `failed` trước khi tính tỷ lệ thất bại và nhóm signature.
   - Công thức fleet failure rate chuẩn:
     `effective_fail_rate = failed_count / (total_machines - skipped_count)` (trên số máy thực sự có account để chạy).
2. **Cô lập lỗi P0 xác minh / văng tài khoản:**
   - Các máy dính lỗi auth thực sự (ví dụ: `navigation target profile not found`, `focused package unavailable`, `verification marker detected`) phải được ghi nhận vào nhóm riêng `auth_failures` để đưa vào luồng giải Captcha / xử lý app, không đánh đồng với các máy skip.
3. **Phản ứng của Coordinator khi nhận Alert `account row X is empty`:**
   - Kiểm tra ngay ca chạy hiện tại (Row mấy) và số lượng nick thực tế của các máy trong workbook.
   - Nếu là ca Row 7/Row 8 và các máy trong danh sách đều chưa có nick: Kết luận ngay **False Positive Alert** do skip hợp lệ.
   - Giữ an toàn fleet, không chạy lại toàn bộ máy rỗng, chỉ tập trung giải cứu các máy dính lỗi thực sự (P0).
