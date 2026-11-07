# Quy Trình Đối Soát Tam Giác Phân Lớp Tài Khoản (Clean Regular vs Pro vs TikTok)

## 1. Bản Chất Vấn Đề
Khi User yêu cầu "tìm nick Google bình thường (không Pro, không dính TikTok)":
- Coordinator rất dễ mắc bẫy tra cứu bề nổi trong `farm_master.db` hoặc GPM, lấy nhầm tài khoản đã được kích hoạt gói **Google AI Pro** (ví dụ: `dokieu04092004@gmail.com` trong combo `gemini-web-pro` hoặc `votuyen`, `giangkim` trong `ag-gemini-pool-3`).
- Việc đưa tài khoản Pro cho mục đích sử dụng thông thường gây lãng phí quota AI, làm xáo trộn pool AI của OmniRoute và gây khó chịu cho User.

## 2. Quy Chuẩn Tam Giác Đối Soát (Tri-Layer Exclusion Gate)
Trước khi bàn giao bất kỳ tài khoản Gmail "thường" (clean regular account) nào cho User, BẮT BUỘC chạy script đối soát loại trừ đồng thời qua 3 lớp:

1. **Lớp 1: Loại trừ TikTok Farm (`farm_master.db`)**
   ```sql
   SELECT DISTINCT email FROM tiktok_accounts WHERE email IS NOT NULL
   ```
   Bất kỳ Gmail nào nằm trong danh sách này đều là tài khoản đang gắn nick TikTok Phone Farm -> **LOẠI BỎ**.

2. **Lớp 2: Loại trừ Toàn Bộ Pool OmniRoute Pro (`storage.sqlite`)**
   Tra cứu trong cả bảng `provider_connections` (nhánh `antigravity`, `gemini-web`) và cấu hình `models` trong `combos` (`ag-gemini-pool-3`, `gemini-web-pro`, `gemini-web-argon-pool`).
   Bất kỳ Gmail nào có metadata `g1-pro-tier`, `Pro`, `Google AI Pro`, hoặc có ID nằm trong pool Pro -> **LOẠI BỎ**.

3. **Lớp 3: Khớp nối GPMLogin Profiles (`:19995`)**
   Tài khoản hợp lệ phải có sẵn Profile trên GPM để User có thể bấm Start trực tiếp, có proxy farm/webshare gắn sẵn và có mật khẩu đăng nhập trong `mailboxes`.

## 3. Tiêu Chuẩn Phản Hồi Bàn Giao
Khi User yêu cầu acc thường:
- Cung cấp rõ ràng: Email, Mật khẩu, Tên Profile chính xác trên GPM (kèm từ khóa ngắn để gõ search nhanh trên app GPM).
- Báo cáo rõ ràng: Xác nhận đã đối soát `In_TikTok = False` và `In_Pro_Pool = False`.
