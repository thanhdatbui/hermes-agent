# Feed Session Watchdog: Early Completion & Later Run Release Logic

## 1. Triệu Chứng & Hiện Tượng (Sự Cố 20/10/2026)
- Watchdog báo cáo nuôi acc gửi 2 báo cáo liên tiếp của 2 phiên khác nhau cách nhau đúng 5 phút (ví dụ lúc 09:30 báo Phiên 1/2 và 09:35 báo Phiên 2/2).
- Khung giờ thực tế:
  * Ca 1 - Phiên 1/2 (06:00 - 08:00): Cụm Kibe xong lúc 08:03:14, Cụm Admin xong lúc 07:51:17.
  * Ca 1 - Phiên 2/2 (08:00 - 12:00): Cụm Kibe xong lúc 09:22:13, Cụm Admin xong lúc 09:26:32.
- Người dùng đặt câu hỏi: *"Sao lại trả report 2 phiên 1 lần v (cách nhau có 5ph) ?"*

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Kiểm tra cứng mốc kết thúc cửa sổ (`end_hm >= win_end_hm`)**:
   - Khi Phiên 2/2 bắt đầu chạy (từ 08:00), cờ toàn cục `is_feed_runner_active()` luôn là `True`.
   - Để nhả báo cáo phiên trước khi runner toàn cục đang bận chạy phiên sau, hàm `is_cluster_session_busy()` kiểm tra:
     ```python
     completed_after_window = _is_session_manifest_completed(date_live, latest_run_name, win_end_hm)
     ```
   - Hàm `_is_session_manifest_completed` trước đây kiểm tra cứng:
     ```python
     if end_hm >= win_end_hm:
         return True
     ```
   - Vì cụm Admin chạy nhanh và hoàn thành lúc 07:51:17 (trước 08:00), điều kiện `07:51 >= 08:00` là `False`.
   - Watchdog kết luận cụm Admin vẫn chưa xong Phiên 1/2 (`busy = True`), giam giữ báo cáo của Phiên 1/2 trong suốt thời gian Phiên 2/2 đang chạy.
2. **Cơ chế nhả cuốn chiếu 1 message / tick**:
   - Khi Phiên 2/2 kết thúc lúc 09:26:32, runner toàn cục rảnh (`runner_busy = False`). Cả 2 phiên cùng đủ điều kiện chốt.
   - Watchdog có cơ chế claim atomic 1 phiên mỗi tick 5 phút:
     * Tick 09:30: Gửi report Phiên 1/2.
     * Tick 09:35: Gửi report Phiên 2/2.

## 3. Giải Pháp Cơ Học & Tiêu Chuẩn Thẩm Định (Closeout Gate 83/100)
1. **Truyền cờ `has_later_run` vào `_is_session_manifest_completed`**:
   - Tính toán `has_later_run = _has_later_session_run_started(date_live, latest_run_name, latest_hhmmss)` trước.
   - Khi đã có lượt chạy mới của phiên tiếp theo xuất hiện (`has_later_run == True`), lượt chạy hiện tại chỉ cần có `end_time` hợp lệ là được xác nhận đã hoàn tất.
2. **Phòng vệ định dạng `end_time` (Reviewer Audit)**:
   - Bắt buộc parse `end_time` thành định dạng `HH:MM` chuẩn và validate regex `^\d{2}:\d{2}$` trước khi đánh giá `has_later_run`:
     ```python
     try:
         dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
         end_hm = dt.astimezone(HCMC).strftime("%H:%M") if dt.tzinfo else dt.strftime("%H:%M")
     except Exception:
         end_hm = end_time.replace("T", " ").split(" ", 1)[-1][:5]
     if not end_hm or not re.match(r"^\d{2}:\d{2}$", end_hm):
         continue
     if has_later_run or win_end_hm in {"24:00", "00:00"}:
         return True
     if end_hm >= win_end_hm:
         return True
     ```
3. **Đồng bộ song song**: Bắt buộc cập nhật cả 2 file:
   - `scripts/feed_session_watchdog.py`
   - `scripts/hermes_cron/feed_session_watchdog.py`
   Kèm unit test kiểm tra parity giữa hai bản triển khai.
