# Case UI-85: Quy Tắc Progressive Cooldown 3-5-7 Ngày & Cơ Chế Phục Hồi Follow

## 1. Bối cảnh & Số Liệu Thực Tế Khảo Sát Farm (25/09 - 02/10/2026)
- **Tổng số tài khoản từng bị nhả follow (dính FOLLOW_FAILED):** 191 nick trên 80 máy.
- **Tỷ lệ phục hồi khi thử lại sau cữ nghỉ ngắn 1 ngày (Streak 1 cũ):** Chỉ đạt **2/69 nick (~2.9%)**!
  - 97.1% nick khi vừa hết hạn nghỉ 1 ngày lôi ra follow lại đều bị TikTok backend tiếp tục nhả ngay lập tức.
  - 2 trường hợp phục hồi thành công (`M49_R1` và `M25_R3`) thực tế đều đã được nghỉ dưỡng sinh trọn vẹn từ **4 đến 6 ngày**.
- **Nguyên nhân cốt lõi:**
  1. Cờ rolling rate-limit / shadow-ban của TikTok kéo dài tối thiểu 3 đến 7 ngày. Nghỉ 1 ngày là chưa đủ thời gian để hệ thống giải phóng cờ đen.
  2. Dính cờ thiết bị (Device Velocity Limit): 92.4% các máy ghi nhận nhả dây chuyền >= 2 nick trên cùng thiết bị.

## 2. Quy Tắc Progressive Cooldown Backoff Mới (Triển Khai Trong follow_state.py)
- **Streak 1 (Lần đầu bị nhả):** Nghỉ **3 ngày** (`today_end_local + timedelta(days=3)` tính đến 23:59:59 local).
- **Streak 2 (2 cữ liên tiếp bị nhả):** Nghỉ **5 ngày** (`today_end_local + timedelta(days=5)`).
- **Streak >= 3 (Tái phạm nhiều lần):** Nghỉ **7 ngày** (`today_end_local + timedelta(days=7)`).
- **Grace Window:** Tương ứng mở rộng thành **7 ngày** (cho streak 1), **9 ngày** (cho streak 2), và **11 ngày** (cho streak >= 3).
- **Post-Cooldown Warmup Quota:** Sau khi mãn hạn cooldown, nick chỉ được cấp ngân sách thăm dò (probing budget) **3–5 follows**. Nếu phiên chạy hoàn thành trơn tru không lỗi -> `fail_streak` tự động reset về 0 và xóa hoàn toàn trạng thái cooldown.

## 3. Quy Chuẩn Đánh Giá Tách Bạch Trong Báo Cáo
- Không gộp file test vào ngân sách O(1) của Code Logic khi sửa chữa state machine.
- Bảo đảm 100% test suite `test_follow_state.py` (35 test) và `test_verify_follow.py` (44 test) duy trì pass 100%.
