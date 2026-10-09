# Kiến Trúc Đồng Bộ Code Hai Chiều Kibe ↔ Admin (Chống Ghi Đè & Chống Bẫy OneDrive)

## 1. Bản chất sự cố & Bẫy kiến trúc (Post-Mortem 2026-09-17)

Trong phiên làm việc ngày 2026-09-17, hệ thống gặp phải bài toán chia sẻ thư mục `tools` (`D:/Taadaa/tools`) giữa 2 máy Kibe và Admin:
1. **Bẫy NTFS Junction trong OneDrive:**
   - Trên máy Kibe, `D:/OneDrive/Taadaa_Sync_Shared/tools` được tạo là NTFS Junction trỏ về `D:/Taadaa/tools`.
   - Ứng dụng OneDrive client của Windows mặc định bỏ qua (ignore) Junction/Symlink để tránh loop. Do đó, toàn bộ tools trên Kibe không bao giờ được sync lên cloud cho máy Admin.
2. **Bẫy script copy một chiều tự động (Ghi đè thảm họa):**
   - Agent đề xuất viết script Python copy tự động các file `.py` từ `D:/Taadaa/tools` sang OneDrive định kỳ 15 phút.
   - User Tad phát hiện ngay lỗ hổng chí tử: *"lỡ bên admin có bản ms hơn sửa ở onedrive r m lại ghi đè à"*.
   - Đúng như vậy: Nếu Admin sửa code trên OneDrive, script copy 1 chiều mù quáng của Kibe sẽ lấy phiên bản cũ trên máy Kibe ghi đè nát toàn bộ thay đổi của Admin, gây mất mát mã nguồn âm thầm không thể phục hồi!
3. **Bẫy chạy code Python trực tiếp trên OneDrive (Sol Auditor phân tích):**
   - **WinError 32 File Lock:** Khi Python chạy sinh ra `__pycache__`, file `.pyc` và ghi log/cache, OneDrive sẽ lock file để sync, gây crash runtime: `PermissionError: The process cannot access the file because it is being used by another process`.
   - **OneDrive Conflict Copy:** Khi 2 máy cùng chạy hoặc sửa file sát giờ, OneDrive tự sinh file rác: `script - Kibe.py` và `script - Admin.py`, làm gãy import module.
   - **Race condition:** File đang sync dở từng chunk thì máy khác nạp vào chạy, gây cú pháp chắp vá hoặc hỏng dữ liệu farm.

---

## 2. Giải pháp chuẩn kiến trúc: GitHub Private Repository

Theo tư vấn của Sol Auditor và phê duyệt của User Tad, giải pháp tối ưu và an toàn nhất cho Source Code dùng chung giữa nhiều máy là **quản lý qua Git độc lập**, hoàn toàn tách biệt khỏi OneDrive.

### A. Cấu trúc thiết lập
- **Repository:** `https://github.com/thanhdatbui/taadaa-farm-tools.git` (Private).
- **Thư mục làm việc trên Kibe:** `D:\Taadaa\tools` (là Git working tree trực tiếp, remote `origin/main`).
- **Thư mục làm việc trên Admin:** `D:\Taadaa\tools` (được clone/pull độc lập qua Git).

### B. Quy tắc vận hành hai chiều (Workflow 0% mất code)
1. **Khi sửa tool trên Kibe:**
   - Sửa code trong `D:\Taadaa\tools`.
   - Commit và push: `git commit -am "..." && git push origin main`.
2. **Khi đồng bộ sang máy Admin:**
   - Admin chỉ cần chạy `clone_all_repos.bat` (hoặc `git -C D:\Taadaa\tools pull origin main`).
   - Nếu Admin có sửa code local, Git bắt buộc kiểm tra merge/rebase, tuyệt đối không tự ý xóa đè code của Kibe.
3. **Cập nhật script cài đặt chung (`link_shared_to_admin.bat` & `clone_all_repos.bat`):**
   - Bỏ lệnh `mklink /J D:\Taadaa\tools` trong `link_shared_to_admin.bat`.
   - Thêm block clone/pull tự động repo `tools` vào `clone_all_repos.bat`.

---

## 3. Bảng phân định ranh giới: Cái gì để OneDrive, cái gì để Git?

| Thành phần | Cơ chế lưu trữ | Lý do |
| :--- | :--- | :--- |
| **Source Code (Tools, Schedulers, Runners)** | **Git Repository** (GitHub Private) | Kiểm soát lịch sử, merge 2 chiều an toàn, không bị lock file runtime `.pyc`. |
| **Configs / Rules / Docs (`machine-config`, `AGENTS.md`)** | **OneDrive Sync Shared** | Static text, ít thay đổi song song, cần áp dụng tức thì. |
| **Excel Data (`gmail_clean_v2.xlsx`, `PROXYgandienthoai.xlsx`)** | **OneDrive Data** | Dữ liệu bảng tính dùng chung, chỉ 1 bên ghi tại một thời điểm hoặc có single-writer. |
