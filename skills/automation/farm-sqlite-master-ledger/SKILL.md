---
name: farm-sqlite-master-ledger
description: "Use when managing farm SQLite database, DAL, or web ledger."
---
# Farm SQLite Master Ledger & Web Dashboard Operations

## 1. Trọng Tâm & Bối Cảnh
- **Thay thế Excel bằng SQLite:** Chuyển đổi toàn bộ các file Excel phân mảnh trong OneDrive (`taikhoan_dat_v2_updated .xlsx`, `gmail_clean_v2.xlsx`, `taikhoan_run_safe.xlsx`, `PROXYgandienthoai.xlsx`) sang cơ sở dữ liệu SQLite tập trung đặt tại ổ đĩa local: `D:/Taadaa/data/farm_master.db`.
- **Mục tiêu:** Diệt trừ 100% lỗi lock file OneDrive (`RecallOnDataAccess`, `PermissionError`), đồng thời cung cấp giao diện Web trực quan tại `http://kibe:1905` cho người dùng tra cứu nhanh, quản lý và copy 2FA / Mật khẩu.

## 2. Cấu Trúc Cơ Sở Dữ Liệu (`farm_master.db`)
- `machines`: `machine_id` (PK, 1-80 Kibe, 201-280 Admin), `owner`, `proxy_endpoint`, `device_serial`, `source`.
- `tiktok_accounts`: `username` (PK), `password`, `twofa_secret`, `email`, `machine_id`, `video_slot`, `owner`.
- `mailboxes`: `email` (PK), `password`, `twofa_secret`, `oauth_refresh_token`, `oauth_client_id`, `oauth_status`, `provider`.
- `slot_assignments`: `machine_id`, `slot_no` (1-8), `tiktok_username`.
- **Cập nhật & Đồng bộ Thay thế Gmail DIE:** Toàn bộ 3 nick khuyết email trước đây (`@doanmai0701` Máy 25, `@lieuhoan03` Máy 02, `@tanglam024` Máy 42) đã được liên kết thành công sang Hotmail mới có Graph API. Toàn farm còn 40 tài khoản đang dính Gmail DIE cần cuốn chiếu thay thế bằng Hotmail sạch. Tra cứu quy trình thay thế và dọn dẹp tại `references/hotmail-replacement-for-die-gmail.md` và `references/migration_reconciliation.md`.

## 3. Quy Chuẩn Hiển Thị Trên Web Sổ Cái (`http://kibe:1905`)
File hiển thị: `D:/Taadaa/tools/dashboard/ledger_component.py` (tích hợp vào `tiktok_dashboard.py`).
- **Tách Danh Mục Lớn độc lập (Top-level Navigation):** Sổ Cái Farm là hệ thống quản trị dữ liệu local độc lập, bắt buộc đặt thành tab danh mục lớn riêng ở đầu trang (`📊 Giám Sát TikTok` vs `📓 Sổ Cái Farm (SQLite)`), tự động ẩn KPI thừa khi xem Sổ Cái. CẤM đưa Sổ Cái vào hàng nút lọc phụ (`.filter-buttons`) của bảng TikTok.
- **Quy chuẩn Sub-card 2 Khối & Thứ tự trực quan:**
  - Mỗi slot tài khoản bắt buộc chia làm 2 sub-card viền riêng: Khối TikTok bên trái và Khối Mail bên phải.
  - **Khối TikTok:** Nhãn `TIKTOK`, gồm `🔑 Pass:` và thẻ vàng `🔑 2FA TT:`.
  - **Khối Mail:** Nhãn `GMAIL` hoặc `OUTLOOK`. BẮT BUỘC đặt `📧 Email` lên **dòng đầu tiên** theo luồng đọc tự nhiên, tiếp theo là `✉️ Pass Mail:` và thẻ xanh `🔑 2FA Mail:` (nếu có).
  - **Nút Copy 1 chạm:** Trang bị nút `[Copy]` ngay cạnh Password, 2FA TT, Email, Pass Mail, 2FA Mail để tiện chép thẳng vào clipboard trên mobile, chuyển trạng thái `Copied!` xanh lá phản hồi.
- **Responsive Mobile Layout (Chống Đè Chữ):** Tuyệt đối CẤM dùng `grid-template-areas` cứng 3 cột khi hiển thị các chuỗi hash 32 ký tự (như secret key 2FA). Bắt buộc phân khối component `.slot-header` + `.slot-cols` gồm 2 sub-card, tự động stack 1 cột trên mobile `@media (max-width: 600px)` kèm `word-break: break-all;` / `overflow-wrap: anywhere;` để triệt tiêu 100% tình trạng đè chữ, lẹm mép.
- **Khởi động / Restart:** Chạy `python D:/Taadaa/tools/restart_tiktok_dashboard.py`.

## 4. Microsoft OAuth Graph API Trích Xuất OTP Tự Động (mailboxes)
- **Hơn 880 hòm thư Hotmail/Outlook trong `mailboxes` có sẵn `oauth_refresh_token`:**
  - CẤM dùng browser đăng nhập web Outlook bằng password khi cần lấy OTP (Microsoft sẽ kích hoạt checkpoint đòi mail khôi phục `fviainboxes.com`).
  - **Luồng lấy OTP chuẩn O(1):**
    1. Lấy `oauth_refresh_token` và `oauth_client_id` (nếu null dùng client mặc định `0000000040170455`).
    2. POST đổi access token qua `https://login.live.com/oauth20_token.srf` (`grant_type=refresh_token`).
    3. GET tin nhắn mới nhất qua Microsoft Graph: `https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=1` (nếu không có, kiểm tra thêm thư mục `junkemail`).
    4. Trích xuất regex 6 số `\b\d{6}\b` từ `bodyPreview` hoặc `subject`.
  - CẤM dừng lại xin người dùng email cá nhân hoặc than phiền thiếu mail khi Farm đã có sẵn kho mailboxes OAuth tự động giải OTP trong 2 giây.

## 5. Đối Soát GPM Login Session & Cookie Store Trình Duyệt
- Xem chi tiết tại `references/gpm-profile-and-cookie-reconciliation.md` về cách đối soát `farm_master.db` với GPM SQLite DB (`profile_data.db`) và quét session cookie sống (Google SID/SSID, Microsoft AUTH) qua chế độ URI read-only mà không gây lock file.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
