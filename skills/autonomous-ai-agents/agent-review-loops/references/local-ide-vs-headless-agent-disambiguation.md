# Local IDE vs Headless Coding Agent Disambiguation (Antigravity & Third-Party CLIs)

## 1. Phân loại hình thức tích hợp khi user yêu cầu gọi agent bên thứ 3

Khi người dùng yêu cầu: "Gọi Antigravity/OpenCode/Claude sửa đi như claude -p", điều phối viên tuyệt đối KHÔNG được đánh đồng giữa 3 hình thức:

1. **Headless Coding CLI (như `claude -p "..."` hoặc `opencode run "..."`)**:
   - Chạy trực tiếp từ shell, nhận prompt qua CLI argument hoặc stdin.
   - Trả kết quả, diff, stdout/stderr trực tiếp về caller.
   - Thích hợp cho automation, subagent delegation, background process.

2. **IDE CLI Launcher (như `antigravity-ide.cmd chat`)**:
   - Launcher của ứng dụng IDE (như Antigravity IDE based on VS Code: `C:\Users\Kibe\AppData\Local\Programs\Antigravity IDE\bin\antigravity-ide.cmd`).
   - Lệnh `chat` (`-m ask`, `-m edit`, `-m agent`) gửi prompt vào cửa sổ giao diện GUI đang mở, KHÔNG trả stream stdout/JSON headless ra shell.
   - Không thể dùng thay thế trực tiếp cho `claude -p` nếu chưa có adapter bắt output/diff hoặc bridge qua CDP (`127.0.0.1:60450`).

3. **HTTP Model Pool (như OmniRoute `:20129` `ag-opus`, `ag-sonnet`, `ag-gemini-pool-3`)**:
   - Chỉ là API endpoint cung cấp weights/completions của model, hoàn toàn không phải app/agent CLI cục bộ.
   - Tuyệt đối KHÔNG lái việc gọi App/IDE cục bộ sang model pool khi chưa có chỉ đạo của user.

## 2. Quy trình xác thực trước khi kết luận trạng thái

- Kiểm tra binary CLI và subcommand thật: `--help`, `--version`.
- Nếu công cụ chỉ hỗ trợ GUI chat, báo cáo trung thực ranh giới adapter và sự khác biệt với `claude -p`.
- Không tự ý giải thích lan man sang các model pool không liên quan.
