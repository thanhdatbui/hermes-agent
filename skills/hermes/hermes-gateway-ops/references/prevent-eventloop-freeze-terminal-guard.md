# Phòng chống Đơ Event Loop Gateway & Hermes Agent do Terminal Lệnh Nặng

## 1. Hiện Tượng Thực Tế
- Dashboard OmniRoute và Gateway Telegram đứng im suốt 6–10 phút, không có bất kỳ request LLM nào được gửi đi.
- User gửi tin nhắn nhưng bot không phản hồi, Telegram webhook báo pending hoặc gateway coroutine bị nghẽn.
- Nguyên nhân: Coordinator hoặc Subagent chạy lệnh `terminal` foreground (`background=False` / omitted) không giới hạn timeout, chạm trần mặc định 600s (10 phút) của Hermes, khóa chặt Event Loop.

## 2. Các Lỗ Hổng & Bài Học Rút Ra

### A. Lệch Wire Protocol giữa Hermes Shell Hooks và Tool Input
- `shell_hooks.py` của Hermes Agent khi bắn sự kiện `pre_tool_call` truyền payload:
  ```json
  {
      "hook_event_name": "pre_tool_call",
      "tool_name": "terminal",
      "tool_input": {"command": "...", "timeout": ...},
      "session_id": "...",
      "cwd": "..."
  }
  ```
- **Pitfall**: Nếu hook viết `args = payload.get("args") or {}`, `args` sẽ luôn rỗng vì Hermes dùng key `"tool_input"`. Kết quả là `cmd = ""` và toàn bộ các rule regex kiểm tra lệnh quét đĩa (`os.walk`, `grep -r`, `rg`) bị vô hiệu hóa hoàn toàn!
- **Chuẩn hóa**: BẮT BUỘC đọc:
  ```python
  tool_name = payload.get("tool_name") or payload.get("tool") or ""
  args = payload.get("tool_input") or payload.get("args") or {}
  ```

### B. Lỗi Regex DANGEROUS_TARGETS có Dấu Kết Thúc Dòng `$`
- **Pitfall**: Regex `r"D:[\\/]Taadaa[\\/]?$"` có dấu `$` ở cuối khiến lệnh `python -c "import os; os.walk('D:/Taadaa')"` lọt lưới hoàn toàn, vì sau `'D:/Taadaa'` là dấu nháy đơn `'` chứ không phải kết thúc chuỗi.
- **Khắc phục**: Dùng pattern kiểm tra substring hoặc bóc tách target không phụ thuộc vào dấu `$`.

### C. Robust Parsing Timeout & Tránh Bỏ Lọt String
- **Pitfall**: Nếu chỉ kiểm tra `isinstance(to, (int, float)) and to > 60`, khi tham số truyền dạng chuỗi `"180"` hoặc `"600"`, điều kiện `isinstance` trả về `False` và lệnh bị bỏ lọt.
- **Khắc phục**:
  ```python
  if to is None:
      block("GUARD_FOREGROUND_TIMEOUT_MISSING", "Thiếu timeout...")
  else:
      try:
          to_val = float(to)
          if to_val > 60:
              block("GUARD_FOREGROUND_TIMEOUT_EXCEEDED", f"Timeout {to_val}s > 60s...")
      except (ValueError, TypeError):
          block("GUARD_FOREGROUND_TIMEOUT_INVALID", f"Timeout '{to}' không hợp lệ...")
  ```

### D. Kỷ Luật Terminal Foreground vs Background
- **Foreground (Luồng chat chính)**:
  - Chỉ dành cho lệnh inspect O(1) tức thời (< 30s).
  - BẮT BUỘC clamp cứng bằng hook: `timeout <= 60s`.
  - Thiếu `timeout` $\rightarrow$ Block ngay (`GUARD_FOREGROUND_TIMEOUT_MISSING`).
  - `timeout > 60s` $\rightarrow$ Block ngay (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`).
- **Background (Tác vụ nặng)**:
  - BẮT BUỘC dùng cho: pytest, ADB batch farm, build, render/download video, GPM login automation.
  - Cú pháp: `terminal(command=..., background=True, notify_on_complete=True)`.
  - Không bao giờ khóa Event Loop; bot trả lời người dùng ngay lập tức và bắn kết quả khi tiến trình kết thúc.

### E. Telemetry & Audit Observability
- Mọi quyết định block của hook phải được append vào `D:/Taadaa/runtime/audit_logs/guard_scan_audit.jsonl` để theo dõi và kiểm toán độc lập.

### F. Cấu Hình Timeout Subagent (`delegation`) & Worker Model Fallback
- Tránh đặt `child_timeout_seconds` quá dài (như 1200s / 20 phút) khiến worker bị kẹt mạng ngâm slot làm nghẽn scheduler.
- Thiết lập mức trần tối ưu:
  ```yaml
  delegation:
    child_timeout_seconds: 480  # 8 phút Fail-Fast
  ```
- **Xử lý Worker Stale/Timeout 480s**: Khi subagent chạy `codex/gpt-5.6-luna-high` bị nghẽn API qua proxy OmniRoute và chạm trần 480s: Coordinator chuyển ngay sang worker model `ag-gemini-pool-3` qua lệnh:
  ```bash
  hermes config set delegation.model ag-gemini-pool-3
  ```
  để worker hoàn thành task patch/test O(1) chỉ trong 2-3 phút, giải phóng tắc nghẽn tức thời.
