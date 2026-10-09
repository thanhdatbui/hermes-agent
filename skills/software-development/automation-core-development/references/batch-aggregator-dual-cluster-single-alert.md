# Batch Alert Dual-Cluster Unified Message Specification

## Bối cảnh & Vấn đề
Farm Taadaa vận hành mô hình 2 cụm:
- **Cụm Kibe (Local):** Dải máy `1-80`
- **Cụm Admin (Remote):** Dải máy `201-280` qua ADB socket LAN `.119:5037`

Khi một phiên chạy đồng thời trên cả 2 cụm (như TikTok Feed Session), nếu mỗi cụm khi gặp sự cố tự gọi `batch_aggregator` độc lập, Telegram sẽ nhận **2 tin nhắn Batch Alert** riêng biệt gây loãng và khó theo dõi toàn cảnh.

## Quy tắc Invariant: Single Unified Alert
1. **Gộp làm 1 tin nhắn duy nhất:**
   - Mọi cảnh báo Batch Alert khi một quy trình chạy song song/đồng thời trên 2 cụm Kibe và Admin **BẮT BUỘC gộp thành 1 tin nhắn Telegram duy nhất**.
   - CẤM tách bắn 2 tin riêng lẻ.

2. **Gắn thẻ cụm rõ ràng (Cluster Tagging):**
   - Header: `🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【TOÀN FARM】`
   - Bóc tách từng cụm rõ ràng:
     - `🏢 【FARM KIBE - MÁY 1-80】`: quy mô, tỷ lệ lỗi, signature lỗi hệ thống, cảnh báo văng session / captcha.
     - `🏢 【FARM ADMIN - MÁY 201-280】`: quy mô, tỷ lệ lỗi, signature lỗi (như adb/usb disconnect), cảnh báo văng session / captcha.
   - Nếu một cụm chạy thành công 100% không có lỗi hệ thống, vẫn ghi nhận ngắn gọn `Thành công 100% (không có lỗi hệ thống)`.

3. **Canary Recovery hợp nhất:**
   - Mục Canary Test đại diện nêu rõ từng máy đại diện cho từng cụm gặp lỗi:
     - `Kibe: python D:/Taadaa/tools/inspect_machine.py <M_KIBE>`
     - `Admin: python D:/Taadaa/tools/inspect_machine.py <M_ADMIN>`
   - Đính kèm hình ảnh hiện trường đại diện từ cả 2 cụm.
