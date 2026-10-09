# Power Outage & Brownout Farm Diagnosis (Chẩn đoán sụt áp & mất điện dàn máy)

## 1. Triệu chứng phân biệt giữa Chớp điện (Brownout / Voltage dip) và Mất điện thật (Blackout)
- **Chớp điện 1-2s (Brownout):**
  - Đèn, quạt chớp tắt rồi có lại ngay trong 1-2s (thường do Recloser trạm hạ thế đóng cắt khi mưa bão, giông sét).
  - **PC / Server (mainboard Huananzhi, nguồn công suất lớn):** Không sụp. Bộ nguồn PC có dàn tụ lọc sơ cấp & thứ cấp lớn (Hold-up time 16ms - 25ms+), đủ gánh CPU/RAM qua cú chớp tức thời.
  - **Dàn Box Phone / Samsung S7:** Adapter nguồn rời hoặc mạch ổn áp của box phone rất nhạy cảm với sụt áp dưới ngưỡng (brownout threshold). Mạch ngắt bảo vệ kích hoạt ngay lập tức hoặc sạc ngắt nguồn -> **Toàn bộ phone S7 sụp nguồn/tắt ngúm ngay lập tức**.
- **Mất điện hoàn toàn (Blackout):**
  - Sau khoảng thời gian mất hẳn nguồn, PC sụp nguồn thật.
  - Windows Event Log ghi nhận `Event ID 41` (Kernel-Power: The system has rebooted without cleanly shutting down) và `Event ID 6008` (The previous system shutdown at <time> was unexpected).

## 2. Quy trình kiểm tra hiện trường O(1) qua PowerShell
```powershell
# 1. Kiểm tra thời điểm shutdown đột ngột gần nhất
Get-WinEvent -FilterHashtable @{LogName='System'; Id=6008,41} -MaxEvents 5 | Format-Table TimeCreated, Id, Message -AutoSize

# 2. Kiểm tra thời điểm hệ thống boot lại (Event 6005)
Get-WinEvent -FilterHashtable @{LogName='System'; Id=6005} -MaxEvents 5 | Format-Table TimeCreated, Id, Message -AutoSize

# 3. Tính khoảng thời gian mất nguồn:
# Delta = (TimeCreated Event 6005) - (Time trong Message Event 6008)
```

## 3. Bản chất phần cứng & Hành vi tự phục hồi
- **Server Kibe (Main Huananzhi X99-F8D):**
  - Mặc định bật `Restore on AC Power Loss: Power On` trong BIOS.
  - Khi có điện trở lại, máy tự kích nguồn boot vào Windows mà không cần bấm nút nguồn vật lý.
- **Dàn Samsung Galaxy S7 (ROM Gốc vs ROM Mod):**
  - **ROM Gốc:** KHÔNG tự bật nguồn khi có điện lại. Khi có nguồn trở lại, máy chỉ nhận sạc pin (màn hình LPM) hoặc ở trạng thái tắt, bắt buộc phải bấm nút nguồn vật lý.
  - **ROM Mod:** Đã patch auto-boot on charge (`/system/bin/lpm`) thì sẽ tự động khởi động vào OS ngay khi có nguồn sạc trở lại.
- **Khác biệt nhánh điện giữa các máy (Admin vs Kibe):**
  - Nếu máy Admin uptime liên tục hàng chục tiếng mà không có Event 41/6008 trong khi Kibe sập:
    - Chứng minh sự cố chỉ xảy ra cục bộ trên nhánh điện / pha điện riêng của cụm Kibe.
    - Kiểm tra nhiệt độ mặt ổ cắm và chuôi phích cắm (dùng mu bàn tay chạm nhẹ bề mặt nhựa cách điện): Nếu MÁT RƯỢI -> loại trừ ổ cắm Sino bị move/cháy tiếp điểm, khẳng định do điện lưới bên ngoài hoặc CB nhánh cấp riêng.

## 4. Kỷ luật Gate 6 & Chống Spam MEDIA Rác (Bài học phiên 15/09/2026)
- **Vấn đề cốt lõi:** Khi thảo luận kỹ thuật/hạ tầng (điện, UPS, mạng, Shopee), Agent máy móc trigger Gate 6 chụp screencap điện thoại S7 (máy đang ngủ / Dozing) gửi ra ảnh đen ngòm gây loãng và khó chịu cho người dùng.
- **Quy tắc kích hoạt Gate 6 chuẩn (Action Verb + Artifact):**
  - **CHỈ kích hoạt khi:** Báo cáo kết quả của một HÀNH ĐỘNG THỰC THI (Action Verb + Artifact) đã chạy thực tế trên thiết bị/farm (batch, test can thiệp, fix bug thiết bị, canary, recovery).
  - **TUYỆT ĐỐI CẤM kích hoạt khi:**
    - Đang trao đổi, tư vấn kỹ thuật, phân tích hạ tầng (điện, UPS, mạng, router, ổ cắm, mua sắm).
    - Task read-only / monitoring chỉ đọc log hoặc kiểm tra hiện trường lý thuyết.
  - **CẤM SPAM:** Cấm chụp screencap màn hình đen (mWakefulness=Dozing) gửi cho user khi không có thao tác can thiệp màn hình thật.

## 5. Cấu hình UPS khuyến nghị & Tiêu chuẩn Hạ tầng Toàn Farm
- **Quy mô toàn Farm (160 S7 + 2 PC Dual Xeon + 4 Aruba AP + Ruijie):**
  - **Đặc tả thiết kế chi tiết:** Xem tại `D:/Taadaa/AI-Tools/docs/infrastructure/farm-ups-power-backup-specs.md`.
  - **Topology bắt buộc:** **Online Double Conversion (True Online)** với thời gian chuyển mạch **0ms**.
  - **Lý do sống còn:** 160 phone S7 chạy bo mạch không pin (dummy battery), rất nhạy cảm với sụt áp vi mô; UPS Line-Interactive (độ trễ relay 4ms–8ms) có nguy cơ gây brownout sập nguồn hàng loạt bo mạch S7.
  - **Công suất định mức:** Tối thiểu 5kVA / 4.5kW đến 6kVA / 6kW (tải thực tế ~2.22kW, chạy ở mức 37% - 50% tải an toàn).
  - **Bảo vệ đi kèm:** Chống sét lan truyền SPD Type 2 (40kA), tiếp địa $R_{\text{earth}} \le 4\,\Omega$, RCBO 30mA, và cầu dao bảo trì Manual Bypass.
  - **Tự động hóa:** Tích hợp NUT qua Coordinator cảnh báo Telegram ID `1076231895`, kích hoạt `TAT_FARM_KHAN_CAP.bat` sau 5 phút mất điện.
- **Quy mô nhỏ lẻ / Đơn lẻ (1 PC trạm hoặc cụm 4 Box S7):**
  - Có thể dùng Line-Interactive sóng sin chuẩn 1000VA – 1500VA (600W – 900W) để chống sập ngang hỏng SSD/SQLite khi chớp nháy điện.
