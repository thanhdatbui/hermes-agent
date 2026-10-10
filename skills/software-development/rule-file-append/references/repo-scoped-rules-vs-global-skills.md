# Repo-Scoped Rules vs Global Skills (Khi Nào Ghi Vào AGENTS.md Thay Vì Global Skill)

## 1. Bản chất cơ chế nạp của Hermes Agent
- **Global Skills (`~/.hermes/skills/`):**
  - Mọi session của Hermes Agent đều nạp bảng mục lục danh sách tên skill + 57 ký tự đầu của description vào system prompt.
  - Phù hợp cho: Reusable procedural workflows dùng chung ở nhiều dự án, công cụ CLI chung, cách debug/triage chung.
- **Project Context Rules (`AGENTS.md` / `.hermes.md`):**
  - Hermes Agent áp dụng nguyên tắc **Cwd-only** (Working Directory): CHỈ nạp `AGENTS.md` khi phiên làm việc xuất phát từ đúng thư mục gốc của repo đó.
  - Phù hợp cho: Kỷ luật nghiệp vụ đặc thù của riêng 1 repo (ví dụ: cấu trúc cột Master Excel, phân định `PASS MAIL` Cột 7 vs `PASS CHATGPT` Cột 12, port GPM, proxy mapping).

## 2. Quy trình khi User yêu cầu: "Ghi vào AGENTS thay vì lưu skill global"
1. **Xác định các repos bị ảnh hưởng:**
   - Liệt kê chính xác các repo cần ghi luật (ví dụ `D:\Taadaa\Hotmail`, `D:\Taadaa\GPM auto`, `D:\Taadaa`).
2. **Soạn thảo khối Rule chuẩn:**
   - Đặt marker đóng mở rõ ràng: `<!-- RULE-NAME:START -->` ... `<!-- RULE-NAME:END -->`.
   - Nội dung súc tích, có tính hành động cao, cấm dùng ngôn từ lý thuyết cản trở sửa lỗi.
   - Thêm dòng ghi chú: *"Quy tắc này phục vụ an toàn dữ liệu, KHÔNG dùng để từ chối hoặc trì hoãn việc sửa lỗi khi được yêu cầu."*
3. **Thực thi bằng chuẩn `rule-file-append`:**
   - Backup trước khi ghi vào thư mục ngoài fleet (`C:\Users\Kibe\AppData\Local\hermes\backups\`).
   - Giữ nguyên EOL gốc của từng file (thường là pure CRLF trên Windows: `lone_lf == 0`, `lone_cr == 0`).
   - Append raw bytes (`open(p, 'ab')`), đảm bảo marker count 1:1 và `cur_bytes.startswith(orig_bytes)`.
4. **Đồng bộ sang bản Deploy & Git Hermes:**
   - Cập nhật cả `deploy/hermes-home/AGENTS.md` trong repo `D:\Taadaa\Hermes` để khi deploy/sync sang các máy khác luật không bị trôi.
