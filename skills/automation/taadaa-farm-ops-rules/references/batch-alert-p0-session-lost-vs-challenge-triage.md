# Triage Quy Chuẩn Cho P0 Cảnh Báo Mất Phiên / Văng Account (Batch Alert)

## 1. Bản Chất Vấn Đề
Khi nhận cảnh báo dạng:
`🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG`
`⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện 1 máy dính lỗi login/xác minh: Máy M35: manual_challenge marker detected`

Cần phân biệt rõ:
- **P0 Mất Phiên Thật (Session Lost):** Bị log out ra màn hình đăng nhập (`logged out`, `signed out`, `session expired`, `văng`, `login screen`).
- **Captcha / Thử Thách Tạm Thời (Challenge):** Gặp captcha kéo thanh trượt, xoay hình, hoặc text "xác minh" trong video/caption (`manual_challenge`, `captcha`, `verification`).

## 2. Quy Trình Triage O(1) Cho Coordinator
1. **Kiểm tra trạng thái thiết bị live (O(1)):**
   - Lệnh: `python D:/Taadaa/tools/inspect_machine.py <N>`
   - Xem `Current Focus`: Nếu máy đang ở Launcher (`LauncherActivity`), chứng tỏ session nuôi trước đó đã tự động teardown sạch sẽ, không bị kẹt hay treo app.
2. **Kiểm tra trạng thái tài khoản trên Database SOT (O(1)):**
   - Source of Truth duy nhất của Farm cho tài khoản TikTok là SQLite DB: `D:/Taadaa/data/tiktok_tracker.db`.
   - Kiểm tra `account_mapping` (cột `may`, `tik`, `username`) và bảng `snapshots` (cột `status`, `follower`, `following`, `heart`, `video`).
   - Nếu tài khoản vẫn ở trạng thái `LIVE`, số liệu video/tim/follow cập nhật bình thường -> Khẳng định **False P0 Alert**.
3. **Cấm Can Thiệp Bừa Bãi:**
   - Khi phát hiện là False P0 (máy đã về Home, tài khoản LIVE, không kẹt UI), **CẤM** gõ lệnh ADB can thiệp, cấm dispatch worker sửa bậy mã nguồn hoặc bấm màn hình làm xáo trộn farm.
   - Báo cáo rõ ràng: Trạng thái máy, trạng thái focus, tình trạng live của các tài khoản từ database SOT.
