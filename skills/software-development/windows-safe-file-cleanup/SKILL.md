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

## 2. Kiến Trúc Thực Thi Kỹ Thuật (3 Tầng Đồng Thuận 3 Bên 18/10/2026)

Theo biên bản thống nhất 100% giữa Coordinator, Advisor Sol (:20129) và Reviewer Claude Sonnet 5.5:

### Tầng 1: Atomic Quarantine Cùng Volume (BẮT BUỘC & CỐT LÕI AN TOÀN)
- **Vị trí:** Đặt tại thư mục ẩn ngay trên cùng ổ đĩa: `D:/Taadaa/.quarantine/YYYY-MM-DD/<timestamp>_<uuid>_<filename>`.
- **Atomic Move NTFS:** Dùng `MoveFileExW` / `os.replace` trên cùng filesystem để hoàn thành trong $O(1)$, không copy tránh đứt gãy, không phụ thuộc Shell Explorer, hoạt động bền bỉ trong mọi ngữ cảnh (service, cron, watchdog).
- **Write-Ahead Logging (WAL):** Ghi log audit JSONL (nguồn, đích, timestamp, SHA-256 hash, actor/process) **trước khi move** để không bao giờ mất dấu nếu crash giữa chừng.
- **Post-Verification Bắt Buộc:** Sau khi move, bắt buộc đọc lại metadata tại quarantine path (tồn tại, kích thước khớp, hash khớp) VÀ xác nhận đường dẫn nguồn không còn tồn tại.

### Tầng 2: Recycle Bin Native API (TIỆN ÍCH UX TÙY CHỌN, BEST-EFFORT)
- Dùng `IFileOperation` với cờ `FOFX_RECYCLEONDELETE` (hoặc PowerShell `Microsoft.VisualBasic.FileIO.FileSystem.DeleteFile` với `RecycleOption.SendToRecycleBin`) để đưa vào Recycle Bin của Explorer phục vụ người dùng xem trực quan.
- **Tuyệt đối cấm dùng `SHFileOperationW` cũ** vì rủi ro tràn `MAX_PATH` 260 ký tự và không bắt được mã lỗi chi tiết.
- Lớp này là best-effort (không làm gián đoạn pipeline nếu thất bại, vì Tầng 1 Quarantine đã bảo vệ 100%).

### Tầng 3: Nguyên Tắc FAIL-CLOSED Tuyệt Đối
- Nếu gặp file lock (`WinError 32`), thiếu quyền, symlink trỏ ra ngoài, hoặc bất kỳ lỗi không xác định nào: **DỪNG LẠI NGAY LẬP TỨC (ABORT), GIỮ NGUYÊN FILE NGUỒN**, ném exception và phát alert. Tuyệt đối không có nhánh "xóa ép cho được".

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
