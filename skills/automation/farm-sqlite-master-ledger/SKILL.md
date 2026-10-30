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

## 3. Microsoft OAuth Graph API Trích Xuất OTP Tự Động (mailboxes)
- **Hơn 880 hòm thư Hotmail/Outlook trong `mailboxes` có sẵn `oauth_refresh_token`:**
  - CẤM dùng browser đăng nhập web Outlook bằng password khi cần lấy OTP (Microsoft sẽ kích hoạt checkpoint đòi mail khôi phục `fviainboxes.com`).
  - **Luồng lấy OTP chuẩn O(1):**
    1. Lấy `oauth_refresh_token` và `oauth_client_id` (nếu null dùng client mặc định `0000000040170455`).
    2. POST đổi access token qua `https://login.live.com/oauth20_token.srf` (`grant_type=refresh_token`).
    3. GET tin nhắn mới nhất qua Microsoft Graph: `https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=1` (nếu không có, kiểm tra thêm thư mục `junkemail`).
    4. Trích xuất regex 6 số `\b\d{6}\b` từ `bodyPreview` hoặc `subject`.
  - CẤM dừng lại xin người dùng email cá nhân hoặc than phiền thiếu mail khi Farm đã có sẵn kho mailboxes OAuth tự động giải OTP trong 2 giây.

## 4. Quy Chuẩn Hiển Thị Web Dashboard (`http://kibe:1905`)
- **Tách riêng Danh Mục Lớn (Top-level Navigation):** Sổ Cái Farm là hệ thống quản trị dữ liệu local độc lập, bắt buộc đặt thành tab danh mục lớn ở đầu trang (`📊 Giám Sát TikTok` và `📓 Sổ Cái Farm (SQLite)`). CẤM đưa Sổ Cái vào hàng nút lọc phụ (`.filter-buttons`) của bảng TikTok. Khi chuyển sang tab Sổ Cái, ẩn hoàn toàn khu vực KPI và thanh lọc của TikTok.
- **Phân định rõ ràng 2FA TikTok vs 2FA Mail:**
  - Bảng `tiktok_accounts` có `twofa_secret` -> hiển thị cột trái: `🔑 2FA TT: <SECRET_KEY>`.
  - Bảng `mailboxes` có `twofa_secret` riêng -> hiển thị cột phải: `🔑 2FA Mail: <SECRET_KEY>` (nếu có 2FA mail; nếu dùng token thì hiện badge `🟢 OAuth Live`). Tuyệt đối CẤM chỉ ghi nhãn `2FA` chung chung khiến người dùng nhầm lẫn giữa 2FA của TikTok và Mail.
- **Kiến trúc JS & f-string Pitfall:** File `tiktok_dashboard.py` dùng f-string `f"""..."""`. Toàn bộ logic JS và style của Sổ Cái bắt buộc đóng gói dạng raw string `r"""..."""` trong `dashboard/ledger_component.py` (`LEDGER_VIEW_CSS`, `LEDGER_VIEW_JS`), tránh viết inline JS trong template gây vỡ cú pháp `SyntaxError`.
- **Responsive Mobile Layout (Chống Đè Chữ & Sub-card 2 Khối):** Tuyệt đối CẤM dùng `grid-template-areas` cứng 3 cột khi hiển thị các chuỗi hash 32 ký tự (như secret key 2FA). Bắt buộc phân khối component `.slot-header` (slot no, username, badge) + `.slot-cols` gồm 2 sub-card viền riêng: Khối TikTok (`Pass`, `2FA TT`) và Khối Mail (`Email` đặt đầu, `Pass Mail`, `2FA Mail`), tự stack 1 cột trên mobile `@media (max-width: 600px)` kèm `word-break: break-all;` / `overflow-wrap: anywhere;`. Trang bị nút `[Copy]` 1 chạm cạnh Password và 2FA để tiện thao tác.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
> - `references/migration_reconciliation.md`: Đối chiếu di chuyển Excel sang SQLite.
> - `references/hotmail-oauth-graph-otp-extraction.md`: Hướng dẫn trích xuất mã OTP Hotmail tự động qua Microsoft OAuth Graph API.
