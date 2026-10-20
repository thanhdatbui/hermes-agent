# Worker Timeout Governance & False Diagnosis Pitfall (20/10/2026)

## 1. Sự Cố Hiện Trường & Lời Chấn Chỉnh của Operator

Trong phiên điều phối ngày 20/10/2026, Operator đã chấn chỉnh gay gắt Coordinator:
> *"File agent lớn là sao, làm gì có chuyện do file agent mà làm lâu timeout. Ai cho phép mày để timeout 180s t nhớ hqua benchmark t đã tăng timeout r mà. Chỉnh timeout tất cả worker nâng lên."*

### Hiện Tượng Thực Tế:
- Coordinator giao tác vụ sửa code cho Antigravity CLI pool (`ag_cli.py fix`).
- Tiến trình chạy đúng 180 giây thì bị ngắt, file log `pool_state.json` ghi nhận:
  `"reason": "TimeoutExpired (180s)", "cooldown_until": 1792449106, "cooldown_seconds": 1200`.
- Toàn bộ 22 profiles trong pool (`acc_01` -> `acc_22`) lần lượt bị timeout 180s rồi bị đưa hết vào trạng thái `COOLDOWN` 20 phút. Toàn bộ pool bị khóa đứng.
- Khi điều tra, Coordinator nhìn thấy dòng thông báo trong log:
  `Rule file AGENTS.md truncated by 118233 bytes`
  và vội vàng kết luận chủ quan: *"Do file AGENTS.md quá lớn làm lag API và treo timeout"*.

---

## 2. Phân Tích Nguyên Nhân Cốt Lõi (Root Cause Analysis)

### 2.1. Bẫy Chẩn Đoán Sai (False Diagnosis)
- Kiểm tra log nội bộ tại `D:\Taadaa\agy_profiles\acc_01\.gemini\antigravity-cli\cli.log` cho thấy:
  Tiến trình Antigravity CLI vẫn đang kết nối mạng và stream token (`streamGenerateContent`) liên tục qua các turn:
  `05:08:51 -> 05:09:17 -> 05:09:48 -> 05:10:07 -> 05:10:27 -> 05:11:09 -> 05:11:42`.
- Mô hình Gemini Code Assist hoàn toàn không bị đơ, không bị treo, và việc truncate file `AGENTS.md` là hành vi cắt context mặc định an toàn của CLI, không hề ảnh hưởng đến khả năng sinh token.
- Nguyên nhân duy nhất khiến tiến trình dừng lại là do **Caller (Coordinator) áp timeout quá ngắn (180s)**. Khi đồng hồ chạm 180s, `subprocess.Popen` của caller cưỡng chế gửi lệnh `taskkill /F /T` giết chết tiến trình worker đang streaming dở dang.

### 2.2. Dây Chuyền Cooldown Gây Tê Liệt Toàn Pool
- Trong `ag_cli.py`, hàm điều phối pool bắt ngoại lệ `subprocess.TimeoutExpired`:
  ```python
  except subprocess.TimeoutExpired:
      logger.warning("Profile %s timeout sau %ds", profile_name, timeout)
      mark_cooldown(profile_name, seconds=1200, reason=f"TimeoutExpired ({timeout}s)")
  ```
- Khi Coordinator gọi `dispatch_worker.py` hoặc `ag_cli.py` với cờ `--timeout 180`, caller đã đè (override) cấu hình chuẩn của Operator (vốn đã nâng lên 1200s–1500s sau benchmark).
- Hậu quả: Khi profile 1 dính timeout 180s -> bị phạt 1200s cooldown -> failover sang profile 2 -> profile 2 tiếp tục dính timeout 180s -> phạt 1200s... Cứ thế cả 22 profile đều dính án phạt cooldown, khiến cả hệ thống rơi vào trạng thái tê liệt hoàn toàn.

---

## 3. Quy Chuẩn Timeout Toàn Farm (1200s Standard)

Đã cơ giới hóa và đồng bộ trần timeout chuẩn trên toàn bộ hệ sinh thái công cụ:

| Công Cụ | File Nguồn | Tham Số | Giá Trị Cũ | Giá Trị Chuẩn Hóa |
|---|---|---|---|---|
| Single Dispatch Gateway | `D:/Taadaa/tools/dispatch_worker.py` | `--timeout` default | 180s | **1200s (20 phút)** |
| Claude Worker CLI | `D:/Taadaa/tools/claude_worker.py` | `default_timeout` (all roles) | 180s | **1200s (20 phút)** |
| Haiku Worker CLI | `D:/Taadaa/tools/haiku_worker.py` | `DEFAULT_TIMEOUT` | 180s | **1200s (20 phút)** |
| Sol Worker ReAct | `D:/Taadaa/tools/sol_worker.py` | `DEFAULT_TIMEOUT_PER_TURN` | 90s | **300s (5 phút/turn)** |
| Antigravity CLI Ask | `D:/Taadaa/tools/ag_cli.py` | `ask` `--timeout` | 1200s | **1200s (20 phút)** |
| Antigravity CLI Fix | `D:/Taadaa/tools/ag_cli.py` | `fix` `--timeout` | 1500s | **1500s (25 phút)** |

---

## 4. Quy Trình Khôi Phục Nhanh Khi Pool Dính Cooldown Hàng Loạt

Khi pool bị phạt cooldown nhầm do lỗi timeout caller, thực hiện giải tỏa tức thì cho cả 22 profiles qua file state:
1. Đọc file `D:/Taadaa/agy_profiles/pool_state.json`.
2. Đặt lại `cooldown_until: 0`, `cooldown_seconds: 0`, `reason: ""` cho toàn bộ profiles.
3. Ghi lại file bằng `write_file` (hoặc script Python chuyên dụng).
4. Kiểm tra trạng thái bằng lệnh allowlisted:
   `python D:/Taadaa/tools/ag_cli.py pool-status`
   Xác nhận toàn bộ 22/22 profiles hiển thị `READY`.

---

## 5. Quy Tắc Ứng Xử Bất Biến Cho Coordinator

1. **CẤM ĐỔ LỖI MÙ CHO FILE AGENT / REPO:** Trước khi phán đoán lý do lỗi, bắt buộc đọc log thực tế (`cli.log`, `dispatch.jsonl`, traceback) để xác minh xem tiến trình có đang streaming hay không.
2. **CẤM TỰ Ý HẠ TIMEOUT DƯỚI 1200s:** Mọi lệnh gọi worker (Haiku, Claude, Agy) bắt buộc để timeout mặc định 1200s. Tuyệt đối không truyền `--timeout 180` hay `--timeout 60` vào dòng lệnh.
3. **CẤM SỬ DỤNG `delegate_task` CHO TÁC VỤ SỬA CODE:** Mọi việc sửa code và unit test bắt buộc dispatch qua `dispatch_worker.py` để chạy CLI độc lập, không dùng subagent Gemini trong session chính.
