---
name: hermes-orchestration-dispatcher
description: "Hermes role in orchestration: spec writer + dispatcher, NEVER coder."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [orchestration, dispatch, codex, claude, workflow]
---

# Hermes Orchestration Dispatcher

## Quy tắc cứng

Khi user yêu cầu code/sửa code/implement và nói "dùng rule điều phối" (hoặc bất kỳ dấu hiệu nào cho thấy cần orchestration), Hermes TUYỆT ĐỐI KHÔNG tự viết code, không tự patch, không tự sửa file.

Hermes CHỈ làm:
1. Viết task spec rõ ràng (lưu vào tasks/*.md)
2. Dispatch Codex `codex exec` để implement
3. Dispatch Claude `claude -p` để review
4. Nếu Claude trả MINOR_FIXES/REJECT → dispatch Codex fix
5. Loop đến khi Claude APPROVED
6. Verify cuối cùng (chạy test, dry-run)

Hermes KHÔNG ĐƯỢC:
- Tự gọi `patch()` hoặc `write_file()` để sửa code
- Tự chạy `terminal()` để implement logic
- Tự "sửa nhanh" rồi dispatch review sau
- Nhảy qua bước spec để implement thẳng

## Trigger

Bất kỳ cụm nào sau đây từ user đều kích hoạt rule này:
- "dùng rule điều phối"
- "theo rule điều phối"
- "dispatch codex claude"
- "làm theo orchestrator"

## Pitfall

Lần trước Hermes đã tự ý viết plan rồi implement thẳng code (patch, write_file) khi user nói "dùng rule điều phối". User đã nhắc nhở nghiêm khắc. KHÔNG LẶP LẠI.
