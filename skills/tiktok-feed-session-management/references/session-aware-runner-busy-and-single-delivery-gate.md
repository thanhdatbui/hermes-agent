# Session-Aware Runner Busy & Single Delivery Gate (Khắc Phục Lỗi Gộp 2 Phiên Vào 1 Tin Nhắn)

## 1. Hiện Tượng & Triệu Chứng
- Người vận hành phát hiện watchdog gom 2 phiên liên tiếp (ví dụ Ca 3 - Phiên 1/2 và Ca 3 - Phiên 2/2) vào chung một tin nhắn Telegram duy nhất.
- Phiên 1 đã kết thúc trước đó hơn 1.5 giờ nhưng không hề gửi báo cáo ngay khi xong, mà đợi đến khi Phiên 2 kết thúc mới xuất cả 2 phiên cùng lúc.
- User phản ánh: *"tao bảo rõ ràng là phiên nào xong gửi cron phiên đó sao lại gộp 2 phiên làm 1 thế này"*.

## 2. Phân Tích Nguyên Nhân Kép (Dual Root Cause)

### A. Global `runner_busy` Gây Nghẽn Báo Cáo Phiên Trước (Cascading Hold)
- `feed_session_watchdog.py` kiểm tra tiến trình feed bằng hàm `is_feed_runner_active()`. Hàm này quét toàn bộ tiến trình trên máy chủ (psutil) và trả về `True` nếu có bất kỳ batch runner nào đang chạy.
- Khi Ca 3 Phiên 1 (18:00 - 20:00) kết thúc lúc 20:02:59 (80 máy hoàn tất, file `run_manifest.json` đã đóng `end_time`), Ca 3 Phiên 2 (20:00 - 24:00) đã được launcher kích hoạt ngay lúc 20:02:25.
- Do Phiên 2 đang chạy, `is_feed_runner_active()` trả về `True` liên tục từ 20:02 đến 21:37.
- Trong `can_report_session()`, điều kiện bảo vệ `if is_today and runner_busy: return False` nhận cờ `runner_busy` toàn cục. Kết quả là Phiên 1 bị giam giữ (hold) suốt 1.5 tiếng dù đã kết thúc 100%.

### B. Gom Danh Sách Thông Điệp (`messages.append` + `print("\n\n".join(messages))`)
- Đến 21:37 khi Phiên 2 kết thúc, `runner_busy` mới trở về `False`.
- Ở tick cron 21:52, watchdog quét thấy cả Phiên 1 và Phiên 2 đều thỏa mãn điều kiện báo cáo.
- Vòng lặp `main()` duyệt qua cả hai `win` trong `SESSION_WINDOWS`, gom cả 2 thông điệp vào `messages = [msg_p1, msg_p2]`.
- Sau vòng lặp, script thực hiện `print("\n\n".join(messages))`.
- Cronjob `tiktok-feed-session-watchdog` (chạy chế độ `no_agent: true`) nhận toàn bộ stdout và chuyển tiếp đến Telegram adapter thành **1 tin nhắn văn bản duy nhất** dài hơn 6.000 ký tự.

## 3. Giải Pháp Kỹ Thuật Chuẩn (Patch Contract)

### 1. Cơ Chế Session-Aware Runner Busy (`is_cluster_session_busy`)
Thay vì dùng `runner_busy` toàn cục cho mọi phiên, watchdog kiểm tra theo từng session cụ thể:
- Nếu phiên đang kiểm tra đã vượt qua giờ kết thúc của window (`now_hm >= win["end"]`):
  - Kiểm tra thư mục run mới nhất của session đó: nếu đã có file `run_manifest.json` và chứa trường `end_time` (chứng minh session đã xong hoàn toàn).
  - Kiểm tra thư mục ngày (`date_live`): nếu đã có run folder của phiên tiếp theo xuất hiện (`r_hm >= win["end"]`).
  - Khi thỏa mãn cả 2 điều kiện trên, trả về `session_runner_busy = False` cho session đó, bất kể máy chủ đang chạy phiên tiếp theo.
- Nhờ đó, Phiên 1 được xả báo cáo ngay ở tick cron đầu tiên sau khi kết thúc (lúc 20:05), không bị Phiên 2 chặn lại.

### 2. Khóa Cứng Kỷ Luật "One-Message-Per-Session" Tại Vòng Lặp
Để bảo đảm bất biến mỗi lần chạy chỉ gửi đúng 1 phiên:
- Trong vòng lặp `for win in SESSION_WINDOWS:`: Ngay sau khi format xong 1 phiên và claim state key, thực hiện `break`.
- Ở vòng lặp ngày `for target_date, is_today in dates_to_check:`: Nếu `messages` đã có dữ liệu, thực hiện `break`.
- Thay thế hoàn toàn `print("\n\n".join(messages))` bằng `print(messages[0])`.
- Nếu có tình huống nhiều phiên cùng sẵn sàng báo cáo (ví dụ sau downtime hệ thống), watchdog sẽ claim và gửi Phiên 1 ở tick cron hiện tại, và Phiên 2 sẽ được gửi độc lập ở tick cron kế tiếp (5 phút sau), tuyệt đối không bao giờ nối chuỗi 2 phiên vào chung 1 payload.

## 4. Quy Trình Kiểm Thử & Đồng Bộ
1. Unit test: Bổ sung test case kiểm tra `is_cluster_session_busy` trả về `False` khi phiên trước đã có `end_time` và có run tiếp theo, đồng thời trả về `True` khi đang trong giờ chạy.
2. Kiểm tra bộ test regression: Toàn bộ unit tests của `test_feed_session_watchdog.py` phải PASS 100%.
3. Đồng bộ nghiêm ngặt đủ 4 vị trí:
   - `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`
   - `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
   - `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py`
   - `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/feed_session_watchdog.py`
