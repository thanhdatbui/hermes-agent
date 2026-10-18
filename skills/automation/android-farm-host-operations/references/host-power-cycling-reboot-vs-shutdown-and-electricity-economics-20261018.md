# Host Power Cycling: Reboot vs Shutdown & Phân Tích Kinh Tế Điện Năng Farm (18/10/2026)

## 1. Cạm Bẫy Phản Biện Giáo Điều: "Thermal Cycling & Inrush Current"
- **Hiện tượng phản biện sai lệch:** Khi người dùng hỏi về việc tắt máy hoặc reboot PC Host, Coordinator đem lý thuyết sách vở về "sốc nhiệt (thermal cycling), dòng nạp xung kích (inrush current) làm chai tụ nguồn, nứt mối hàn BGA" ra để cản trở hoặc dọa dẫm.
- **Thực tế vận hành farm (User Invariant):**
  - Farm duy trì lịch reboot máy định kỳ trước 3 ca nuôi chính (`05:20`, `11:20`, `17:20`) qua script `farm_scheduled_reboot.py`.
  - Đây là kỹ thuật thực chiến hoàn toàn chính xác và cần thiết nhằm: giải phóng bộ đệm điều khiển USB, làm sạch rác driver của Windows và reset trạng thái USB 2.0 EHCI sau khi Xiaowei/ADB cày ải hàng chục máy điện thoại liên tục.
  - Reboot mềm thông thường không gây suy hao phần cứng đáng kể; các server và PC hiện đại có tuổi thọ linh kiện bán dẫn (MTBF) 50.000 - 100.000 giờ, vượt xa thời gian khấu hao công nghệ (4-5 năm).

## 2. Bản Chất Kỹ Thuật: Reboot Mềm vs Shutdown Tắt Hẳn Ban Đêm (00:00 - 05:20)
Rủi ro của việc tắt hẳn PC Host qua đêm không nằm ở "hỏng linh kiện", mà nằm ở **tính sẵn sàng của tự động hóa và an toàn vận hành**:
1. **Rụng kết nối & Bão nhận diện USB (USB Enumeration Storm):** Khi PC tắt, USB Root Hub mất điện hoàn toàn. Đến 05:20 sáng PC bật dậy, toàn bộ 80–160 box phone S7 cùng handshake lại một lúc, dễ làm quá tải bus USB, crash ADB server, hoặc bung popup RSA "Cho phép gỡ lỗi USB" (`device unauthorized`).
2. **Kẹt khởi động không người giám sát:** Windows Update ngầm tự reboot, lỗi RTC Alarm trong BIOS (do pin CMOS yếu hoặc Windows Fast Startup ghi đè), hoặc lỗi Auto-login khiến PC không vào được Desktop lúc sáng sớm $\rightarrow$ Ca nuôi 06:00 gãy hoàn toàn.
3. **Mất hệ thống giám sát & báo động đêm:** PC tắt làm ngắt kết nối Hermes Gateway và bot Telegram. Nếu ban đêm xảy ra chập điện, nhảy aptomat hoặc rớt mạng MikroTik, hệ thống không thể phát cảnh báo khẩn cấp.
4. **Điều kiện kỹ thuật nếu bắt buộc phải hẹn giờ tắt/bật PC:**
   - Phải tắt tính năng **Fast Startup** trong Windows Power Options (chống nuốt lệnh RTC Alarm).
   - Bật **Resume by RTC Alarm** trong BIOS và đặt giờ cố định (ví dụ 05:20 hàng ngày).
   - Bật `AutoAdminLogon = 1` trong Registry để Windows tự vào thẳng Desktop.

## 3. Bóc Tách Kinh Tế Điện Năng Farm (~3 Triệu / Tháng)
Khi phân tích hóa đơn điện hộ gia đình có đặt phone farm (~900 - 1.000 kWh/tháng, chạm bậc thang 5-6):
- **Máy lạnh phòng ngủ (1 - 1.5 HP, chạy 16h/ngày):** Chiếm **~40% - 45% (~1.200.000đ - 1.450.000đ)**. Đây là phụ tải tiêu thụ điện lớn nhất.
- **Dàn Box Phone (80 - 160 máy S7 + nguồn tổ ong 12V-5V + quạt box):** Chiếm **~20% - 25% (~600.000đ - 750.000đ)**.
- **2 Case PC Server (Kibe + Admin chạy 24/7):** Chiếm **~15% - 20% (~450.000đ - 550.000đ)**.
- **Thiết bị sinh hoạt gia đình khác (Tủ lạnh, máy giặt, nước nóng, đèn, quạt):** Chiếm **~15% - 18% (~450.000đ - 550.000đ)**.

### Đánh Đổi Risk / Reward & Kết Luận Vận Hành:
- Nếu tắt 2 PC trong 5.5 tiếng ban đêm (00:00 - 05:30): Chỉ cắt giảm được phần idle (~120W - 150W), tiết kiệm khoảng **20 - 25 kWh/tháng $\approx$ 70.000đ - 85.000đ/tháng**.
- Hóa đơn từ 3.000.000đ chỉ giảm xuống ~2.920.000đ (không giải quyết được gốc rễ chi phí), nhưng đánh đổi bằng nguy cơ tê liệt ca sáng của dàn hơn 600 tài khoản TikTok và mất giám sát mạng ban đêm.
- **Khuyến nghị chuẩn:** Giữ 2 PC Host chạy 24/7.
- **Giải pháp tối ưu tiền điện thực tế:**
  1. Tối ưu máy lạnh: Đặt 26°C - 27°C kết hợp quạt gió và vệ sinh lưới lọc định kỳ (tiết kiệm ngay 300k - 400k/tháng).
  2. Dàn Box Phone: Duy trì lệnh ép tắt màn hình điện thoại (`Display Power: OFF`, `input keyevent 223`) lúc rảnh để hạ dòng sạc từ 0.8A xuống 0.2A.
  3. Tắt màn hình máy tính PC khi không ngồi làm việc (tiết kiệm ~35-40k/tháng).
