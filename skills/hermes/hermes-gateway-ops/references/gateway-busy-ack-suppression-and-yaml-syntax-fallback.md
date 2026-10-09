# Gateway Busy Ack Suppression & YAML Syntax Fallback Prevention

## 1. Hiện tượng & Phản hồi từ User
Người dùng nhắn tin vào Telegram trong lúc bot đang bận xử lý hoặc chạy dở lệnh, bot bắn ra thông báo:
```text
⚡ Interrupting current task. I'll respond to your message shortly.

💡 First-time tip — I just interrupted my current task to answer you. Send /busy queue to queue follow-ups for after the current task instead, /busy steer to inject them mid-run without interrupting, or /busy status to check. This notice won't appear again.
```
Người dùng phản ánh bức xúc: *"Bỏ cái dòng xàm lồn này dùm vs trc đây đâu có bị"*.

## 2. Nguyên nhân gốc rễ (Root Cause)
Có 2 nguyên nhân cốt lõi dẫn đến việc thông báo này bất ngờ xuất hiện:

1. **Lỗi cú pháp YAML trong `config.yaml` khiến Gateway rơi vào Default Fallback:**
   - Khi chỉnh sửa system prompt hoặc personality trong `config.yaml`, nếu chuỗi văn bản không được bọc trong dấu nháy (`'...'` hoặc `>-`) mà chứa dấu hai chấm kèm khoảng trắng (ví dụ: `mỗi bước quan trọng. MỌI task đụng tới máy N: Báo cáo kết quả...`), trình phân tích PyYAML sẽ coi `Báo cáo kết quả...` là một mapping value không hợp lệ (`yaml.scanner.ScannerError: mapping values are not allowed here`).
   - Lệnh `hermes config check` sẽ cảnh báo:
     ```text
     ⚠️ hermes config: Failed to parse config.yaml: mapping values are not allowed in this context...
     Falling back to default config — every user override is being IGNORED. Fix the YAML and restart.
     ```
   - Khi fallback về default config:
     - Toàn bộ tùy chọn cá nhân hóa, model overrides và cờ onboarding đã lưu bị Hermes bỏ qua.
     - Hermes Gateway kích hoạt hành vi mặc định: `busy_input_mode: interrupt` và coi đây là "lần đầu tiên" gặp trạng thái busy (`is_seen == False`), do đó tự động chèn thông báo onboarding tip vào chat.

2. **Cơ chế Busy Input Acknowledgment trong `gateway/run.py`:**
   - Tại dòng ~5708 của `gateway/run.py`, mỗi khi user gửi tin nhắn ngắt (`interrupt`), Gateway mặc định chuẩn bị nội dung:
     `⚡ Interrupting current task. I'll respond to your message shortly.`
   - Tại dòng ~5611 của `gateway/run.py`, Gateway có kiểm tra cờ tắt:
     ```python
     busy_ack_enabled = os.environ.get("HERMES_GATEWAY_BUSY_ACK_ENABLED", "true").lower() == "true"
     if not busy_ack_enabled:
         logger.debug("Busy ack suppressed for session %s", session_key)
         return True  # input still processed, just no ack sent
     ```
   - Và tại dòng ~1634, Gateway nạp giá trị từ cấu hình `display.busy_ack_enabled` trong `config.yaml`:
     ```python
     if "busy_ack_enabled" in _display_cfg:
         os.environ["HERMES_GATEWAY_BUSY_ACK_ENABLED"] = str(_display_cfg["busy_ack_enabled"])
     ```

## 3. Quy trình khắc phục triệt để (Standard Fix)

### Bước 1: Sửa lỗi cú pháp YAML trong `config.yaml`
- Luôn bọc nháy đơn `'...'` hoặc dùng folded block scalar `>-` cho các chuỗi prompt nhiều dòng có chứa ký tự `:`, `-`, `#`, `[`, `{`.
- Chạy kiểm tra bắt buộc:
  ```bash
  hermes config check
  ```
  Xác nhận không còn dòng cảnh báo `Failed to parse config.yaml` hay `Falling back to default config`.

### Bước 2: Khóa cứng tắt thông báo ngắt (`busy_ack_enabled: false`)
Cập nhật đồng thời ở 2 tầng cấu hình:
1. **Trong `config.yaml`:**
   Thêm `busy_ack_enabled: false` vào khối `display:`:
   ```yaml
   display:
     busy_ack_enabled: false
     busy_input_mode: interrupt
     ...
   ```
2. **Trong `.env`:**
   Thêm biến môi trường:
   ```bash
   HERMES_GATEWAY_BUSY_ACK_ENABLED=false
   ```

### Bước 3: Đồng bộ vào repo Hermes Deploy
Đồng bộ cả hai file sửa đổi vào repo quản trị để khi deploy sang máy khác (như máy Admin) không bị tái diễn:
- `D:\Taadaa\Hermes\deploy\hermes-home\config.yaml`
- `D:\Taadaa\Hermes\deploy\hermes-home\.env`

## 4. Kết quả sau khi áp dụng
- Khi người dùng gửi tin nhắn trong lúc bot đang bận, Gateway âm thầm ngắt tiến trình cũ và phản hồi ngay câu hỏi mới.
- Tuyệt đối không gửi tin nhắn ack `⚡ Interrupting current task...` hay tip `/busy` vào cuộc trò chuyện.
