# Cạm Bẫy Follow Đè 2 Phiên Trong Cùng Một Ca (Intra-Shift Burst Follow Trap)

## 1. Bản Chất Sự Cố
- **Ngữ cảnh điều phối Ca nuôi TikTok:** Mỗi ca nuôi (Ca 1: 06:00 & 08:00, Ca 2: 12:00 & 14:00, Ca 3: 18:00 & 20:00) chia làm 2 phiên cách nhau đúng 2 tiếng.
- **Cơ chế Sync Row giữa 2 Phiên:** Để đảm bảo tính nhất quán của ca nuôi, `shift_pool_selector.py` có logic đồng bộ cứng: Phiên 1 bốc row nào thì Phiên 2 bốc lại chính xác row đó (`session=2 source=session1_sync`).
- **Xung đột chết người giữa Nhịp Feed vs Nhịp Follow:**
  - Nhịp Feed: Cần lướt feed 2 lần/ca để tăng thời lượng tương tác và duy trì nhịp hoạt động tự nhiên.
  - Nhịp Follow: Thuật toán TikTok áp dụng giới hạn burst rate cực kỳ khắt khe theo cửa sổ ngắn hạn. Khi một tài khoản vừa follow 10–15 người ở Phiên 1 (06:00), việc kích hoạt lại Follow Hook ở Phiên 2 (08:00, chỉ sau 2 tiếng) sẽ khiến TikTok kích hoạt cờ bot / spam rate-limit.
  - Hậu quả thực tế ngày 27/10/2026: 5 nick khỏe (M11, M16, M28, M31, M33) gom 11–14 follow sạch ở Phiên 1, nhưng khi bị ép chạy lại ở Phiên 2 thì bị TikTok silent-drop ngay follow đầu tiên (`FOLLOW_FAILED: TikTok không nhận follow`).

## 2. Chuỗi Phản Ứng Dây Chuyền (Cascading Penalty)
1. Runner ghi nhận `follow_failed = True` và `status = FOLLOW_FAILED`.
2. `follow_state.py` kích hoạt phạt nặng:
   - Thu hồi trạng thái tốt nghiệp (`graduated` bị chuyển thành `None` hoặc hạ trần).
   - Hạ trần hoạt động (`active_ceiling` và `proven_safe_ceiling` tụt về mức an toàn tối thiểu).
   - Ghi nhận `fail_streak += 1` và kích hoạt Cooldown phạt 48h (`cooldown_until_date = ngày_hôm_sau`).
3. Nick khỏe bị biến thành "nick bệnh" một cách oan uổng, trong khi nguyên nhân hoàn toàn do lịch trình gọi Follow quá dầy (2 giờ/lần).

## 3. Quy Tắc & Invariant Khắc Phục (Single Daily Follow Invariant)
1. **Quy Tắc Độc Tôn 1 Lần Follow / Ngày:** Mỗi tài khoản TikTok trên farm CHỈ ĐƯỢC PHÉP kích hoạt Follow Hook tối đa 1 lần trong 24 giờ.
2. **Phiên 1 Pure Feed, Phiên 2 Follow Hook:**
   - Phiên 1 (06:00, 12:00, 18:00): Tuyệt đối là Pure Feed (chỉ lướt video tăng trust, không đụng vào Follow).
   - Phiên 2 (08:00, 14:00, 20:00): Mới kích hoạt Follow Hook khi nick đã được ngâm Trust từ Phiên 1.
3. **Chốt Chặn Trong Runner (`multi_machine_feed_session.py`):**
   - Trước khi gọi `_run_follow_hook()`, bắt buộc kiểm tra:
     - Nếu `session_index == 1`: Bỏ qua follow hook với lý do `session-1-pure-feed-follow-disabled`.
     - Nếu `budget_used > 0` trong ngày hôm nay: Bỏ qua follow hook với lý do `already-followed-today-skip`.
4. **Quy Trình Cứu Hộ Oan Sai (Triage & State Salvage):**
   - Khi phát hiện nick có `followed_count >= 5` ở Phiên 1 nhưng lại dính `FOLLOW_FAILED` ở Phiên 2 trong cùng một ngày:
   - Xác định ngay đây là lỗi Burst Rate do chạy đè phiên, cấm phạt nick.
   - Chạy script hoàn trả trạng thái: xóa `follow_failed`, reset `fail_streak = 0`, khôi phục `graduated = True` và giữ nguyên `proven_safe_ceiling` đã chứng minh từ Phiên 1.
