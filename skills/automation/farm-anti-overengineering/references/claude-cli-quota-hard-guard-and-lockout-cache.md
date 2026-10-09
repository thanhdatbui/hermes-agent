# Claude CLI Quota Hard Guard & Lockout Cache Enforcement (Farm Guard)

## 1. Bối Cảnh Vi Phạm Quota (06/09/2026)
- **Quy định của User:** Claude CLI chỉ dùng cho ca khó hoặc khi user chỉ định; khi quota 5h đạt 85% hoặc weekly đạt 90% thì CẤM TUYỆT ĐỐI không được gọi.
- **Sự cố:** Agent sơ suất chạy lệnh `claude -p --model opus --effort max` nhồi prompt lớn mà không kiểm tra quota trước, đẩy tài khoản Claude Pro chạm trần 100% dẫn đến bị Anthropic khóa limit tới 16:40.
- **Phản ứng của User:** *"ơ mà claude cli t đã khoá chặt là nếu quota 5h đạt 85% thì k đc hỏi nữa mà???? sao vẫn vi phạm"*.
- **Nguyên nhân cốt lõi:**
  1. Quy tắc chỉ là "luật mềm" (soft prompt/memory), không có chốt chặn vật lý.
  2. Lệnh `claude auth status --text` trên tài khoản Claude Pro không hiển thị % quota phiên, khiến agent không có API đo đếm trực tiếp.

---

## 2. Kiến Trúc Chặn Cứng (Hard Intercept) Trong `farm-coordinator-guard`
Tư vấn bởi OmniRoute Review (`:20129`), cơ chế được đặt tại Tầng 0 của Action Guard (`_on_pre_tool_call`):

1. **Kiểm tra Lockout Cache (`claude_lockout.json`):**
   - Khi dính lỗi limit từ Anthropic (ví dụ: `You've hit your session limit · resets 4:40pm (Asia/Bangkok)`), ghi nhận timestamp `locked_until`.
   - Trong thời gian này, mọi lệnh chứa `\bclaude\b` bị `_check_claude_cli_guard(cmd)` chặn đứng vật lý (`action: "block"`), trả thông báo lỗi và ép fallback sang OmniRoute `:20129`.
2. **Kiểm tra Self-Tracking Usage (`claude_usage.json`):**
   - Đếm số lượt gọi trong cửa sổ 5h. Lệnh `opus` với `effort max` tính trọng số 4x.
   - Ngưỡng chặn: Chạm 38/45 cuộc gọi tương đương (~85%) là chặn đứng vật lý ngay.
3. **Zero Overhead & Không Vòng Lặp Vô Tận:**
   - Toàn bộ kiểm tra thực hiện qua File I/O (< 1ms). CẤM gọi subprocess `claude` trong hook để tránh kích hoạt lại hook gây infinite loop.

---

## 3. Quy Chuẩn Fallback Reviewer
- Review / Audit bình thường: Dùng combo OmniRoute Review (`:20129`) theo chuỗi `Opus -> Sonnet -> GPT OSS -> Nemotron -> AG`.
- Ca khó hoặc khi Claude CLI bị khóa / chạm 85%: Fallback ngay sang `auto/claude-opus` hoặc `review` trên OmniRoute `:20129`.
