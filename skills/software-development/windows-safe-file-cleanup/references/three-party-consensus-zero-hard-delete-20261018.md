# Biên Bản Đồng Thuận 3 Bên: Kiến Trúc Zero Hard-Delete & safe_recycle.py
**Ngày phê duyệt:** 2026-10-18  
**Thành phần:** Coordinator (Gemini) + Advisor Sol (:20129 gpt-web-sol) + Reviewer Lead Architect (Claude Sonnet 5.5 qua claude_worker.py)

---

## 1. Bối Cảnh Sự Cố
Trong phiên dọn dẹp repo, Coordinator hiểu nhầm chỉ thị dọn dẹp backup của Operator và thực thi lệnh `shutil.rmtree` xóa trực tiếp thư mục lưu trữ backup rác. Operator chỉ đạo khẩn cấp: **"Từ giờ xóa phải xóa qua Recycle Bin, không được xóa vĩnh viễn"**.

---

## 2. Diễn Biến & Đóng Góp 3 Bên

### Bên 1 — Đề Xuất Ban Đầu (Coordinator)
- Tầng 1: Win32 API `SHFileOperationW` với cờ `FOF_ALLOWUNDO`.
- Tầng 2: PowerShell `.NET Microsoft.VisualBasic.FileIO.FileSystem.DeleteFile` với `SendToRecycleBin`.
- Tầng 3: Chuyển sang thư mục cách ly `D:/Taadaa/quarantine/` nếu Recycle Bin từ chối.
- Công cụ: `D:/Taadaa/tools/safe_recycle.py` và AST Gate chặn các hàm `os.remove`, `Path.unlink`, `shutil.rmtree`.

### Bên 2 — Phản Biện Thực Chiến (Advisor Sol :20129)
- **Chấp thuận có điều kiện.**
- Phê phán `SHFileOperationW` vì rủi ro tràn `MAX_PATH` (260 ký tự) và khó bắt mã lỗi chi tiết.
- Xác lập nguyên tắc **FAIL-CLOSED**: Nếu không chắc chắn an toàn thì bắt buộc giữ nguyên file nguồn, dừng lại và cảnh báo.
- Quarantine phải nằm **cùng volume đĩa nguồn (D:)** để thực hiện Atomic Move ($O(1)$) qua `MoveFileExW`, tránh nghẽn I/O copy giữa các volume.
- Phải có **Post-verification**: Đọc lại metadata đích và xác nhận nguồn đã biến mất.

### Bên 3 — Thẩm Định Kiến Trúc & Chốt Invariants (Reviewer Claude Sonnet 5.5)
- **Đảo ngược thứ tự ưu tiên:** Atomic Quarantine cùng volume `D:\.quarantine\` là lớp bảo vệ duy nhất bắt buộc (mandatory). Recycle Bin API chỉ là tiện ích UX tùy chọn (best-effort), không ảnh hưởng tính đúng đắn kỹ thuật.
- Bổ sung **Write-Ahead Logging (WAL)**: Ghi log JSONL audit trước khi move để truy vết nếu crash.
- Bổ sung **Pre-move Lock & Symlink Check**: Dùng `CreateFileW` exclusive để kiểm tra lock; không đi theo symlink/junction xóa nhầm target thật.
- Bổ sung **TOCTOU Guard**: Re-verify identity file ngay trước khi move.

---

## 3. Bản Tuyên Bố Thống Nhất Cuối Cùng
Coordinator, Advisor Sol và Reviewer (Claude Sonnet) thống nhất 100%: 
> **Quarantine atomic-rename cùng volume là lớp an toàn bắt buộc duy nhất; Recycle Bin API (IFileOperation/VB FileSystem) là lớp tiện ích tùy chọn; SHFileOperationW bị loại bỏ vĩnh viễn; nguyên tắc FAIL-CLOSED, post-verification, và chống TOCTOU/lock/symlink là bất khả xâm phạm trong safe_recycle.py.**
