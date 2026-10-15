# User Override Push Pattern (Ngoại Lệ Cho Phép Push Khi User Trực Tiếp Ra Lệnh)

## 1. Vấn đề thực tế
Khi chạy Closeout Gate (`closeout_gate.py`), dù tests focused đã PASS 100%, Reviewer AI có thể bị kẹt điểm số (79-82) do soi xét các chi tiết ngoài scope của task. Khi User trực tiếp kiểm tra và ra lệnh "push đi" / "cho phép push", hệ thống cần có cơ chế hợp thức hóa quyền tối cao của User thay vì cứng nhắc chặn push.

## 2. Giải pháp kỹ thuật
1. `closeout_gate.py` hỗ trợ cờ:
   `--user-override` kèm `--override-note "<lý_do_user_ra_lệnh>"`
2. Điều kiện bắt buộc:
   - Focused tests BẮT BUỘC PASS 100%. Tuyệt đối không push code lỗi test.
3. Khi thỏa mãn:
   - Gate gán verdict `USER_OVERRIDE` (`passed=True`), ghi nhận audit log và cho phép `--push` (`safe_push`) thực thi.
   - Các pre-push hooks chấp nhận verdict `USER_OVERRIDE` có `details.user_override`.
