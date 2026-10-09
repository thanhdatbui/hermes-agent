# Chẩn đoán & Khắc phục: Event Loop Saturation do Subagent 600s Timeout Cascade + Semaphore Queue Overload (2026-09-25 Incident)

## 1. Bối cảnh & Triệu chứng thực tế
- **Thời gian xảy ra**: 13:56:13 – 14:03:54 (Ngày 25/09/2026).
- **Hiện tượng quan sát**:
  - Dashboard OmniRoute (:20129) hoàn toàn trống trơn, không có request nào từ 13:57:09 đến 14:03:54 (~6 phút).
  - Ngay sau đó (14:04 – 14:15), hệ thống xả dồn 173 requests liên tục.
  - Các tin nhắn Telegram từ User gửi lúc 14:03 dồn ập về trong cùng 1-2 giây (`14:03:54.956`, `14:03:55.581`, `14:04:02.090`).
  - Log Gateway xuất hiện cảnh báo nghiêm trọng: `Job 'e95493820697': live adapter send to telegram:... timed out before the coroutine was dispatched, falling back to standalone`.

---

## 2. Phân tích Nguyên nhân Cốt lõi (2 Đầu Nghẽn)

### A. Đầu Hermes Gateway: Event Loop Saturation do Subagent ngâm 600s & Terminal Blocking
1. **Trần ngâm `child_timeout_seconds: 600` (10 phút) quá rộng**:
   - Hai subagent worker chạy lệnh tool nặng bị đơ hoặc kẹt mạng, ngâm trọn 600 giây mới bị hủy:
     - `13:59:41,197 WARNING tools.delegate_tool: Subagent 0 timed out after 600.1s`
     - `14:04:35,653 WARNING tools.delegate_tool: Subagent 0 timed out after 600.1s`
   - Suốt 10 phút này, subagent giữ cứng các slot trong `max_concurrent_children: 8`, đồng thời chiếm tài nguyên async của Gateway.
2. **Terminal tool blocking 180s trên Main Thread**:
   - Session `20260925_132435` chạy lệnh terminal foreground chạm trần:
     `13:56:36,569 WARNING agent.tool_executor: Tool terminal returned error (183.08s): [Command timed out after 180s]`.
   - Lệnh blocking lâu khiến Main Event Loop bị chậm nhịp, làm trễ quá trình dispatch coroutine mới (thể hiện rõ ở việc cron job không kịp dispatch coroutine gửi tin nhắn).

### B. Đầu OmniRoute: Semaphore Queue Congestion trên `ag-gemini-pool-3`
- Khi các session đồng loạt thoát khỏi trạng thái chờ và gửi request LLM (nhiều payload nặng 100k–280k tokens):
  - 16 accounts trong pool `ag-gemini-pool-3` bị cạnh tranh slot gay gắt.
  - Request phải xếp hàng chờ slot tài khoản quá 30 giây $\rightarrow$ văng mã lỗi:
    `Semaphore timeout after 30000ms for antigravity:...` $\rightarrow$ sinh HTTP 429 nội bộ.

---

## 3. Giải pháp Nâng trần Chịu đựng (Dual-Head Hardening)

### Bước 1: Nâng sức chứa Concurrent Heavy Requests trên OmniRoute
- Thêm vào `C:/Users/Kibe/OmniRoute/.env`:
  ```bash
  OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT=24
  ```
- *Cơ sở*: Máy host có 64GB RAM và CPU đa nhân, hoàn toàn đủ sức chứa 24 heavy in-flight requests (50k-250k tokens) đồng thời thay vì bị bóp ở trần mặc định (9).

### Bước 2: Hạ trần Timeout Subagent trên Hermes — Cảnh báo bẫy False-Kill & Cấu hình Sweet Spot (27/09/2026 Audit)
- **CẢNH BÁO BẪY 180s**: Không được hạ trần cứng tổng xuống 180s. Subagent coding/debug có test hoặc flow farm (TikTok login, OTP, upload) thực tế chạy 8-15 tool calls mất 3-8 phút. Hạ trần tổng xuống 180s sẽ gây False-kill hàng loạt:
  1. Trạng thái dở dang trên thiết bị Android (kẹt giữa chừng màn hình login/upload).
  2. Tiến trình con mồ côi (`adb.exe`, python) không bị kill theo, giữ lock máy.
  3. Coordinator retry gây trùng thao tác (đăng video 2 lần, reg trùng -> ban tài khoản).
- **Cấu hình chuẩn (Sweet Spot)**:
  ```bash
  hermes config set delegation.child_timeout_seconds 480
  ```
  *Mục tiêu*: Đặt trần tổng 480s (8 phút), đủ 100% thời gian cho các flow farm nặng nhất hoàn tất an toàn, nhưng giải phóng ngay sau 8 phút nếu worker deadlock (thay vì ngâm 20 phút / 1200s). Con số 180s chỉ thích hợp cho *silence timeout* (không có tool call mới trong 180s).

### Bước 3: Kỷ luật Foreground Terminal của Coordinator (Chặn Đứng Gốc Rễ Đơ Bot)
- **Clamp cứng timeout foreground**: Mọi lệnh terminal foreground trên session chat trực tiếp chỉ được đặt `timeout <= 60s`. Tuyệt đối không để lệnh ngâm 180s - 600s block main thread.
- Tác vụ nặng (>30s như ADB suite, pytest full repo, batch download) BẮT BUỘC:
  - Chạy `background=True` kèm `notify_on_complete=True`.
  - Script Python chạy nền bắt buộc có cờ `python -u` hoặc `PYTHONUNBUFFERED=1` (tránh block buffering).
  - Redirect output ra file log để tránh đầy Windows pipe buffer (4-64KB) làm treo process nền.
  - Không chạy bão lệnh ADB nền song song gây crash `adb.exe` server trên Windows.

### Bước 4: Kiểm Chứng Hiện Trường & Chẩn Đoán Đa Tiến Trình ADB (Claude CLI Consensus)
- **Rà soát xung đột ADB**: Khi thấy 2+ tiến trình `adb.exe` trong `tasklist`, chạy ngay:
  `powershell.exe -NoProfile -Command "Get-Process adb | Select-Object Id, Path, StartTime"`
  Nếu tất cả PID cùng trỏ về 1 binary (ví dụ: `C:\Program Files (x86)\xiaowei\tools\adb.exe`) thì là các daemon phân cụm của phần mềm quản lý dàn máy Xiaowei, không phải xung đột phiên bản. Nếu khác binary, bắt buộc thống nhất về 1 binary duy nhất để tránh tự kill nhau theo chu kỳ.
- **Canary Test Chạy Nền**: Luôn kiểm chứng cơ chế background qua 2 kịch bản:
  1. *Success case*: `python -u -c "import time; time.sleep(3); print('done')"` -> kiểm tra bắt được notify `exit_code: 0`.
  2. *Failure case*: `python -u -c "import sys; sys.exit(1)"` -> kiểm tra bắt được notify `exit_code: 1` và log lỗi, không bị nuốt thông báo.
