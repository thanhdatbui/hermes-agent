# Taadaa Workspace Cleanup & Retention Protocol

## Quy tắc dọn dẹp thư mục Taadaa (D:\Taadaa)

1. **BẮT BUỘC BACKUP TRƯỚC KHI XÓA**:
   - Mọi thao tác dọn dẹp file rác, file tạm, file test phải được copy sao lưu vào `D:\Taadaa\BACKUP_ALL\cleanup_backup_<YYYYMMDD>\` trước khi xóa nguồn.
   - Kiểm tra đối chiếu dung lượng và tính toàn vẹn của bản sao lưu trước khi thực thi xóa.

2. **DANH MỤC CẤM XÓA TUYỆT ĐỐI (PROTECTED LOGS & CREDENTIALS)**:
   - **Log change pass & Account recovery history**: Toàn bộ log đổi mật khẩu, OTP history, thông tin khôi phục email trong `Hotmail/`, `Hotmail/.ai-runs/`.
   - **Log đăng ký tài khoản & mail**: Toàn bộ log reg, inventory, profile mapping trong `Tiktok_Reg/`, `register gmail/`, `add mail khoi phuc/`.
   - **Workbook & safe database**: Các file excel vận hành (`taikhoan_run_safe.xlsx`, `Tik*.xlsx`, `machine-config/`, v.v.).
   - Lý do: Phục vụ tra cứu, truy vết khi phát sinh sự cố sai mật khẩu hoặc cần đối soát tài khoản sau này.

3. **CÁC HẠNG MỤC ĐƯỢC PHÉP DỌN DẸP SAU KHI BACKUP**:
   - File backup tạm của agent: `*.bak*`, `AGENTS.md.bak-*`, `AGENTS.md.flash-high-*.bak`, `*.tmp`, `*~`.
   - Thư mục rỗng / tàn dư ở root hoặc repo: `.git` (nếu rỗng không phải repo), `.agents` (rỗng).
   - Ảnh screenshot test cục bộ/debug tạm: `auth_check_*.png`, `m*_check.png`, `chrome_test*.png` (không thuộc log reg/recovery chính).
   - Artifacts manifest gán tạm: `assignment-manifest-avatar-*.json`.
   - File build desktop cũ chiếm dung lượng lớn (`apps/desktop/release-*`, `build-prebuild-*`).
