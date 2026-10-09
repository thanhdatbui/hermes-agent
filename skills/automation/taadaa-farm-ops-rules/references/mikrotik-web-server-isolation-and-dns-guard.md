# Pitfall: Cấm chèn dịch vụ mới vào Web Server nội bộ đang chạy của Farm (MikroTik Web Manager :2310)

## Sự cố ngày 17/09/2026:
- Khi user yêu cầu theo dõi list TikTok qua giao diện web xem trên điện thoại và nhắc tới `kibe:2310`, agent đã tự ý:
  1. Thêm route `/tiktok` và chèn link vào code `D:/Taadaa/AI-Tools/tools/mikrotik_web/server.py`.
  2. Tự ý thêm DNS tĩnh `kibe` -> `192.168.110.123` trên router MikroTik.
  3. Kill tiến trình `server.py` đang chạy để restart.
- Hậu quả: Gây xung đột DNS MagicDNS của Tailscale (`kibe -> 100.88.164.111`), làm gián đoạn dashboard MikroTik khiến user trên điện thoại không thể truy cập được cả MikroTik lẫn TikTok, gây ức chế.

## Quy tắc bất biến (Farm Invariant):
1. **CẤM TUYỆT ĐỐI** tự ý patch, chèn route mới hoặc restart các server web nội bộ đang phục vụ hạ tầng farm (đặc biệt là MikroTik Web Manager `server.py` cổng `2310`).
2. **CẤM TUYỆT ĐỐI** tự ý thêm DNS tĩnh đè lên các hostname cốt lõi (`kibe`) trên Router MikroTik vì sẽ xung đột với dải Tailscale VPN và các dịch vụ đồng bộ khác.
3. Mọi công cụ, dashboard hoặc report mới phải chạy độc lập hoàn toàn (standalone service ở cổng riêng, hoặc xuất file Excel OneDrive / tin nhắn Telegram), không được ký sinh vào web server của hạ tầng.
4. Khi user báo lỗi không vào được dịch vụ hiện hữu: BẮT BUỘC ưu tiên REVERT về bản gốc sạch (`.bak`), xóa sạch các thay đổi cấu hình mạng/DNS vừa làm, và xác minh dịch vụ gốc hoạt động trở lại trước tiên.
