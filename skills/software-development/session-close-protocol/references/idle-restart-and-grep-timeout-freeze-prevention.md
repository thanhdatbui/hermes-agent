# Bài Học Chống Treo Phiên 4 Tiếng: Grep Timeout 900s & Idle Restart Gateway Kill Trap (06/09/2026)

## 1. Hiện tượng sự cố thực tế
- Người dùng gửi lệnh `chốt phiên` lúc 17:03.
- Bot Telegram hiển thị trạng thái streaming:
  `⏳ Working — 21 min — iteration 22/200, waiting for provider response (streaming)`
  và bị treo cứng liên tục hơn 3 tiếng rưỡi (từ 17:03 đến 21:00) mà không có bất kỳ phản hồi hay cập nhật nào.

## 2. Phân tích nguyên nhân gốc rễ (Root Cause Chain)

### A. Kẹt lệnh I/O đĩa diện rộng (Grep Timeout 900s)
- **Hành vi sai lầm:** Coordinator tự ý gọi lệnh `grep -rn "budget" "D:/Taadaa/tiktok-luot nuoi acc/python_runner"` trực tiếp trong terminal ở session chính.
- **Hậu quả:** Thư mục chứa lượng lớn file và runtime, I/O filesystem Windows bị nghẽn làm lệnh chạy trọn vẹn 900 giây (15 phút) mới bị hệ thống ngắt bởi timeout (`exit_code 124`). Điều này làm iteration 22 bị đội thời gian xử lý lên 21 phút.

### B. Bẫy tiến trình nền kill Gateway (`restart-when-idle.ps1`)
- **Hành vi ngầm:** Một tiến trình PowerShell nền `restart-when-idle.ps1` (PID: 221048) được kích hoạt từ 16:28 với nhiệm vụ "restart gateway khi idle 12s".
- **Hậu quả chết người:** Lúc 17:28:41, trong khi Coordinator đang chuẩn bị chạy test suite ở Gate 2, tiến trình watcher kiểm tra `gateway_state.json` thấy `active_agents = 0` liên tục trong 12 giây nên đã lập tức **ra lệnh kill tiến trình Hermes Gateway để restart**.
- **Tác động:**
  1. Tiến trình Gateway bị terminated đột ngột, turn xử lý bị biến thành mồ côi (`Orphan recovery`).
  2. Tin nhắn streaming của Telegram không được nhận hook kết thúc, bị đóng băng vĩnh viễn với dòng chữ `⏳ Working — 21 min...`.
  3. Toàn bộ phiên giao tiếp bị đứt gãy, người dùng nhìn thấy bot treo suốt 4 tiếng mà không biết lý do.

## 3. Quy tắc phòng ngừa bắt buộc (Invariants)
1. **Tuyệt đối tuân thủ INVARIANT TAADAA FARM SAFETY:**
   - CẤM chạy `grep -rn`, `find`, `os.walk`, `glob(recursive=True)` quét đĩa diện rộng ở session chính. Mọi việc rà soát code diện rộng bắt buộc phải delegate cho Worker Subagent trong context riêng hoặc dùng `search_files` có giới hạn chặt chẽ.
2. **Quản lý an toàn các script restart gateway ngầm:**
   - Khi đang trong phiên làm việc hoặc khi nhận lệnh `chốt phiên`, BẮT BUỘC kiểm tra và diệt sạch các tiến trình `restart-when-idle.ps1` hoặc watcher restart ngầm (`tasklist | grep -i restart`).
   - Tuyệt đối không để watcher tự động kill gateway khi người dùng đang chờ phản hồi.
