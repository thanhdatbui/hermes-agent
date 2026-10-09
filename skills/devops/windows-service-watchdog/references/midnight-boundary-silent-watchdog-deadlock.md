# Midnight Boundary Silent Watchdog Deadlock & Schedule Alignment

## Bối cảnh & Vấn đề (2026-09-20)
Khi triển khai các watchdog kiểu Silent Watchdog trên Hermes Cron (`no_agent=True`):
- Watchdog chạy cuốn chiếu các batch nền (ví dụ: upload avatar, đồng bộ dữ liệu, đổi mật khẩu) trong khung giờ tối (20:15 - 23:45).
- Để chống spam Telegram (`-5373649734`), watchdog tuân thủ nguyên tắc: **IM LẶNG TUYỆT ĐỐI** giữa các batch lẻ, **CHỈ IN STDOUT 1 LẦN DUY NHẤT** khi toàn bộ hoàn tất 100% hoặc khi hết khung giờ ca tối (`is_after_evening_window` -> `report_final_summary`).

### Hiện tượng Deadlock im lặng:
1. Batch cuối cùng (ví dụ Tik 8) được kích hoạt lúc 23:35 và chạy đến 23:56:35 mới kết thúc.
2. Lịch cronjob của Hermes được cấu hình: `*/5 20,21,22,23 * * *`.
3. Lần tick cuối cùng trong ngày chạy lúc **23:55:08**:
   - Lúc này batch Tik 8 vẫn đang chạy dở.
   - Watchdog kiểm tra thấy tiến trình PowerShell/Python còn sống -> `return 0` (im lặng chờ batch xong).
4. Lúc **23:56:35**, batch kết thúc thành công.
5. **DEADLOCK**: Do cron schedule bị ngắt ở `23`, sau 23:55 không còn bất kỳ tick nào được gọi trong khung giờ rạng sáng (`00:00 - 04:00`).
6. Dẫn tới file state vẫn giữ `running_batch`, watchdog không bao giờ được đánh thức lại để dọn state và gửi báo cáo tổng kết. Người dùng thấy job biến mất im lặng và không có báo cáo nào gửi về Farm Alert.

---

## Nguyên nhân gốc rễ
Sự lệch pha giữa logic thời gian trong Code và Lịch trình Cron (Code vs Cron Invariant Mismatch):
- **Trong mã nguồn Python**: Hàm `is_after_evening_window(now_dt)` được thiết kế hỗ trợ từ `23:45 đến 04:00 sáng hôm sau` (`h == 23 and m > 45` hoặc `0 <= h < 4`).
- **Trong Hermes cronjob**: Tham số `schedule` lại bị cắt cụt ở `23` (`*/5 20,21,22,23 * * *`), bỏ quên các giờ qua đêm `0, 1, 2, 3`.

---

## Quy tắc thiết kế chuẩn (Invariants)
1. **Cron Schedule Bắt Buộc Phủ Hết After-Window**:
   - Khi một job có batch được kích hoạt đến 23:45 và mỗi batch có thể chạy tối đa 30-45 phút, thời điểm kết thúc thực tế chắc chắn sẽ tràn qua `00:xx`.
   - Lịch cron BẮT BUỘC phải bao quát các giờ rạng sáng tiếp theo:
     ```cron
     */5 20,21,22,23,0,1,2,3 * * *
     ```
2. **Quy trình Chẩn đoán O(1) khi Watchdog "Im bặt"**:
   - Kiểm tra `state.json` của watchdog: Đọc timestamp `start_time` và `pid` của `running_batch`.
   - Đối chiếu `time.time() - start_time`: nếu > 45 phút và process đã chết mà `running_batch` vẫn còn trong state -> Cron bị thiếu tick đánh thức sau khi batch hoàn tất.
   - Kiểm tra `cronjob action='list'` -> Xem trường `schedule` có bị cắt cụt ở giờ cuối cùng không.
   - Kích hoạt bù ngay: `cronjob action='run' job_id='...'` để watchdog giải phóng state và xuất stdout báo cáo.
   - Cập nhật vĩnh viễn schedule: `cronjob action='update' job_id='...' schedule='...'`.
