# Aborted Feed Runner vs No-Run-Recorded False Mass ADB Disconnect Triage

## 1. Hiện Tượng & Cạm Bẫy
- **Cảnh báo từ Watchdog:** `🚨 [FARM ALERT] PHÁT HIỆN LỖI NUÔI FEED HÀNG LOẠT (109 máy lỗi) - Ca 1 - Phiên 1/2 (Sáng)` với lý do chủ đạo: `Mất kết nối ADB/USB (51 trên Kibe, 34 trên Admin)`.
- **Cạm bẫy Coordinator tự suy diễn (Hallucination Trap):**
  - Tự biện minh rằng "Farm chia 2 phiên, mỗi phiên chạy 1 nửa máy (cohort 1 vs cohort 2)" ➔ **HOÀN TOÀN SAI**. Mọi phiên nuôi feed (Phiên 1 và Phiên 2) đều chạy toàn bộ dàn máy (74-80 máy/cụm) có account hợp lệ.
  - Kết luận vội vã phần cứng sụt nguồn Hub USB trong khi `adb devices` và `inspect_machine.py` vẫn thấy 156/160 máy online 100%.

## 2. Cơ Chế Gốc Gây Báo Động Giả
1. **Runner bị ngắt giữa chừng (Premature Batch Interruption):**
   - Runner `run-feed-session.ps1` chạy theo lô workers (`MaxWorkers = 25`). Lô đầu hoàn thành (24 máy Kibe, 23 máy Admin). Lô sau mới bắt đầu (M1, M2, M3, M9, M13...) thì tiến trình runner bị kill/crash đột ngột (cùng một thời điểm đồng loạt trên cả 2 host).
   - Các máy đang chạy dở hoặc chưa kịp start không có `run_manifest.json` trong thư mục `machines/`.
2. **Watchdog phán nhãn `no-run-recorded`:**
   - Trong `feed_session_watchdog.py`: mọi máy thuộc `expected_machines` nhưng không có trong `all_machines` bị gán:
     ```python
     all_machines[fm] = {"status": "fail", "reason": "no-run-recorded"}
     ```
3. **Bộ phân loại gom nhãn sai lệch (`formatters.py`):**
   - Hàm `classify_feed_failure()` chứa:
     ```python
     if any(k in r for k in (..., "no-run-recorded", ..., "adb/usb")):
         return "Mất kết nối ADB/USB"
     ```
   - Hậu quả: Tiến trình runner bị ngắt giữa chừng bị biến tướng thành báo cáo "mất kết nối ADB/USB" hàng loạt.

## 3. Quy Trình Điều Tra Chuẩn Xác O(1)
1. **Kiểm tra fleet tổng:** Chạy `python D:/Taadaa/tools/inspect_machine.py` (không tham số). Nếu vẫn online ~77 máy Kibe và ~79 máy Admin ➔ Khẳng định ngay KHÔNG phải lỗi cáp/hub USB.
2. **Kiểm tra mtime các log máy dở dang:** Xem timestamp cuối cùng trong `log.jsonl` của các máy fail. Nếu toàn bộ dừng lại ở cùng một phút (ví dụ 06:19) ➔ Đây là sự cố runner tiến trình nền bị ngắt đột ngột (crash/kill/reboot), không phải lỗi từng máy riêng lẻ.
3. **Đối chiếu lịch sử chạy ngày hôm trước:** Kiểm tra thư mục ca hôm trước (ví dụ `row-0-060026/machines`), đếm tổng số máy chạy để tái xác nhận phiên chạy toàn bộ dàn máy chứ không bao giờ có chuyện "chạy nửa máy".
