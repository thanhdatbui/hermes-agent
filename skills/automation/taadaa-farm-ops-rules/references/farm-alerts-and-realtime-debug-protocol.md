# Giao Thức Farm Alerts & Điều Phối Debug Qua Telegram (19/08)

## 1. Cấu Trúc Nhóm "Farm Alerts"
- **Telegram Group ID:** `-5373649734`
- **Tên Nhóm:** `Farm Alerts`
- **Mục Đích:** Kênh tiếp nhận toàn bộ cảnh báo lỗi phát sinh trên 80 máy farm (kèm ảnh chụp màn hình thực tế đóng dấu số máy) và là trung tâm điều phối lệnh sửa lỗi trực tiếp từ xa.

## 2. Format Cảnh Báo Lỗi Tự Động Kèm Ảnh
Mỗi khi worker của một máy bị dừng hoặc gặp sự cố:
1. Chụp màn hình qua ADB: `screencap -p`.
2. Dùng Pillow vẽ banner màu đỏ ở đỉnh ảnh: `[MAY XX] - HH:MM DD/MM`.
3. Gửi ảnh kèm caption chuẩn HTML:
   ```html
   🚨 <b>[MÁY XX] DỪNG PHIÊN</b>
   • <b>Script:</b> <code>multi-machine-feed-session</code> (hoặc follow / reg)
   • <b>Tài khoản:</b> <code>username_hoặc_email</code>
   • <b>Lý do:</b> <i>Mô tả chi tiết lỗi phát sinh</i>
   • <b>Trạng thái:</b> 🟢 <b>ĐANG MỞ</b> <i>(Tự động chạy tiếp phiên sau)</i>
   ```

## 3. Quy Tắc Vận Hành Khi Gặp Lỗi
- **Hết phiên lỗi máy vẫn chạy tiếp:** Sang phiên/ca kế tiếp cùng máy, hệ thống **VẪN TỰ ĐỘNG dọn app và CHẠY TIẾP** (không tự ý lock hay skip ngầm theo prior handoff).
- **Chỉ LOCK khi User ra lệnh:** Lock chỉ được kích hoạt khi có lệnh rõ ràng từ User.
- **Fix lỗi máy thật:** Khi sửa lỗi trên máy đang kẹt, sau khi test qua bước lỗi, **BẮT BUỘC kích hoạt chạy tiếp tục toàn bộ script** cho đến khi hoàn tất phiên (SUCCESS) mới coi là xong.

## 4. Cơ Chế Điều Phối Sửa Lỗi Tại Nhóm Farm Alerts
- Khi User reply tin nhắn alert hoặc gõ lệnh (ví dụ: `sửa máy 43`, `test lại máy 19 follow`):
  - Bot Hermes đóng vai trò Orchestrator tự động trỏ về đúng repo (`tiktok-luot nuoi acc`, `tiktok-follow`, `Tiktok_Reg`, `automation-core`).
  - Thực hiện debug, vá code, chạy test trực tiếp trên máy thật.
  - Báo cáo kết quả kèm ảnh màn hình mới về ngay tại nhóm `Farm Alerts`.
