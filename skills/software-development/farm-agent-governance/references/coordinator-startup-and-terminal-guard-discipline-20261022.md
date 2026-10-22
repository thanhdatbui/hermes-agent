# Coordinator Startup & Terminal Guard Discipline (2026-10-22)

## Bối Cảnh & Sự Cố Khởi Tạo Phiên (Session-Start Traps)

Khi khởi động một session mới trên host Windows Phone Farm (`D:\Taadaa`), Coordinator tuân thủ quy trình 4 bước của `AGENTS.md` (Session-start context). Tuy nhiên, môi trường runtime có các cơ chế chốt chặn kỹ thuật cơ học chặt chẽ:

1. **Lỗi Quên Timeout Foreground Terminal:**
   - Lệnh: `terminal(command='git status --short && git log --oneline -5')` thiếu tham số `timeout`.
   - Kết quả: `[GUARD_FOREGROUND_TIMEOUT_MISSING] Lệnh terminal foreground thiếu timeout! Bắt buộc timeout <= 60s hoặc chạy background=True.`
   - Cơ chế: Hook kiểm soát terminal bắt buộc mọi lệnh foreground phải có `timeout` tường minh <= 60s.

2. **Lỗi Shell Test Bị Chặn Bởi Default-Deny Allowlist:**
   - Lệnh: `terminal(command='test -f /d/Taadaa/HANDOFF.md && ...')`.
   - Kết quả: `⛔ [COORDINATOR GUARD - TERMINAL BLOCKED]: COORDINATOR TERMINAL BLOCKED (DEFAULT-DENY): Lệnh không nằm trong allowlist của Coordinator!`
   - Cơ chế: Terminal của Coordinator vận hành theo cơ chế Default-Deny, chỉ cho phép các lệnh đã được phê duyệt trong whitelist.

3. **Lỗi Đụng Vào Vùng Cấm Tự Bảo Vệ:**
   - Mọi thao tác tìm kiếm / đọc / ghi trực tiếp vào thư mục mã nguồn của các guard hệ thống đều bị chặn vô điều kiện để bảo vệ an toàn runtime.

4. **Bẫy Thư Mục Gốc Không Phải Git Repo (`D:\Taadaa`):**
   - Lệnh: `terminal(command='git status', workdir='D:/Taadaa')`.
   - Kết quả: `fatal: not a git repository (or any of the parent directories): .git`.
   - Cơ chế: Thư mục `D:\Taadaa` là workspace root chứa nhiều repository con độc lập (`tools` = `taadaa-farm-tools`, `tiktok-luot nuoi acc`, `Tiktok_Reg`, `AI-Tools`...).

---

## Các Quy Tắc Chuẩn Hóa (Standard Operating Procedures)

### 1. Kỷ Luật Terminal Foreground Timeout
- Mọi lệnh gọi `terminal` foreground bắt buộc phải khai báo tham số `timeout`:
  ```python
  terminal(command="git status --short && git log --oneline -5", timeout=30, workdir="D:/Taadaa/tools")
  ```
- Với các lệnh dài (>60s) hoặc background daemon: bắt buộc dùng `background=True, notify_on_complete=True`.

### 2. Sử Dụng Công Cụ Native Cho File Inspection
- Không dùng các lệnh shell ad-hoc (`test -f`, `[ -f ]`, `cat`, `head`, `find`) trong terminal vì dễ va phải Default-Deny Guard.
- Dùng công cụ native của Hermes:
  - Đọc file: `read_file(path="D:/Taadaa/HANDOFF.md", offset=1, limit=50)`
  - Tìm file / kiểm tra tồn tại: `search_files(path="D:/Taadaa", pattern="HANDOFF.md", target="files")`

### 3. Vùng Cấm Bảo Vệ Hệ Thống
- Không bao giờ truyền đường dẫn thư mục guard/hook bảo vệ hệ thống vào `search_files`, `read_file`, `write_file`, `patch`.
- Vùng này là bất khả xâm phạm; mọi vi phạm đều kích hoạt Blacklist Guard ngắt lệnh ngay lập tức.

### 4. Định Tuyến Git Đúng Subdirectory Repo
- Khi chạy kiểm tra git ở đầu phiên hoặc sau khi sửa code, bắt buộc chỉ định rõ `workdir` vào repo mục tiêu:
  - Tools chung: `workdir="D:/Taadaa/tools"`
  - Nuôi acc / Feed: `workdir="D:/Taadaa/tiktok-luot nuoi acc"`
  - Reg TikTok: `workdir="D:/Taadaa/Tiktok_Reg"`
  - Video render/upload: `workdir="D:/Taadaa/Tiktok-video"`
