# Anti-Overwrite & Bidirectional Sync Safety Protocol (OneDrive vs Local Tools)

## Bối Cảnh Lỗi Hệ Thống & Sự Cố (2026-09-17)

### Vấn Đề Kiến Trúc: Thư Mục Tools Dùng Chung Giữa Kibe & Admin
- **Thiết kế ban đầu của hệ thống (`link_shared_to_admin.bat`)**:
  - `D:\OneDrive\Taadaa_Sync_Shared\tools` là thư mục **GỐC (Single Source of Truth - SSOT)** nằm trên OneDrive đám mây.
  - Cả máy Kibe và máy Admin khi cài đặt đều tạo liên kết NTFS Junction:
    ```cmd
    mklink /J "D:\Taadaa\tools" "%ONEDRIVE_SHARED%\tools"
    ```
  - Mục đích: Bất kỳ ai sửa đổi file tool trên máy nào, file đều lập tức cập nhật lên OneDrive và sync về máy còn lại mà không cần copy thủ công.

### Bẫy Chết Người: Script Tự Ý Đồng Bộ 1 Chiều Bằng `shutil.copy`
- Trong phiên làm việc ngày 2026-09-17, Agent đã mắc sai lầm nghiêm trọng khi tự ý viết thêm hàm `sync_tools()` vào `cron_sync_watchdog.py`:
  ```python
  # SAI LẦM TAI HẠI (ANTI-PATTERN):
  shutil.copy2(src_local_tools, dst_onedrive_tools)
  ```
- **Hậu Quả Khôn Lường**:
  - Nếu máy Admin sửa code hoặc nâng cấp một script trong `tools` trên OneDrive.
  - Script chạy ngầm của Kibe (vốn chỉ copy 1 chiều từ local `D:/Taadaa/tools` lên OneDrive) sẽ so sánh timestamp hoặc tự động **GHI ĐÈ NÁT TOÀN BỘ CODE MỚI CỦA ADMIN BẰNG PHIÊN BẢN CŨ TRÊN MÁY KIBE**.
  - Đây là lỗi Silent Code Loss (mất mã nguồn âm thầm) cực kỳ nguy hiểm trong kiến trúc phân tán đa máy.

---

## 5 Quy Tắc Bất Biến Về Đồng Bộ File & Tool Đa Máy (INVARIANT SYNC SAFETY)

### 1. CẤM TUYỆT ĐỐI Viết Script Copy Tự Động 1 Chiều Ghi Đè Thư Mục Code Chung
- Tuyệt đối CẤM mọi script ngầm dùng `shutil.copy`, `shutil.copy2`, `rsync`, hoặc `Robocopy` theo chế độ tự động đè file từ máy cục bộ lên thư mục chia sẻ OneDrive.
- Khi hai máy cùng làm việc trên một thư mục dùng chung, việc copy 1 chiều không có kiểm tra conflict sẽ biến máy chạy cron thành "kẻ hủy diệt code" của máy kia.

### 2. Single Source of Truth (SSOT) Tại OneDrive
- Không duplicate thư mục `tools` thành nhiều bản sao rời rạc trên cùng một máy rồi tìm cách sync qua lại.
- Dùng NTFS Junction (`mklink /J "D:\Taadaa\tools" "D:\OneDrive\Taadaa_Sync_Shared\tools"`) để trỏ thẳng vào thư mục OneDrive. Mọi tiến trình chạy trên máy đọc/ghi trực tiếp vào Junction, để OneDrive client tự động lo việc đồng bộ nhị phân hai chiều giữa Kibe và Admin.

### 3. Phân Biệt Giữa Sync Artifacts (1 chiều được phép) vs Sync Source Code (Cấm)
- **Được phép copy 1 chiều**: Các file sinh ra từ runtime của riêng máy Kibe (ví dụ: `jobs.json` của Kibe, file state, snapshot logs).
- **CẤM copy 1 chiều**: Toàn bộ mã nguồn Python (`.py`), shell script (`.bat`, `.sh`, `.ps1`) trong `tools/` và code repositories. Mã nguồn phải quản lý qua Git hoặc OneDrive Junction trực tiếp.

### 4. Báo Cáo & Revert Ngay Khi Phát Hiện Cơ Chế Copy Ghi Đè
- Khi phát hiện mã nguồn hoặc cron watchdog có chứa logic copy đè tools từ local lên OneDrive:
  1. Dừng ngay lập tức và Revert mã nguồn về trạng thái an toàn.
  2. Báo cáo trung thực với User về nguy cơ xung đột phiên bản.
  3. Tuyệt đối không bao biện rằng "script chỉ copy file mới hơn" vì timestamp giữa các máy qua OneDrive có thể bị lệch hoặc bị reset khi tải về.
