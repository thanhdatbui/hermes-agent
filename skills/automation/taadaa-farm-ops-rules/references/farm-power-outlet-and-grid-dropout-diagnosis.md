# Diagnosing Farm Power Drops, Outlets, and Split Failures

## Overview
Khi gặp sự cố farm sập nguồn, máy khởi động lại hoặc phone sập nguồn sau các biến cố điện lưới (chớp nháy, mưa bão, brownout):

### 1. Phân biệt sự cố Lưới điện toàn nhà vs. Nhánh điện / Ổ cắm cục bộ
- **Dấu hiệu lưới điện sụt áp (Brownout / Recloser EVN):**
  - Đèn, quạt ở phòng khác chớp tắt 1-2s rồi có lại ngay.
  - PC server có bộ nguồn tốt (tụ lọc lớn) có thể vượt qua cú chớp 1-2s mà không sập.
  - Box phone S7 dùng nguồn tổ ong / adapter cực kỳ nhạy với sụt áp, sập ngay lập tức.
- **Dấu hiệu sập cục bộ nhánh / ổ cắm (Không phải cúp điện cả nhà):**
  - Máy Admin (hoặc máy khác cùng phòng/khác phòng) chạy thông suốt hàng chục tiếng không hề sập (`uptime` không đổi, không có Kernel-Power Event 41/6008).
  - Chỉ có máy Kibe + Box Phone sập kéo dài nhiều chục phút.
  - Nguyên nhân: Nhảy CB con của riêng nhánh ổ cắm đó, hoặc ổ cắm tường bị move nhiệt / giãn lá đồng tiếp điểm khi tải dồn.

### 2. Hành vi khởi động lại của thiết bị khi có điện lại (Auto Power-on)
- **Mainboard Server (như HUANANZHI X99-F8D):**
  - Mặc định BIOS có tính năng `Restore on AC Power Loss: Power On`. Khi có điện trở lại, main tự kích nguồn boot vào Windows ngay lập tức.
- **Samsung Galaxy S7:**
  - **ROM Mod (Auto-boot / Boot on charge):** Tự động bật máy boot thẳng vào Android khi có nguồn sạc trở lại, tự nhận lại ADB.
  - **ROM Gốc:** Chỉ hiện biểu tượng sạc pin (`LPM`), KHÔNG tự bật nguồn. Bắt buộc phải bấm nút nguồn vật lý.

### 3. Cạm bẫy đấu nối điện Farm (Pitfalls)
- **Tuyệt đối KHÔNG cắm chung PC Dual Xeon + Dàn Box Phone vào cùng 1 mặt ổ cắm tường gia dụng:**
  - PC Dual Xeon (300W - 600W) + Box Phone khi sạc dồn (vài trăm Watt) tạo dòng Ampe đỉnh (inrush current) cực lớn.
  - Ổ cắm âm tường dân dụng (như Sino/Vanlock) tiếp điểm đồng mỏng, chạy 24/7 sinh nhiệt làm giãn lá đồng, gây move điện và sụt áp cục bộ khiến nguồn PC tự ngắt bảo vệ.
- **Tuyệt đối KHÔNG dồn tải Box Phone sang ổ cắm của máy khác đang full tải:**
  - Nếu máy Admin cũng đang cắm Dual Xeon + 4 Box + Router, việc kéo Box của Kibe sang cắm ké sẽ làm ổ Admin quá tải, sập cả 2 cụm.
- **Khắc phục chuẩn:**
  - Nâng cấp mặt ổ cắm chịu tải cao (ví dụ Panasonic Wide 16A hoặc Schneider có lò xo kẹp chống giãn).
  - Tách nhánh điện hoặc dùng UPS (1000VA - 1500VA) làm đệm bảo vệ riêng cho thùng PC server.
