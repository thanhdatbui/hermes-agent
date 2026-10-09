# Quy Chuẩn Hợp Nhất 67 Cổng Proxy (MobiProxy + MikroTik LAN) & Tối Ưu Tải Video Farm (2026-09-11)

## 1. Bối cảnh & Sự cố thực tế
Khi chạy batch tải video (`download_by_niche.py`), việc nạp trực tiếp file master `PROXYgandienthoai.xlsx` đã gây ra sự cố nghiêm trọng:
- Danh sách proxy trong file có chứa dải domain `mirotik1.taadaa.click:10001..10007`.
- Domain `mirotik1.taadaa.click` phân giải ra IP WAN public (`171.231.181.33`), nhưng trên Router MikroTik firewall có rule **DROP toàn bộ kết nối WAN vào các cổng này** và không bật Hairpin NAT.
- Kết quả: Các worker download từ máy Kibe cố kết nối tới `171.231.181.33:10005` và dính `ProxyError: ConnectTimeoutError` liên hoàn sau 30s timeout, làm nghẽn tiến trình tải.
- Sai lầm thứ hai: Coordinator suy diễn sai lệch "cổng MikroTik dành riêng cho điện thoại nuôi nick, cổng Mobi mới tải", chỉ bốc 7 cổng thay vì toàn bộ 35 lines PPPoE của hệ thống.

## 2. Bản chất kỹ thuật & Giải pháp chuẩn
- **MobiProxy (`test.taadaa.click:5101..5132`)**: Có **32 ports** chạy trên nền 4G Viettel/Mobi, phản hồi cực nhanh (~0.6s).
- **MikroTik PPPoE (`10001..10035`)**: Có **35 lines PPPoE độc lập** chạy trên router MikroTik nội bộ tại IP LAN `192.168.110.2`. Toàn bộ 35 cổng từ 10001 đến 10035 đều OPEN và LIVE 100% trong mạng LAN.
- **Ánh xạ DNS nội bộ bắt buộc**:
  Thêm vào file `C:\Windows\System32\drivers\etc\hosts`:
  ```text
  192.168.110.2 mirotik1.taadaa.click
  ```
  Sau khi map, mọi kết nối tới `mirotik1.taadaa.click:10001..10035` sẽ đi thẳng nội bộ qua switch LAN tới MikroTik với độ trễ siêu thấp **~0.4 - 0.5s**, lách hoàn toàn firewall WAN.

## 3. Quy chuẩn tạo Pool 67 Cổng Master
Sử dụng script canonical `D:\Taadaa\Tiktok-video\scripts\generate_67_proxy_pool.py` để sinh danh sách:
- **32 ports Mobi**: `test.taadaa.click:5101:mobi1:TaadaaMobi#2026!` .. `test.taadaa.click:5132:mobi32:TaadaaMobi#2026!`
- **35 ports MikroTik**: `mirotik1.taadaa.click:10001:admin@1:admin@1` .. `mirotik1.taadaa.click:10035:admin@1:admin@1`
- **Tổng cộng**: 67 ports live 100%, ghi ra `D:\Taadaa\Tiktok-video\proxy_pool_67.txt` và `combined_proxies_pool.txt`.

## 4. Quy tắc Scale Worker: Download vs Render
- **Batch Download (Network I/O bound)**:
  - Tải video qua `yt-dlp` chủ yếu tốn băng thông mạng và đĩa, **hoàn toàn KHÔNG gây lag máy host**.
  - Có 67 cổng proxy xoay vòng đỡ tải $\rightarrow$ **BẮT BUỘC chạy `--parallel 20` workers** để tối đa hóa tốc độ gom video.
  - CẤM hạ worker xuống 5 hay 8 khi không có sự cố, vì làm chậm tiến độ gom kho nguồn.
- **Batch Render (CPU/GPU bound)**:
  - FFmpeg mã hóa và randomize filter rất nặng CPU $\rightarrow$ **BẮT BUỘC duy trì `--parallel 1` worker** để bảo vệ máy Kibe luôn mát mẻ và phục vụ các tác vụ khác.
