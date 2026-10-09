# Quy tắc phân tách kênh báo cáo và Farm Alert Watchdog

## 1. Phân định 3 kênh Telegram riêng biệt
Căn cứ theo chỉ đạo tách báo cáo ca nuôi TikTok (2026-10-09):
- **Lướt Feed:** Kênh `Tiktok Luot Nuoi Acc` (`-5377611430`) — deliver tự động qua stdout của cronjob `tiktok-feed-session-watchdog`.
- **Follow chéo:** Kênh `Tiktok Follow` (`-5127276494`) — gửi trực tiếp qua Telegram bot.
- **Đăng Video:** Kênh `Tiktok Video` (`-5435853713`) — gửi trực tiếp qua Telegram bot.

## 2. Bóc tách Alert độc lập (Không gộp header)
- **Lỗi hàng loạt (Farm Alert >= 8 máy):**
  - Đánh giá riêng biệt cho từng nghiệp vụ:
    - Nếu lỗi script Follow >= 8 máy ➔ Gửi `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT FOLLOW HÀNG LOẠT (...)` về kênh Follow (`-5127276494`).
    - Nếu lỗi script Upload >= 8 máy ➔ Gửi `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT UPLOAD HÀNG LOẠT (...)` về kênh Video (`-5435853713`).
  - Kênh Feed chỉ phát alert khi chính quá trình lướt Feed gặp sự cố hàng loạt, tuyệt đối không bị ô nhiễm bởi lỗi của Follow hay Upload.

## 3. Invariant bắt buộc về Metadata trên tiêu đề
Mọi alert (hoặc tin báo hoàn tất) khi bóc tách sang từng kênh đều BẮT BUỘC phải giữ nguyên đầy đủ metadata:
- Tên ca chạy (`{win_name}`, ví dụ: `Ca 1 - Phiên 1/2 (Sáng)`).
- Thứ tự Row cấu hình (`(Row {active_row})`).

Ví dụ chuẩn:
`🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT UPLOAD HÀNG LOẠT (14 máy lỗi script Upload) - Ca 1 - Phiên 1/2 (Sáng) (Row 1)`
`📊 [TIKTOK NUÔI ACC] Ca 1 - Phiên 1/2 (Sáng) hoàn tất (Row 1)`
