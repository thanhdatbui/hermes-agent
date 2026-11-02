---
name: windows-safe-file-cleanup
description: "Use when deleting files on Windows via safe Recycle Bin."
version: 1.0.0
platforms: [windows]
category: software-development
metadata:
  hermes:
    tags: [recycle-bin, cleanup, safe-delete, windows, quarantine, zero-hard-delete]
    related_skills: [taadaa-farm-ops-rules, desktop-automation]
---
# Windows Safe File Cleanup & Zero Hard-Delete

Use this skill whenever removing, cleaning, pruning, or purging files or directories in Windows development, farm, or production environments.

## 1. Core Invariants (Bất biến tối cao)
1. **Zero Hard-Delete Invariant:** CẤM TUYỆT ĐỐI các lệnh xóa hủy trực tiếp trên đĩa: `shutil.rmtree`, `os.remove`, `os.unlink`, `Path.unlink`, `rm -rf`. Mọi thao tác loại bỏ file/thư mục bắt buộc phải đưa vào **Windows Recycle Bin (`$Recycle.Bin`)**.
2. **Fail-Closed on Rejection:** Nếu Windows Recycle Bin từ chối nhận (file vượt dung lượng quota, ổ đĩa ngoài/mạng không có Recycle Bin, lỗi quyền), hệ thống **bắt buộc di chuyển sang Thư mục Cách ly (Quarantine)** trên cùng volume. Nếu cả Recycle Bin và Quarantine đều lỗi: **DỪNG LẠI NGAY LẬP TỨC (ABORT), GIỮ NGUYÊN FILE NGUỒN**, cấm xóa ép.
3. **Audit Trail Bắt Buộc:** Mọi thao tác dọn dẹp đều phải ghi nhận log hoặc `manifest.json` chứa: đường dẫn gốc, kích thước, SHA-256 hash, thời điểm và danh tính tiến trình thực thi.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
