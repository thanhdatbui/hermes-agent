# RCA & Quy chuẩn: Bẫy Giữ Nghẽn Báo Cáo Feed Watchdog Khi Chạy Xong Sớm (20/10/2026)

## 1. Hiện tượng & Triệu chứng
- Người dùng nhận 2 bản tin báo cáo hoàn tất nuôi TikTok của 2 phiên liên tiếp cách nhau đúng 5 phút (ví dụ: 09:30 nhận report Ca 1 - Phiên 1/2, đến 09:35 nhận report Ca 1 - Phiên 2/2).
- Thực tế trên farm:
  - Cụm Kibe (Máy 1-80) hoàn tất Phiên 1 lúc 08:03.
  - Cụm Admin (Máy 201-280) hoàn tất Phiên 1 lúc 07:51 (chạy nhanh hơn khung giờ kết thúc 08:00).
  - Phiên 2 khởi chạy lúc 08:00:10 trên cả 2 cụm.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Kiểm tra cứng thời gian kết thúc trong `_is_session_manifest_completed`:**
   - Trong lúc Phiên 2 đang chạy (08:00 – 09:26), biến toàn cục `is_feed_runner_active()` luôn là `True`.
   - Để giải phóng báo cáo của phiên cũ, watchdog gọi `is_cluster_session_busy(..., win_end_hm)` -> `_is_session_manifest_completed(...)`.
   - Hàm này kiểm tra cứng: `if end_hm >= win_end_hm: return True`.
   - Do Cụm Admin xong lúc 07:51 (`07:51 >= 08:00` là `False`), watchdog đánh giá Cụm Admin vẫn "chưa xong" Phiên 1 và trả về `busy = True`.
   - Vì thế, toàn bộ báo cáo Phiên 1 bị giữ nghẽn (hold) trong suốt thời gian Phiên 2 đang chạy.
2. **Cơ chế nhả cuốn chiếu 1 phiên / 5 phút (One-message-per-tick):**
   - Đến 09:26, Phiên 2 trên Cụm Admin xong hẳn, `runner_busy = False`.
   - Cả 2 phiên đồng loạt đủ điều kiện báo cáo.
   - Watchdog có cơ chế chống spam chỉ gửi 1 tin mỗi tick (5 phút):
     - Tick 09:30: Gửi report Phiên 1/2.
     - Tick 09:35: Gửi report Phiên 2/2.

## 3. Giải pháp kỹ thuật chuẩn hóa
1. **Truyền `has_later_run` vào `_is_session_manifest_completed`:**
   ```python
   def _is_session_manifest_completed(date_live: str, run_name: str, win_end_hm: str, has_later_run: bool = False) -> bool:
       ...
       # Parse và validate end_time chuẩn HH:MM trước
       try:
           dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
           end_hm = dt.astimezone(HCMC).strftime("%H:%M") if dt.tzinfo else dt.strftime("%H:%M")
       except Exception:
           end_hm = end_time.replace("T", " ").split(" ", 1)[-1][:5]
       if not end_hm or not re.match(r"^\d{2}:\d{2}$", end_hm):
           continue
       # Nếu đã có lượt chạy của phiên sau (has_later_run) hoặc phiên qua đêm: hoàn tất ngay
       if has_later_run or win_end_hm in {"24:00", "00:00"}:
           return True
       if end_hm >= win_end_hm:
           return True
   ```
2. **Tính toán `has_later_run` trước trong `is_cluster_session_busy`:**
   - Tính `has_later_run = _has_later_session_run_started(date_live, latest_run_name, latest_hhmmss)` trước khi gọi kiểm tra manifest.
   - Truyền `has_later_run=has_later_run` vào `_is_session_manifest_completed`.
3. **Đồng bộ song song 2 bản sao:**
   - Bắt buộc sửa và giữ parity tuyệt đối giữa:
     - `scripts/feed_session_watchdog.py`
     - `scripts/hermes_cron/feed_session_watchdog.py`
   - Bổ sung test kiểm tra parity và unit test chống end_time malformed/corrupted (`test_feed_session_watchdog_parity_with_hermes_cron`).
