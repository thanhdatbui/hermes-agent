# Target Selection Email Deduplication Policy (Tiktok_Reg)

## Vấn đề & Triệu chứng
- Khi `gmail_clean_v2.xlsx` có các email nguồn xuất hiện ở nhiều dòng máy khác nhau (do mapping hoặc duplicate).
- Hàm `select_pending_targets` trong `scripts/tiktok_target_eligibility.py` duyệt qua danh sách các máy để chọn candidate.
- Nếu không đánh dấu `used.add(mailbox_key(email))` ngay sau khi chọn candidate cho máy hiện tại:
  + Máy A ở batch 1 nhận `email_1`.
  + Máy B ở batch 2 (hoặc cùng batch) lại nhận tiếp `email_1`.
  + Máy B khi mở TikTok sẽ đăng nhập/vào đúng tài khoản TikTok mà Máy A vừa tạo.
  + Đến khâu merge workbook (`apply_deferred_tracking_results.py` / `deferred_tracking_writer.py`), hệ thống chặn lại với lỗi `EMAIL_FOUND_OUTSIDE_EXPECTED_ROW` để tránh ghi đè/gán 1 nick cho 2 máy, dẫn đến kết quả chỉ sync tài khoản của máy đầu tiên.

## Quy tắc bắt buộc
1. **Deduplication tức thì:**
   Trong `select_pending_targets`:
   ```python
   candidate = next(
       (row for row in grouped[stt] if mailbox_key(row["email"]) not in used),
       None,
   )
   if candidate is None:
       continue
   email = candidate["email"]
   used.add(mailbox_key(email))  # BẮT BUỘC: Đánh dấu đã dùng ngay lập tức
   ```
2. **Nguyên tắc phân bổ:**
   - 1 email chỉ được cấp cho đúng 1 máy duy nhất trong toàn bộ batch.
   - Nếu máy không còn email nào chưa dùng trong danh sách của nó -> Skip máy, tuyệt đối không lấy lại email đã được gán cho máy khác.
