# Cooperative Device Handoff & Preemption Architecture (Taadaa Phone Farm 160 máy)

## Bối cảnh và vấn đề
Khi một máy đang chạy tác vụ dài hạn (ví dụ: `run_tiktok.py --mode multi-machine-feed-session reservation`), tiến trình này chiếm `device-locks/machine_N.lock.json` với owner active và TTL 1h.
Khi Operator / Coordinator cần can thiệp xử lý lỗi gấp (sửa account, đổi avatar, giải challenge, fix profile):
- Nếu chỉ dùng cron / watchdog chờ máy rảnh: Quá thụ động, có thể phải chờ 40–50 phút giữa ca, làm tê liệt khả năng xử lý sự cố.
- Nếu cho phép phá lock cưỡng chế (force-kill, đè lock): Rất nguy hiểm vì ADB không tự hiểu fencing token, dễ gây split-brain (hai tiến trình cùng gửi lệnh ADB lên cùng một máy), corrupt UI state, văng tài khoản hoặc hỏng phiên.

## Đồng thuận kiến trúc giữa Sol & Claude CLI (25/09/2026)
Không chọn cực đoan "chỉ chờ cron" và không chọn "phá lock cưỡng chế ngay". Áp dụng kiến trúc:
**Cooperative Preemption + Reservation (Pha 0) → Fenced Enforcement (Pha 2).**

### 1. Phân cấp ưu tiên (Priority Tiers)
- `P0 (Emergency / Recovery, Prio=100)`: Login recovery, manual challenge, giải cứu máy kẹt.
- `P1 (Maintenance Urgent, Prio=50)`: Đổi avatar, cập nhật profile khẩn cấp theo lệnh Operator.
- `P2 (Normal Workload, Prio=20)`: Nuôi feed, warmup, browsing định kỳ.
- `P3 (Background Maintenance, Prio=10)`: Dọn dẹp cache, scan guard, kiểm tra app rảnh.
- `HUMAN (Immutable)`: Operator đang cắm scrcpy hoặc tương tác tay. Tuyệt đối CẤM preempt và cấm reap theo TTL.

### 2. Giao thức Handoff hợp tác (Cooperative Protocol)
1. **Request**: Requester ghi yêu cầu vào lease record:
   `HANDOFF_REQUEST {req_id, device, expected_epoch, requester, priority, reason, soft_deadline=20s, hard_deadline=60s}`.
   Chỉ hợp lệ khi `priority_requester > priority_holder` và holder không phải `HUMAN`.
2. **Safe Point & Interruption Loop**: Tiến trình holder (feed loop) không được dùng `sleep()` dài liên tục (ví dụ `sleep(45)` xem video). Bắt buộc chia nhỏ thành các lát 1s và kiểm tra cờ `drain_requested` / `HANDOFF_REQUEST` sau mỗi lát và tại các điểm an toàn:
   - Giữa các video.
   - Trước và sau khi chuyển trang / navigation.
   - Trước khi thực hiện switch account.
   *(Cấm handoff khi đang ở vùng nhạy cảm: nhập mật khẩu/OTP, đang upload video/ảnh, đang lưu workbook).*
3. **Yield & Checkpoint**: Holder lưu tiến độ session vào checkpoint file atomic (chỉ lưu tiến độ data, không lưu UI), đóng app về HOME an toàn và thoát với exit code riêng (`EXIT_YIELD = 75`).
4. **Acquire & Resume Ticket**: Lock manager chuyển lock sang cho requester, đồng thời tạo một `RESUME_TICKET` ưu tiên cao để sau khi task khẩn hoàn tất, máy sẽ ưu tiên chạy tiếp phần thời gian còn lại của session cũ thay vì bị scheduler nhét việc khác vào.

### 3. Fencing Token & ADB Gate (Điều kiện bắt buộc trước khi mở Force Kill)
- Không được force-kill nếu chưa có **ADB Gate**: Mọi lệnh ADB / UIAutomator phải đi qua một wrapper kiểm tra `epoch` của lease hiện tại (`gate(device, epoch)`). Nếu epoch của tiến trình bị lệch, lệnh ADB bị chặn ngay lập tức.
- Quy trình cứu hộ cưỡng chế khi quá hard deadline (>60s holder không phản hồi):
  1. Tăng epoch trên Lock Manager để fence toàn bộ lệnh ADB của tiến trình cũ.
  2. Gửi stop mềm (SIGTERM / stop-file). Chờ 5s.
  3. `taskkill /T /F` theo PID, sau khi đối chiếu khớp cả `pid_create_time` (chống tái sử dụng PID trên Windows).
  4. Trên thiết bị: `am force-stop` package, kill uiautomator server.
  5. Screencap + OCR kiểm tra màn hình hiện tại. Nếu màn hình sạch -> bàn giao cho requester; nếu kẹt màn hình không xác định -> chuyển sang `QUARANTINE`.

### 4. Vai trò của Cron & Watchdog
- **Cron KHÔNG BAO GIỜ được tự ý acquire máy hay cướp lock**: Cron chỉ đóng vai trò enqueue task vào hàng đợi hoặc reap các lock chết.
- **Reap 2 pha an toàn**: Lock chỉ bị thu hồi khi thỏa mãn cả 2 điều kiện: PID đã chết (xác minh qua kernel handle / create_time) VÀ thời gian không có heartbeat vượt quá TTL. Trước khi reap, chuyển sang trạng thái `SUSPECT` trong 1 chu kỳ để tránh chạy đua với worker đang khởi động.

### 5. Lộ trình triển khai (Implementation Roadmap)
- **Pha 0 (MVP làm ngay)**:
  - Thêm trường `reservation` và cờ `drain_requested` vào lock JSON.
  - Sửa `run_tiktok.py` để chia nhỏ sleep và kiểm tra cờ ở safe point, thoát với exit 75.
  - Feed tự động nhả máy (`self-yield`) khi phát hiện văng login hoặc gặp challenge, không cần đợi request ngoài.
  - Task avatar/profile đặt reservation trước; khi feed kết thúc tự nhiên, scheduler trao thẳng máy cho task đặt chỗ.
- **Pha 1**: Xây dựng Lock Manager tập trung (SQLite WAL, atomic CAS trên `(device, epoch)`), heartbeat 5s, TTL 30s.
- **Pha 2**: Tích hợp ADB gate kiểm tra epoch và recovery cưỡng chế an toàn, kiểm thử chaos test trên 10 máy canary.
- **Pha 3**: Áp dụng chính sách priority toàn diện, rate limit (tối đa 2 lần preempt/máy/giờ) và rollout cho 160 máy.
