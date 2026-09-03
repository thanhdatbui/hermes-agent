# Per-device timeout và terminalization trong feed batch

## Khi áp dụng

Dùng cho `feed-session-smoke` và `multi-machine-feed-session` khi một máy:

- mất ADB hoặc UI capture;
- lặp `wait`, splash-poll, recapture hoặc retry mà không tiến triển;
- process batch vẫn sống nhưng target không có `summary.txt`;
- lock/handoff không chuyển sang trạng thái terminal.

## Mẫu lỗi cần nhận diện

`ThreadPoolExecutor` chỉ giới hạn số worker, không tự tạo deadline cho từng target. Nếu worker có vòng chờ nội bộ vô hạn (ví dụ mỗi poll có budget 60 giây rồi quay lại poll mới), parent `future.result()` sẽ chờ vô hạn. Vì vậy tổng batch có thể treo dù các máy khác đã hoàn tất.

Không kết luận chỉ từ tổng thời gian batch: phân biệt máy chạy lâu nhưng đã có `summary.txt`/`success` với máy không có summary và còn process trong vòng chờ.

## Contract sửa bắt buộc

1. Tạo deadline monotonic **riêng cho từng machine**, mặc định 900 giây (15 phút); cho phép test override bằng timeout nhỏ.
2. Mọi vòng retry/poll/sleep bên trong worker phải gọi guard deadline ở đầu vòng và trước hành động tiếp theo. Chỉ đặt timeout trên `future.result()` là chưa đủ.
3. Khi hết deadline, tạo kết quả terminal không thành công, ví dụ `final_status=device-timeout` hoặc `failed`, với:
   - `stop_reason` nêu rõ per-device timeout và operation cuối;
   - số swipe/step đã hoàn tất;
   - log timeout có timestamp và artifact path.
4. Luôn ghi `summary.txt`/manifest của target trong đường `finally`, kể cả worker ném exception hoặc timeout.
5. Chạy cleanup đúng policy đã được bật: force-stop TikTok + HOME chỉ khi route được phép; không tap mù, không restart ADB, không tác động máy khác.
6. Non-success phải publish handoff evidence trước khi đổi lock; giữ lock ở `blocked`/`handoff` theo contract, không release như thể thành công. Chỉ success đã verify mới finish/release lock.
7. Target timeout không được hủy toàn batch; sibling workers vẫn được aggregate và terminalize độc lập.

## Regression test tối thiểu

Dùng fake clock hoặc timeout test-only rất nhỏ, không chạy ADB/live device:

- worker A bị giữ trong inner poll loop quá deadline;
- worker B hoàn thành success;
- assert A có một row terminal non-success, `stop_reason` chứa timeout, `summary.txt` tồn tại và có `final_status`;
- assert cleanup của A chạy tối đa một lần và lock A không bị ghi success/released;
- assert B vẫn có summary/success và batch aggregate là non-success vì A;
- assert mỗi poll đều chạm deadline guard, tránh regression kiểu chỉ timeout ở outer future.

Test riêng inner loop để chứng minh bug cũ: fake `get_focused_activity()` luôn trả rỗng, `time.sleep()` không làm deadline trôi giả tạo, và guard phải kết thúc thay vì lặp vô hạn.

## Evidence và báo cáo

Thu thập tối thiểu: thời điểm start, thời điểm deadline, operation cuối, số poll, first ADB/UI error, process/artifact state, summary existence và lock status. Máy có ADB timeout nhưng đã summary terminal là lỗi đã tự đóng, không xếp cùng nhóm "timeout không tự close".

Báo cáo ngắn theo `mục đích / kết quả / blocker`; không đưa credential, password, serial thật hoặc workbook path nhạy cảm vào log/report.
