# Concurrency Bottleneck Diagnosis & Identity Switch Fail-Closed

## 1. Hiện Tượng "Nghẽn Diện Rộng" (Perceived Widespread Jam) vs Threadpool Concurrency

### Triệu Chứng
- Dashboard hoặc Alert báo hàng loạt máy (20–30 máy) cùng bị lock bởi một `PID` trong nhiều phút (ví dụ lock từ 21:27).
- Danh sách trạng thái hiển thị hỗn hợp giữa `running` và `queued_v2`.

### Bản Chất & Quy Trình Chẩn Đoán O(1)
1. **Kiểm Tra Tham Số CommandLine Khởi Chạy:**
   - So sánh `--machines` (tổng số máy chỉ định, ví dụ 67 máy) với `--max-workers` (trần luồng đồng thời, thường là 40 máy).
   - Nếu `len(machines) > max_workers`: Số máy dôi dư (ví dụ 27 máy) **bắt buộc phải xếp hàng (`queued_v2`)** chờ 40 máy đầu tiên hoàn tất.
   - Các máy trong hàng đợi đã đăng ký lock file từ khi batch khởi động để xí chỗ, tạo cảm giác "toàn bộ máy bị lock đồng loạt".
2. **Kiểm Tra Liveness Tiến Trình:**
   - Dùng lệnh `tasklist /fi "PID eq <PID>"` hoặc kiểm tra log O(1) `log.jsonl`.
   - Nếu tiến trình vẫn đang liên tục nhả máy cũ và nhận máy mới (hoặc đã exit clean), hệ thống KHÔNG bị deadlock socket ADB, KHÔNG treo router proxy hay proxy MikroTik.

---

## 2. Phân Biệt Lỗi Code vs Lỗi Dữ Liệu Slot / Thiếu Nick (`profile username still mismatched after switch`)

### Bối Cảnh & Cạm Bẫy
- Khi máy kết thúc với `status: manual-needed` và `error: profile username still mismatched after switch`, dễ bị hiểu nhầm là lỗi code switch profile bị tái phát (regression từ Case 119/131).

### Cơ Chế Phân Biệt
1. **Lỗi Code UI / Settle Timing (Đã fix ở Case 119 & 131):**
   - Tài khoản mục tiêu **đã có** trong danh sách switch của app TikTok trên máy.
   - Nhưng UI settle time quá ngắn, parser đọc username trước khi app nạp xong session mới, hoặc click overlay lệch vị trí.
   - Khắc phục: Đã nâng settle time lên 3.5–5.0s và chuẩn hóa nhận diện switcher reason.
2. **Lỗi Dữ Liệu Slot / Tài Khoản Chưa Nạp Lên Thiết Bị (Data / Account Provisioning State):**
   - Đọc O(1) file `summary.json` / `summary.txt` của máy:
     - `expected_account`: username yêu cầu tại row workbook (ví dụ row 6 là `@gabruync3o9`).
     - `current_username`: username hiện tại trên app TikTok (ví dụ `@amandabschmi86`).
     - `switch_attempts: 2`: Runner đã mở switcher tìm kiếm 2 lần.
   - **Hiện trạng:** Nick `expected_account` **hoàn toàn không tồn tại** trong danh sách tài khoản đã login trên máy đó (chưa từng đăng nhập, bị logout, hoặc mapping sai row trong workbook).
   - Khi chạy lệnh feed thông thường KHÔNG kèm cờ `--allow-auto-reconcile`:
     - Runner cố tình không tự động chạy login để tránh phá vỡ kiểm soát phiên nuôi acc.
     - Runner chuyển sang `manual-needed`, kích hoạt chuẩn **Fast Fail-Closed** và giữ lock `status: "blocked"` (TTL 1h / 3600s).
   - **Kết luận:** Đây là hành vi đúng chuẩn an toàn để bảo lưu hiện trường cho operator nạp/kiểm tra nick, KHÔNG PHẢI lỗi codebase.
