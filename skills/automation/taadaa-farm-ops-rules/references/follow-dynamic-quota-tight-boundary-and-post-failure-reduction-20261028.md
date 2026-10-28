# Khế Ước Dò Quota Trần Động Follow (Tight Boundary Probing & Post-Failure Reduction)

## 1. Bối Cảnh & Vấn Đề Lịch Sử
- **Bẫy dải ngẫu nhiên quá rộng (Wide Boundary Trap):**
  Trước đây, nhóm Khỏe cấp budget phiên theo `randint(10, cap)` (với `cap` từ 15 đến 40).
  Khi `cap = 17`, nếu hàm ngẫu nhiên bốc số `10` hoặc `11`, ca chạy lãng phí hoàn toàn cơ hội kiểm chứng ngưỡng 15–17. Ngược lại, nếu hôm trước chạy 10 hôm sau vọt lên 17 (chênh lệch +7), tài khoản rất dễ bị thuật toán TikTok kích hoạt action block / nhả follow do spike đột ngột.
- **Lỗ hổng tái phạm sau tốt nghiệp (Post-Graduation Recidivism):**
  Khi tài khoản bị nhả ở mốc trần cao (ví dụ cày 15 follow thì bị nhả, ghi nhận `last_failed_ceiling = 15`), nó trải qua 2 ca hồi phục an toàn (2–6 follow). Nhưng khi vừa tốt nghiệp lên lại nhóm Khỏe, hệ thống cũ lại ép `max(base_max, ...)` với `base_max = 15`, khiến tài khoản ngay lập tức bị cấp lại 15 follow và dính lại đúng điểm gãy cũ.

## 2. Quy Chuẩn Cơ Chế Dò Quota Trần Động Mới (Áp dụng từ 2026-10-28)
Trong `follow_runner/core/follow_state.py`:

1. **Dải Dò Bám Trần Hẹp (Tight Boundary Probing):**
   Mọi biến random cấp quota phiên cho nhóm Khỏe bắt buộc dao động trong biên độ tối đa **2 lượt**:
   ```python
   lo = max(1, cap - 2)
   budget = _random.randint(lo, cap)
   ```
   - Khi trần dò là `15`: Cấp `[13, 15]`.
   - Khi trần dò là `17`: Cấp `[15, 17]` (chắc chắn kiểm chứng được ngưỡng $\ge 15$).
   - Khi trần cựu binh là `40`: Cấp `[38, 40]`.

2. **Hạ Trần Thích Ứng Khi Tái Xuất Viện (`last_failed_ceiling - 2`):**
   Khi tài khoản có `last_failed_ceiling >= 3`:
   - Trần ca Khỏe mới bắt buộc bị bóp cứng: `safe_cap = max(1, lf - 2)`.
   - Tuyệt đối KHÔNG ép sàn `base_max = 15` khi cờ hạ trần đang kích hoạt.
   - Ví dụ: Gãy ở mốc 15 $\rightarrow$ Tốt nghiệp lên Khỏe chỉ được nhận trần tối đa `13` (dải chạy `[11, 13]`), bảo vệ tuyệt đối không chạm lại mốc 14–15.

3. **Tháo Gỡ Cờ Hạ Trần Sau Ca Khỏe Sạch:**
   Khi tài khoản hoàn thành 1 ca Khỏe sạch ở mức trần mới (`last_session_clean is True and not last_session_failed and prev_used > 0`):
   - Xóa cờ `last_failed_ceiling`.
   - Cập nhật `proven_safe_ceiling = max(curr_p, prev_used)`.
   - Cho phép tài khoản quay lại chu trình dò tăng tiến `+2` bình thường.
