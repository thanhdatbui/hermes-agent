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

## 2. Kiến Trúc Thực Thi Kỹ Thuật (Multi-Tier)

### Tầng 1: Windows Shell API (Recycle Bin Native)
Sử dụng Win32 Shell API với cờ `FOF_ALLOWUNDO` để chuyển tệp/thư mục vào Recycle Bin:
- **Win32 Shell Call (`ctypes`):**
  ```python
  import ctypes
  from ctypes import wintypes

  class SHFILEOPSTRUCTW(ctypes.Structure):
      _fields_ = [
          ("hwnd", wintypes.HWND),
          ("wFunc", wintypes.UINT),
          ("pFrom", wintypes.LPCWSTR),
          ("pTo", wintypes.LPCWSTR),
          ("fFlags", wintypes.WORD),
          ("fAnyOperationsAborted", wintypes.BOOL),
          ("hNameMappings", wintypes.LPVOID),
          ("lpszProgressTitle", wintypes.LPCWSTR),
      ]

  FO_DELETE = 0x0003
  FOF_ALLOWUNDO = 0x0040       # Bắt buộc: Đưa vào Recycle Bin
  FOF_NOCONFIRMATION = 0x0010  # Silent, không hiện popup hỏi
  FOF_SILENT = 0x0004          # Không hiện animation Windows
  FOF_NOERRORUI = 0x0400       # Không hiện error dialog
  ```
- **Lưu ý đường dẫn:** Chuỗi `pFrom` phải được kết thúc bằng **hai ký tự null (`\0\0`)** theo chuẩn Win32 API. Với đường dẫn dài hoặc sâu, chuẩn hóa tiền tố `\\?\` để chống tràn `MAX_PATH` (260 ký tự).

### Tầng 2: PowerShell / .NET Fallback
Khi chạy từ bash/shell CLI hoặc script ngoài:
```powershell
Add-Type -AssemblyName Microsoft.VisualBasic
[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(
    "$Path",
    [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
    [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin
)
# Đối với thư mục:
[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory(
    "$DirPath",
    [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
    [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin
)
```

### Tầng 3: Atomic Quarantine Cùng Volume
Khi Recycle Bin không khả dụng (session 0 service account, disk quota đầy):
- **Vị trí:** Đặt tại thư mục ẩn ngay trên cùng ổ đĩa: `D:/Taadaa/.quarantine/YYYY-MM-DD/<uuid>/`.
- **Atomic Move:** Dùng `MoveFileExW` / `os.replace` trên cùng filesystem để hoàn thành trong $O(1)$, không copy tránh đứt gãy.
- **Manifest:** Tạo `manifest.json` ghi lại hash SHA-256 và đường dẫn gốc để sẵn sàng restore 100%.

## 3. Corner Cases & Pitfalls
1. **File Lock (WinError 32):** Nếu file đang bị tiến trình khác (adb, python daemon, excel) khóa handle, **CẤM ép đóng handle bằng tool bạo lực**. Thử lại tối đa 2 lần với backoff 1s; nếu vẫn khóa thì bỏ qua file đó, ghi warning và báo cáo.
2. **Symlink / Reparse Point:** Tuyệt đối không xóa đệ quy xuyên qua symlink/junction trỏ ra ngoài repo. Chỉ xóa chính junction entry đó.
3. **Hiểu nhầm ý định Operator về Backup:** Khi người dùng bảo "backup xong dọn hết đi", ý là **di chuyển/gom các tệp rác vào thư mục lưu trữ backup để giải phóng repo**, TUYỆT ĐỐI KHÔNG ĐƯỢC XÓA BẢN BACKUP.

## 4. References & Chi Tiết Kiến Trúc
- Phản biện kiến trúc chuyên sâu từ Advisor Sol: [`references/advisor-sol-critique-and-zero-hard-delete-architecture.md`](references/advisor-sol-critique-and-zero-hard-delete-architecture.md)
