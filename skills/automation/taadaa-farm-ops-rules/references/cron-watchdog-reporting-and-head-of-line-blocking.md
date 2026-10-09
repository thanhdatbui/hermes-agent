# Kỷ Luật Báo Cáo Watchdog & Chống Nghẽn Cổ Chai (Head-of-Line Blocking) Trên Farm

## 1. Phân Biệt Tuyệt Đối Giữa "Upload Avatar" và "Đăng Video" (Upload Video)
- **Upload Avatar (`post-evening-avatar-watchdog`)**:
  - Khung giờ: Sau ca tối (20:00 -> 23:45).
  - Mục tiêu: Chỉ chạy cho các nick chưa từng có avatar (`has_avatar == 0` hoặc cột `Avatar != 'OK'`).
  - Runner: `run_tiktok_upload_avatar.ps1`.
- **Đăng Video (`multi_machine_feed_session.py` hook `run_upload`)**:
  - Khung giờ: Tích hợp vào phiên cuối của từng ca nuôi feed (Ca sáng, Ca chiều, Ca tối, Ca đêm).
  - Runner: `D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\run_post.py`.
- **Kỷ luật đối soát khi User hỏi "cron up"**:
  - Luôn kiểm tra log alert gần nhất trên Telegram channel `-5373649734` hoặc `cron/output/` để xác định user đang phản hồi tin nhắn của watchdog nào.
  - Tuyệt đối không suy đoán mù quáng hay lẫn lộn giữa tiến độ up avatar và đăng video.

---

## 2. Anti-Pattern Head-of-Line Blocking trong Batch Dispatcher Đa Mục Tiêu
- **Hiện tượng**:
  - Script duyệt qua danh sách các nhóm/Tik theo thứ tự cố định (ví dụ `target_tiks = [5, 6, 7, 8, 3, 4]`).
  - Script luôn tìm `missing_machines` của Tik đầu tiên, nếu còn máy thiếu thì spawn batch cho Tik đó và `return 0`.
  - Khi một vài máy ở Tik đầu tiên bị lỗi phần cứng/app/mất mạng (ví dụ 7 máy M10, M30, M44, M72 ở Tik 5), chúng không bao giờ hoàn thành $\rightarrow$ Script liên tục lặp lại 15-20 batch xuyên suốt nhiều giờ chỉ để thử lại Tik đó, khiến toàn bộ các Tik sau (Tik 6, 7, 8, 3, 4) bị **bỏ đói 100%**.
- **Giải pháp bắt buộc**:
  1. **Cơ chế Cuốn Chiếu (Round-Robin / Sequential Cursor)**:
     - Ghi nhận `last_dispatched_target` vào state file phiên.
     - Lần trigger tiếp theo bắt buộc chuyển sang target kế tiếp, xoay vòng đều qua tất cả các target thay vì kẹt ở target đầu.
  2. **Session Retry Cap & Blacklist Tạm Thời**:
     - Đếm số lần thất bại của từng máy trong phiên.
     - Máy fail quá ngưỡng (thường là 2 lần) trong cùng một ca phải được gắn cờ `session_blacklisted` để nhường tài nguyên cho các máy khác, không spam vô tận.

---

## 3. Tiêu Chuẩn Báo Cáo Watchdog: Dynamic Session Delta vs Static Snapshot
- **Anti-Pattern "Báo cáo mù mờ"**:
  - Chỉ đọc database/workbook và in snapshot tổng tích lũy: *"Hết khung giờ ca tối (sau 23:30) — Đã có: 240/532 acc (45.1%), còn 292 máy chưa up"*.
  - Người điều hành không thể biết trong ca vừa rồi hệ thống có thực sự chạy không, up được bao nhiêu acc mới, máy nào bị lỗi, máy nào bị kẹt.
- **Tiêu chuẩn Báo cáo Bắt buộc (Action-First & Session Delta)**:
  1. **Kết quả thực thi trong ca (Session Delta)**:
     - Đã kích hoạt bao nhiêu batch cho các target nào.
     - Số máy vừa hoàn thành thành công mới trong ca (kèm danh sách máy cụ thể).
  2. **Chi tiết lỗi / máy kẹt trong ca**:
     - Danh sách các máy thất bại kèm mã lỗi/lý do ngắn gọn.
  3. **Tiến độ lũy kế toàn farm**:
     - Tỷ lệ hoàn thành tổng thể của từng target sau khi kết thúc ca.
