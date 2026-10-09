# Wire Protocol & Hard Clamp Foreground Timeout Chống Nghẽn Event Loop (Incident 28/09/2026)

## 1. Hiện tượng & Triệu chứng
- **Hiện tượng**: User nhắn tin trên Telegram nhưng Hermes không phản hồi suốt 6–10 phút, Dashboard OmniRoute/9Router hoàn toàn vắng bóng request LLM.
- **Log thực tế (`errors.log`)**:
  ```text
  2026-09-28 00:10:16,184 WARNING [20260927_152650_8450126a] agent.tool_executor: 
  Tool terminal returned error (602.91s): {"output": "[Command timed out after 600s]", "exit_code": 124, "error": null}
  ```
- **Lệnh gây nghẽn**: Coordinator trong session chat chính chạy lệnh Python `os.walk('D:/Taadaa')` ở chế độ foreground và không truyền tham số `timeout` $\rightarrow$ Hermes dùng default timeout 600s $\rightarrow$ block cứng tiến trình 602.91s.

---

## 2. Phân tích Nguyên nhân Gốc rễ

### A. Bản fix "bằng mồm" trong Prompt hoàn toàn vô tác dụng
- Ở các phiên trước, quy định "chỉ chạy lệnh <= 60s" chỉ được ghi vào system prompt / SOUL.
- Khi gặp tình huống tìm file gấp, agent vẫn tự ý viết lệnh `os.walk` hoặc chạy tool foreground không set timeout. Prompt không có năng lực tự bảo vệ nếu thiếu phanh cứng bằng code.

### B. Tử huyệt Wire Protocol Mismatch trong `shell_hooks.py`
- Hermes core (`agent/shell_hooks.py`) khi bắn sự kiện hook `pre_tool_call` truyền payload qua `stdin`:
  ```json
  {
      "hook_event_name": "pre_tool_call",
      "tool_name": "terminal",
      "tool_input": {
          "command": "python -c \"...\"",
          "timeout": 120
      },
      "session_id": "sess_123",
      "cwd": "C:/Users/Kibe"
  }
  ```
- **Lỗi ngầm**: Script hook cũ (`guard_broad_grep.py`) đọc:
  ```python
  tool_name = payload.get("tool") or payload.get("tool_name") or ""
  args = payload.get("args") or {}  # ❌ SAI! Hermes truyền 'tool_input', KHÔNG PHẢI 'args'
  cmd = args.get("command") or ""   # cmd LUÔN RỖNG ("")
  ```
- Vì `cmd == ""`, toàn bộ các regex quét đĩa (`PYTHON_SCAN`, `RECURSIVE_GREP`, `RG_SCAN`) đều trả về `None`. Hook hoàn toàn "bị điếc", mọi lệnh quét diện rộng đều lọt lưới 100%!

---

## 3. Giải pháp Hard Clamp Toàn Diện

### A. Chuẩn hóa đọc Payload
```python
tool_name = payload.get("tool_name") or payload.get("tool") or ""
args = payload.get("tool_input") or payload.get("args") or {}
```

### B. Ép Kỷ luật Foreground Timeout bằng Code
Bất kỳ lệnh `terminal` foreground nào (`not args.get("background")`):
1. **Thiếu timeout**:
   ```python
   if args.get("timeout") is None:
       block("GUARD_FOREGROUND_TIMEOUT_MISSING", "Lệnh terminal foreground thiếu timeout! Bắt buộc timeout <= 60s hoặc chạy background=True.")
   ```
2. **Timeout vượt quá 60s**:
   ```python
   to = args.get("timeout")
   if isinstance(to, (int, float)) and to > 60:
       block("GUARD_FOREGROUND_TIMEOUT_EXCEEDED", f"Lệnh terminal foreground có timeout={to}s > 60s! Hãy hạ timeout <= 60s hoặc dùng background=True.")
   ```

### C. Cơ chế phân tách Foreground vs Background
- **Foreground (`background=False` / omitted)**: Chỉ dành cho các lệnh tra cứu nhanh O(1) < 60s (`ls`, `git status`, `inspect_machine.py`, `curl health`).
- **Background (`background=True`, `notify_on_complete=True`)**: Dành cho mọi tác vụ nặng (>60s) như chạy test suite (`pytest`), batch farm, đăng nhập Hotmail/GPM, download/render video. Luồng chat Telegram lập tức được giải phóng, khi tiến trình nền xong hệ thống tự động bắn notify trả kết quả.
