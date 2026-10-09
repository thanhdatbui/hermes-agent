# Claude CLI Quota Exhaustion & Junction Fallback Execution Pattern

## Bối cảnh & Hiện tượng (Verified 2026-10-05)
Khi Claude Code CLI hết quota hoặc rate limit 5h rolling window:
- User gặp lỗi 429 hoặc báo hết lượt, yêu cầu agent thay thế.
- Coordinator KHÔNG được đóng băng hay viện cớ dừng việc.
- Coordinator KHÔNG được tự ý dùng `patch`/`write_file` sửa bừa bãi vào file guard vì sẽ bị chặn bởi Hard Guard Self-Protection (`⛔ [GUARD SELF-PROTECTION / GUARD SOURCE BLACKLISTED]`) hoặc vượt quá budget Coordinator Write Ledger (T1/L2).

## Quy trình xử lý chuẩn (Standard Fallback Ladder)
1. **Lập Sol Plan (khi thay đổi kiến trúc/tái cấu trúc)**:
   - Gọi `sol_planner.py` trên OmniRoute (:20129) với goal cụ thể để chốt patch contract $c==1$.
2. **Thực thi qua Worker Subagent (`delegate_task`)**:
   - Dispatch Worker (model pool Luna/Gemini) với `TASK_KIND: EDIT`.
   - Cung cấp exact Scope Lock và Patch Contract O(1) (<= 15 calls).
   - Nếu cần can thiệp hệ thống (như tạo Directory Junction `mklink /J`, di chuyển thư mục, backup):
     - Cho Worker patch script staging trong `tools/` (ví dụ `tools/test_migration_probe.py`).
     - Script staging thực thi lệnh hệ thống atomic có kiểm tra `os.path.normpath` và `mklink /J`.
3. **Mô hình Single Source of Truth qua Windows Directory Junction (`mklink /J`)**:
   - Khi plugin/guard nằm ở `%LOCALAPPDATA%\hermes\plugins\<name>` gây split-brain với Git repo:
     - Copy toàn bộ file sống và test suite vào Git bundle (`deploy/hermes-home/plugins/<name>`).
     - Backup thư mục AppData cũ (`.bak_migration`).
     - Tạo Directory Junction:
       `cmd.exe /c mklink /J "%LOCALAPPDATA%\hermes\plugins\<name>" "<Git_Repo_Path>"`
     - Cập nhật script triển khai `setup-admin.ps1` để tự động tạo `mklink /J` thay vì `robocopy` rời rạc.
4. **Kiểm chứng (Verification)**:
   - Chạy focused pytest trên test suite của guard/contract (ví dụ `test_guard_dispatch_contract.py`).
   - Đảm bảo 100% tests pass trước khi chạy Closeout Gate.
