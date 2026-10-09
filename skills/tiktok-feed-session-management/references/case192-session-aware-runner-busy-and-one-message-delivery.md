# Case 192: Session-Aware Runner Busy & One-Message-Per-Session Delivery Invariant (28/09/2026)

## 1. Hiện Tượng & Khiếu Nại Của Người Vận Hành
- Người vận hành phát hiện watchdog `tiktok-feed-session-watchdog` (job_id: `1d62cb3562e0`) gộp chung 2 phiên (Ca 3 Phiên 1/2 và Phiên 2/2) vào cùng 1 tin nhắn Telegram dài.
- Thắc mắc: *"tao bảo rõ ràng là phiên nào xong gửi cron phiên đó sao lại gộp 2 phiên làm 1 thế này"*.

## 2. Nguyên Nhân Kép (Double Root Cause)

### A. Phiên 1 Bị Chặn Giữ Bởi Tiến Trình Phiên 2 (Runner Busy Coupling)
- **Phiên 1 (18:00 – 20:00)** kết thúc lúc `20:02:59` (cả 80 máy Kibe + Admin đã hoàn tất, `run_manifest.json` đã đóng `end_time`).
- **Phiên 2 (20:00 – 24:00)** gối đầu chạy ngay lúc `20:02:25`.
- Trong khi Phiên 2 đang chạy, hàm `is_feed_runner_active()` luôn trả về `True` trên toàn máy chủ.
- Hàm `can_report_session()` trước đây chỉ nhận cờ `runner_busy` toàn cục của host. Thấy runner bận, watchdog tự động hoãn (silent hold) Phiên 1 suốt 1.5 giờ dù Phiên 1 đã hoàn tất 100% từ lâu.

### B. Gom Mảng Tin Nhắn Khi Xả Báo Cáo (`"\n\n".join(messages)`)
- Đến `21:37` khi Phiên 2 kết thúc, `runner_busy` về `False`.
- Ở tick cron kế tiếp, watchdog duyệt qua cả Phiên 1 và Phiên 2, gom cả 2 báo cáo vào mảng `messages = [msg1, msg2]` rồi chạy `print("\n\n".join(messages))`.
- Cronjob chạy `no_agent: true` bắt toàn bộ stdout của tiến trình gửi thành 1 tin nhắn Telegram duy nhất, vi phạm nghiêm trọng quy tắc mỗi phiên 1 tin nhắn độc lập.

## 3. Kiến Trúc Khắc Phục Chuẩn (Modular & Decoupled)

### A. Phân Rã Trách Nhiệm Runner Busy Theo Cấp Phiên
Thay vì dồn mọi logic vào một hàm nguyên khối, tách thành 2 helper đơn nhiệm và 1 coordinator:
1. `_is_session_manifest_completed(date_live, run_name, win_end_hm) -> bool`:
   - Đọc `run_manifest.json` tại run directory chính hoặc child run directory.
   - Kiểm tra `end_time` hợp lệ dạng string.
   - So sánh `end_hm >= win_end_hm` (hoặc boundary midnight `24:00` / `00:00`).
2. `_has_later_session_run_started(date_live, latest_run_name, latest_hhmmss) -> bool`:
   - Quét các thư mục trong `date_live`.
   - Trích xuất timestamp số `parts[2][:6]` để so sánh an toàn, tránh lỗi thứ tự chuỗi / khác format row: `int(parts[2][:6]) > int(str(latest_hhmmss)[:6])`.
3. `is_cluster_session_busy(...) -> bool`:
   - Nếu session hiện tại đã có manifest hoàn thành sau giờ `win_end_hm` VÀ đã có run của session sau xuất hiện trong thư mục ngày $\rightarrow$ giải phóng `decision = False`.
   - Ghi log structured telemetry `[WATCHDOG_BUSY_TELEMETRY]` phục vụ giám sát production.

### B. Khóa Cứng Kỷ Luật One-Message-Per-Session (Single Delivery Queue)
- Trong vòng lặp xuất báo cáo của `main()`:
  - Sau khi format thành công 1 phiên hoàn tất: `messages.append(msg)`, `new_reported.add(session_key)`, và gọi ngay `break`.
  - Khối ngoài kiểm tra `if messages: break`.
  - Chỉ in duy nhất phần tử đầu tiên: `print(messages[0])`.
  - Ghi log telemetry `[WATCHDOG_DELIVERY_TELEMETRY] event=one_message_delivered`.
- **Cơ chế cuốn chiếu (Tick-by-Tick Queue):** Nếu có nhiều phiên cùng đến hạn, watchdog gửi Phiên 1 ở tick hiện tại và Phiên 2 ở tick 5 phút tiếp theo thành 2 tin nhắn Telegram riêng biệt.

## 4. Quy Trình Đồng Bộ 4 Vị Trí (Bắt Buộc Khớp MD5)
1. `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`
2. `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
3. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py`
4. `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/feed_session_watchdog.py`
- Kiểm tra sau copy: hash MD5 cả 4 vị trí phải trùng khớp 100%.

## 5. Tiêu Chuẩn Test Sol Auditor Scorecard (>= 85 Điểm)
- Bắt buộc kiểm thử cả:
  - Session hoàn tất có later run xuất hiện $\rightarrow$ `busy = False`.
  - Session chưa xong hoặc chưa có later run $\rightarrow$ `busy = True`.
  - Edge cases: manifest hỏng (corrupt JSON), manifest thiếu `end_time`, `end_time` sai kiểu dữ liệu, danh sách session rỗng.
  - Boundary midnight: mốc giờ `24:00` / `00:00`.
  - Đặt tên thư mục không chuẩn: khác row prefix (ví dụ `row-2-200500` vs `row-6-180033`).
  - Kiểm tra format log `[WATCHDOG_BUSY_TELEMETRY]` qua `assertLogs`.
  - Kiểm tra queue delivery đơn phiên và atomic state claim persist xuống đĩa.
