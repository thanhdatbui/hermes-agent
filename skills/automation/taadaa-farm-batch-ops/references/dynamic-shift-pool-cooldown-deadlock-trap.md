# Dynamic Shift-Pool Cooldown Deadlock Trap & Cycle Completion Invariant

## Hiện tượng thực tế (2026-11-01)
- User phát hiện: *"Ủa sao mới chạy hôm qua lại lôi hôm nay ra chạy?"*.
- Kiểm tra đối soát Kibe giữa 31/10 và 01/11 ở Ca 2 (Pool `{3, 4, 8}`): **70 / 72 máy chạy lặp lại đúng y nguyên Row của ngày hôm qua** (M1, M2 chạy Row 3 cả 2 ngày; M3, M4 chạy Row 4 cả 2 ngày).
- Toàn bộ các nick này đều bị skip follow với lý do `follow-released-daily-cooldown` (Cooldown nhả follow).

## Nguyên nhân gốc rễ (Root Cause)
1. **Quy tắc xoay tua của Shift Pool (`shift_pool_selector.py`):**
   - Hàm `resolve_shift_pool_account` loại bỏ các row đã hoàn thành chu kỳ: `candidates = [r for r in pool if r in available and r not in used]`.
   - Một row chỉ được đưa vào `used` khi hàm `mark_shift_account_cycle_completed` được kích hoạt.
2. **Chốt chặn completion quá hẹp trong Feed Session Runner (`multi_machine_feed_session.py`):**
   - Runner kiểm tra điều kiện đánh dấu hoàn thành lượt chạy trong ca:
     ```python
     is_success_run = proc.returncode == 0 and result.get("status") == "OK" and not bool(result.get("failed"))
     if shift_ca and is_success_run:
         mark_shift_account_cycle_completed(account.machine, account.account_row_index, shift_ca)
     ```
   - Khi nick đang dính cooldown follow hoặc ngày nghỉ dưỡng sinh, hệ thống chủ động bỏ qua follow (`status: "skipped"`, `reason: "follow-released-daily-cooldown"`).
   - Vì `result.get("status") == "skipped"` (khác `"OK"`), `mark_shift_account_cycle_completed` **KHÔNG BAO GIỜ ĐƯỢC GỌI**.
3. **Bẫy ưu tiên dưỡng thương đẩy vào ngõ cụt:**
   - Thuật toán `_follow_rank` xếp các nick có `fail_streak > 0` vào **Rank 4** (ưu tiên lướt feed xả phạt, làm ấm session). Các nick bình thường/chưa chạy là **Rank 5/6**.
   - Sang ngày kế tiếp, vì ngày hôm trước chưa được mark cycle completed, row dính cooldown vẫn là candidate hợp lệ.
   - Do có Rank 4 (nhỏ nhất trong candidates), máy lại tiếp tục bốc lại đúng nick đó $\to$ Lại skip follow $\to$ Lại không mark completion $\to$ **Tạo thành vòng lặp vô tận kẹt cứng tại 1 row duy nhất, các row khác trong pool bị bỏ đói**.

## Quy tắc chuẩn hóa (Standardized Rule)
- Bỏ qua follow do **Cooldown nhả follow / Dưỡng sinh tự nhiên** (`status == "skipped"` với `reason` nằm trong nhóm skip an toàn đã biết như `follow-released-daily-cooldown`, `under-6-videos-follow-disabled`) là hành vi nghiệp vụ bình thường của phiên nuôi feed, **KHÔNG PHẢI lỗi crash hay rớt hạ tầng**.
- Phiên nuôi feed đã hoàn tất trọn vẹn (lướt đủ video, post video thành công nếu có lịch) thì BẮT BUỘC phải gọi `mark_shift_account_cycle_completed` để giải phóng lượt và xoay tua sang các Row còn lại trong Pool ở các ngày tiếp theo.
