# Claude Code CLI 5-Hour Session Limit & Lockout Handling

Tài liệu này ghi nhận hiện tượng thực tế và quy trình xử lý chuẩn khi Claude Code CLI chạm trần giới hạn phiên 5 giờ của Anthropic.

---

## 1. Dấu hiệu nhận biết & Error Signature
Khi chạy `claude -p --model opus --effort high "..."` quá nhiều lần liên tiếp trong cửa sổ 5 giờ với prompt dài (đặc biệt khi phản biện audit mã nguồn đa vòng), Anthropic API sẽ ngắt và trả về stdout/stderr:

```
You've hit your session limit · resets 2:40pm (Asia/Bangkok)
```
- Mã thoát (`exit_code`): `1`
- Nội dung lỗi chứa chuỗi khóa: `You've hit your session limit · resets`

---

## 2. Quy trình xử lý tự động (Auto-Fallback)

1. **Ghi nhận Lockout Cache (`claude_lockout.json`):**
   - Trích xuất thời gian mở khóa từ regex: `resets\s+([0-9:apmAPM]+)\s+\(([^)]+)\)`
   - Chuyển đổi thành epoch timestamp và lưu vào `C:/Users/Kibe/AppData/Local/hermes/claude_lockout.json`:
     ```json
     {
       "locked_until": 1725781200,
       "reset_display": "2:40pm (Asia/Bangkok)",
       "reason": "session_limit_hit",
       "recorded_at": 1725763200
     }
     ```

2. **Cưỡng chế ngắt gọi Claude CLI lập tức:**
   - Plugin `farm-coordinator-guard` kiểm tra file cache này tại `_on_pre_tool_call`.
   - Nếu `locked_until > now`: Chặn đứng mọi lệnh gọi terminal chứa `claude` (<1ms), không để tiến trình tiếp tục chạy gây tốn CPU hoặc delay 180s timeout.

3. **Fallback mượt mà sang OmniRoute (:20129):**
   - Không dừng toàn bộ công việc lại chờ Claude hồi phục.
   - Lập tức định tuyến các tác vụ review / audit còn lại sang endpoint OmniRoute `:20129`:
     + Model: `review` (chuỗi ưu tiên: Opus 4.6 Thinking -> Sonnet 4.6 -> GPT OSS 120B -> Nemotron 3 Ultra -> AG Pool).
   - Tiếp tục hoàn thành quy trình chốt phiên và release bình thường.
