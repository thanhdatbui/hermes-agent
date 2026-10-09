# Post-Evening Watchdog Midnight Schedule Alignment & Silent Report Deadlock

## Bối cảnh & Hiện tượng (2026-09-20)
- Watchdog hậu ca tối (như `post_evening_avatar_watchdog.py`, `post_evening_gpm_login_watchdog.py`) chạy cuốn chiếu các batch nền (upload avatar, nạp GPM, đổi mật khẩu) trong khung giờ 20:15 - 23:45.
- Theo quy tắc Farm Watchdog: **IM LẶNG TUYỆT ĐỐI** giữa các batch lẻ để chống spam nhóm Farm Alert, và **CHỈ BÁO CÁO DUY NHẤT 1 LẦN** khi hoàn tất 100% hoặc khi hết khung giờ ca tối (`report_final_summary`).
- Sự cố: Batch cuối cùng (ví dụ Tik 8) được kích hoạt lúc 23:35 và chạy đến 23:56 mới xong.
- Lúc 23:55 (tick cuối cùng trong ngày của cron schedule `*/5 20,21,22,23 * * *`), watchdog kiểm tra thấy tiến trình batch vẫn đang sống -> `return 0` (im lặng chờ batch hoàn tất).
- Đến 23:56, batch kết thúc thành công. NHƯNG vì cron schedule bị cắt cụt ở `23`, sau 23:55 scheduler không còn tick nào kích hoạt trong khung giờ 00:00 - 04:00 sáng.
- Hậu quả: Báo cáo tổng kết bị "treo im lặng", batch chạy xong nhưng không bao giờ có tick cron nào đánh thức watchdog để phát hiện và gửi báo cáo Farm Alert. User tưởng cron không chạy.

## Nguyên nhân gốc rễ
- **Lệch pha giữa Code logic và Cron Schedule (Code vs Cron Invariant Mismatch)**:
  - Trong code Python, hàm `is_after_evening_window(now_dt)` được định nghĩa từ `23:45 đến 04:00 sáng hôm sau` (`h == 23 and m > 45` hoặc `0 <= h < 4`).
  - Trong cấu hình cron (`jobs.json` / Hermes cronjob), schedule lại chỉ đặt `*/5 20,21,22,23 * * *` (thiếu các giờ rạng sáng `0, 1, 2, 3`).

## Nguyên tắc bất biến (Invariants)
1. **Schedule Phải Phủ Hết Timeout & After-Window**:
   - Mọi watchdog có batch chạy về đêm hoặc có logic `after_window` kéo dài qua nửa đêm BẮT BUỘC schedule cron phải bao phủ các giờ rạng sáng tiếp theo:
     ```cron
     */5 20,21,22,23,0,1,2,3 * * *
     ```
     hoặc tối thiểu `0,1,2,3`.
2. **Cấm Để Schedule Ngắt Lúc 23:xx Nếu Có Batch Spawn Sau 23:00**:
   - Nếu batch có thời gian thực thi 20-45 phút và được phép kích hoạt đến 23:45, điểm kết thúc thực tế của nó sẽ rơi vào `23:55 - 00:30`. Cronjob bắt buộc phải sống qua ranh giới nửa đêm để dọn dẹp state và gửi báo cáo nghiệm thu.
3. **Quy trình Kiểm tra O(1) khi Watchdog Không Báo Cáo**:
   - Đọc state file: `post_evening_avatar_state.json` -> xem `running_batch` (start_time, pid) và `last_reported_session`.
   - Tính diff time giữa `start_time` và thời điểm hiện tại: nếu batch đã xong nhưng `running_batch` vẫn còn trong file state -> chứng tỏ cronjob bị thiếu tick sau khi batch kết thúc.
   - Kiểm tra `cronjob action='list'` -> đối chiếu trường `schedule` với các hàm kiểm tra window trong code (`is_post_evening_window`, `is_after_evening_window`).
   - Trigger bù tức thời: `cronjob action='run' job_id='...'` để watchdog dọn state và gửi báo cáo bù, sau đó update cron schedule bằng `cronjob action='update' job_id='...' schedule='...'`.
