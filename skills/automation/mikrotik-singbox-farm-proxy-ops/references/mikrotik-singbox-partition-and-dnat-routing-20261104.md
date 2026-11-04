# Tối Ưu Định Tuyến MikroTik & Singbox Farm TikTok (2026-11-04)

## 1. Phân Luồng Chuẩn Giữa 3proxy & Singbox
- **48 máy Admin kênh chính:** Chạy trực tiếp 35 line PPPoE tại Đà Nẵng qua `3proxy` (`mirotik1.taadaa.click:10008..10035`). **TUYỆT ĐỐI KHÔNG ĐƯA VÀO SINGBOX CONFIG**.
- **32 máy Admin kênh non/yếu:** Trỏ Singbox sang 16 cổng của Xiaomi R3G Thái Bình (`tb.taadaa.click:5141..5158`).
- **80 máy Kibe:** Trỏ Singbox sang cụm MobiProxy Thái Bình (`test.taadaa.click:5101..5138`).
- Cấu hình gộp Singbox (`singbox_full_160.json`) chỉ được phép nạp **112 máy** (80 Kibe + 32 Admin non), giảm 35% dung lượng file và giải phóng hàng nghìn socket listeners ảo.

## 2. Kiến Trúc Kernel DNAT vs. Singbox L7
- **Tại sao CPU MikroTik x86 lên 95%:**
  - Không phải do thiếu RAM (RAM vẫn trống 4.8GB).
  - Do hàng chục nghìn gói tin video TikTok phải chui qua card mạng ảo `veth-singbox` vào container Docker user-space, gây bão ngắt mạng phần mềm (`softirq`).
- **Kernel DNAT (FastPath) - Lợi ích & Rào cản:**
  - *Lợi ích:* Đổi địa chỉ gói tin ở tầng chip phần cứng, CPU MikroTik rơi về < 5%, giải phóng toàn bộ máy PC.
  - *Rào cản R3G:* Tinyproxy trên R3G bind vào interface PPPoE con (`100.123.x.x`), trong khi gói tin DNAT vào từ cổng WAN cáp quang chính $\rightarrow$ gây lệch đường trả gói tin (*Asymmetric Routing*) làm timeout.
  - *Rào cản MobiProxy:* MobiProxy yêu cầu User/Pass, muốn dùng DNAT phải chuyển sang chế độ *"Không xác thực"* và chỉ dùng Whitelist IP để bảo vệ.

## 3. Khắc Phục Lỗi Advisor Sol & Gemini Trên Cổng :20129
- **Sol:** Trong `consult_advisor.py`, ưu tiên gọi thẳng model `gpt-web-sol` trước model `review` (vốn hay bị 503 do combo retry limit).
- **Gemini Web:** Sửa điều kiện kiểm tra độ dài từ `len(text_resp) > 20` thành `len(text_resp) > 0` để không bỏ qua các câu trả lời ngắn gọn.
