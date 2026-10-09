# Case 84 & Case 85: Cron Workbook Single Source of Truth & Mandatory Turn 1 Delegation

## 🛑 1. Bắt Buộc Coordinator Turn 1 Delegation Khi Nhận Farm Alert [MÁY N]
- **Quy tắc tuyệt đối:** Khi user gửi Farm Alert `[MÁY N]` hoặc sự cố dừng phiên, Main Session CHỈ ĐÓNG VAI TRÒ COORDINATOR.
- **Hành động bắt buộc ở Turn 1:** Gọi `delegate_task` ngay lập tức để spawn Worker subagent thực hiện:
  1. Trích xuất hiện trường bằng `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc lệnh ADB trực tiếp theo serial.
  2. Đọc file flow và log của máy bị lỗi.
  3. Patch script / fix bug và chạy test.
  4. Chạy canary test trên máy thật.
- **Cấm:** Coordinator tự gõ lệnh terminal, tự chạy canary hoặc tự sửa file trực tiếp trên session chính gây phình context và vi phạm quy trình điều phối.

---

## 📌 2. Chân Lý Duy Nhất (Single Source of Truth) — Cắt Bỏ File JSON Trung Gian (Case 84)
- **Vấn đề đã xảy ra:** Khi hệ thống duy trì file cấu hình trung gian `hermes_cron_source_config.json` nằm giữa `taikhoan_run_safe.xlsx` và `tiktok_picker.py`, khi thao tác swap nick / đổi nick trên Excel diễn ra, file trung gian không tự đồng bộ. Sáng ra picker đóng băng cohort theo danh sách cũ, trong khi runner đọc workbook thấy nick mới, gây ra lỗi fail-closed giả `cohort target identity mismatch: expected_username` (như sự cố Máy 1 Row 5 giữa `janayerton71` và `buithudung2011`).
- **Giải pháp chuẩn:**
  - Cắt bỏ hoàn toàn phụ thuộc vào `hermes_cron_source_config.json`.
  - `tiktok_picker.py` và cron runner đọc trực tiếp từ `taikhoan_run_safe.xlsx` thông qua canonical loader `SourceConfig.from_workbook()`.
  - Tự động sinh `default_feed_state` và `default_post_state` cho các nick mới xuất hiện khi swap máy.

---

## 🚀 3. Điều Phối Tham Số Canary & Launcher Gate (Case 85)
- **Vấn đề đã xảy ra:** Khi chạy `run-feed-session.ps1` để test canary thủ công đơn lẻ một máy (hoặc một row cụ thể), script tự động inject `--assignment-manifest` và `--worker-id` từ biến môi trường của farm, nhưng không có `--cohort-artifact`, khiến `multi_machine_feed_session.py` hiểu nhầm là một live cohort child bị thiếu file cohort và fail ngay ở preflight.
- **Giải pháp chuẩn:**
  - Trong `run-feed-session.ps1`, chỉ truyền `--assignment-manifest` và `--worker-id` khi `--cohort-artifact` được cung cấp tường minh.
  - Khi canary test cho nick cụ thể, phải đối chiếu số dòng trong `taikhoan_run_safe.xlsx` và truyền đúng `-Row N` tương ứng (không mặc định `-Row 1`).
