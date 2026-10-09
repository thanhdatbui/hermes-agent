# Device Lock Reaper & Watchdog Invariants (TikTok Feed Session)

## 1. Lệch pha giữa Khoảng cách Phiên (Session Interval) và Lock TTL
- **Hiện tượng:** Runner skip hàng loạt máy ở đầu phiên với lý do `skipped-device-locked` dù ca trước đã dừng từ lâu.
- **Nguyên nhân gốc rễ:**
  - Trạng thái `blocked` được thiết kế để giữ nguyên hiện trường phục vụ điều tra lỗi, có TTL bảo vệ (mặc định 90 phút trong `reap-dead-owner-locks.py`).
  - Lịch nuôi acc gồm các phiên cách nhau khoảng 70 - 90 phút (vd: Ca 1 Phiên 3 kết thúc lúc 11:34, Ca 2 Phiên 1 bắt đầu lúc 12:45).
  - Khoảng nghỉ giữa 2 phiên (71 phút) ngắn hơn TTL 90 phút, dẫn đến khi phiên mới bắt đầu, các máy lỗi của phiên trước vẫn còn nằm trong thời gian bảo vệ TTL -> Runner buộc phải skip an toàn.
- **Quy tắc vận hành:**
  - Muốn các máy lỗi tự động tham gia phiên kế tiếp, TTL lock phải được tính toán nhỏ hơn khoảng cách giữa các phiên (khuyến nghị 40 - 60 phút) hoặc có cơ chế sweep trước giờ phiên chạy.
  - Ngưỡng cảnh báo lock giữ lâu trong `watch_device_locks.py` (`ALERT_THRESHOLD_MINUTES`) chuẩn hóa về 40 phút. Preflight reap timeout nâng lên 120s. Bổ sung broadcast cảnh báo nghẽn diện rộng khi tổng số lock đang giữ >= 30 máy (`⚠️ CẢNH BÁO NGHẼN LOCK DIỆN RỘNG (>= 30 MÁY)`).

## 2. Nghẽn ADB Timeout trong Cron Dọn Lock (`reap-dead-owner-locks`)
- **Hiện tượng:** Cronjob `reap-dead-owner-locks` kết thúc với trạng thái `error` kèm traceback `subprocess.TimeoutExpired: ... timed out after 120 seconds`.
- **Nguyên nhân gốc rễ:**
  - Khi dọn lock (`shutil.move` vào quarantine), script gọi `_cleanup_device_screen(serial)` gửi 3 lệnh ADB (`am force-stop` x2, `keyevent 3` với timeout 10s/lệnh) để đưa máy về Home.
  - Mỗi máy farm có 2 file lock (`machine_X.lock.json` và `serial_Y.lock.json`). Script duyệt từng file nên bị gọi trùng 2 lần cho 1 serial.
  - Nếu gặp nhiều máy cùng lúc bị rớt mạng / mất kết nối ADB (như máy bị `dumpsys connectivity: Wi-Fi not connected` hoặc ADB lost transport), các lệnh ADB chạy tuần tự và bị timeout 10s x 3 lệnh = 30s/máy.
  - Khi dọn từ 4 máy lỗi mạng trở lên, tổng thời gian chờ ADB vượt quá trần timeout ban đầu của wrapper -> cronjob bị kill và gián đoạn giữa chừng.
- **Quy tắc khắc phục:**
  - Nâng timeout wrapper `reap-dead-owner-locks-wrapper.py` lên 180s (chống kill sớm khi nhiều máy offline cùng lúc).
  - Khử trùng lặp serial khi dọn lock (chỉ cleanup 1 lần duy nhất cho mỗi device serial trong 1 lần chạy reap).
  - Các lệnh ADB cleanup phải fail-fast (giảm timeout xuống 3-5s) hoặc bỏ qua nếu thiết bị đang offline/unreachable để không bao giờ làm nghẽn tiến trình dọn dẹp file lock.

## 3. Khoảng trống Phân loại Thống kê Follow trong Watchdog (`feed_session_watchdog.py`)
- **Hiện tượng:** Watchdog báo tổng số máy xử lý là N (vd 79 máy: 58 success + 21 fail), nhưng mục Follow chỉ báo số máy ít hơn (vd 59 máy bỏ qua), thiếu mất 20 máy.
- **Nguyên nhân gốc rễ:**
  - Vòng lặp phân loại follow chỉ kiểm tra:
    1. Nếu có `follow_result.json`: phân loại vào success / released / error / skipped.
    2. Nếu KHÔNG có `follow_result.json`: chỉ ghi nhận lỗi nếu `status == "success"` ở bước Feed.
  - Các máy bị dừng từ trước (do `skipped-device-locked` hoặc `blocked-proxy-vpn`) không bao giờ chạy tới hook follow nên không có `follow_result.json`, đồng thời cũng không có `status == "success"` ở Feed. Do đó, chúng bị lọt khỏi mọi nhánh thống kê của Follow, gây lệch tổng số máy.
- **Quy tắc phân loại:** Mọi máy trong danh sách xử lý của phiên bắt buộc phải rơi vào đúng 1 trạng thái ở mục Follow (nếu không chạy do Feed fail/lock thì phải tính vào nhóm Bỏ qua / Bỏ qua do Feed không đạt).
