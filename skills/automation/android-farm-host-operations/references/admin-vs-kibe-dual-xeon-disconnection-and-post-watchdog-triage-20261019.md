# Chẩn Đoán Khác Biệt Giữa Kibe vs Admin Dual Xeon & Rớt Kết Nối S7 Sau 2 Phiên Chạy (19/10/2026)

## 1. Hiện Tượng & Nghịch Lý Thực Tế
- Cả 2 máy Kibe và Admin đều là máy trạm Dual Xeon chạy Windows 10, quản lý farm Samsung S7.
- Trước mỗi ca chạy, máy tính đều được reboot sạch sẽ (`farm_preflight_daily_reset.py`).
- Cả 2 máy đều đã có Watchdog dọn dẹp port 5038 (`xiaowei_idle_auto_close_watchdog.py`) chạy ngầm 2 phút/lần + Preflight kill trước ca.
- **Nghịch lý sau 2 phiên chạy (khoảng 3–4 tiếng cày cuốc):**
  - Máy Kibe duy trì kết nối ổn định, rất ít khi rớt máy.
  - Máy Admin luôn bị văng kết nối S7 nhiều hơn hẳn (thường tập trung ở Box 4, dải M261–M280).

## 2. Bản Chất Kỹ Thuật (Tại Sao Watchdog 5038 Không Giải Quyết Được Hết)
1. **Ranh giới phần mềm vs Phần cứng:**
   - Watchdog dọn port 5038 chỉ xử lý lớp socket mạng và tiến trình mồ côi `adb.exe -P 5038` do phần mềm Tiểu Vi spawn ra.
   - Dọn một cổng giao tiếp **hoàn toàn không đồng nghĩa với reset thiết bị USB**, không giải phóng được các I/O request packet (IRP) bị treo dở trong driver stack của Windows, và không thể làm sạch thanh ghi phần cứng của controller USB.
2. **Khác biệt chipset & Bộ đệm EHCI USB 2.0:**
   - **Kibe (Chipset C602 / EHCI `1C2D`, `1C26`):** Bộ đệm USB phần cứng lớn hơn, khả năng nuốt các xung nhịp microframe dồn dập tốt hơn.
   - **Admin (Huananzhi X99-F8D / C610 EHCI `8D26`, `8D2D`):** Bộ đệm microframe rất nhỏ và nhạy cảm. Sau 2 phiên chạy, hàng chục ngàn lệnh shell (`dumpsys`, `input`, `screencap`) làm tràn đệm microframe dẫn đến kẹt cứng thanh ghi phần cứng (hardware lockup). Driver Windows của dòng này từ chối lệnh reset mềm (`Disable-PnpDevice` ném `HRESULT 0x8004100c - NotImplemented`).
3. **Độ trễ ngắt (DPC/Interrupt Latency) từ tiến trình FFmpeg:**
   - Máy Kibe chỉ chạy điều phối nhẹ nhàng, CPU và Disk I/O rất rảnh.
   - Máy Admin vừa gánh 80 máy, vừa chạy liên tục các tiến trình nặng: **FFmpeg render video ngầm** ở `D:\video goc may 2` và tool cào tải video (`run_admin_downloader`).
   - Tải CPU và Disk I/O cao làm tăng độ trễ xử lý ngắt phần cứng của driver USB. Các gói tin bắt tay heartbeat `A_SYNC` giữa `adb.exe` và S7 bị chậm trễ quá 2.5s dẫn đến socket bị đứt và ADB đánh dấu máy rớt.
4. **Hiện tượng tích tụ nhiệt & suy hao cáp Box 4:**
   - Sau 3–4 tiếng chạy liên tục trong ca, nhiệt độ trong thùng Box 4 tăng cao. Cổng sạc Micro-USB đuôi máy S7 và đầu giắc cáp bị nóng lên làm tăng điện trở tiếp xúc.
   - Đường nguồn 5V VBUS vẫn thông nên máy vẫn báo sạc, nhưng 2 chân dữ liệu (D+/D-) bị sụt áp làm mất tín hiệu data.
   - Vì nguồn 5V không ngắt, nhân Linux trên S7 không kích hoạt uevent để khởi động lại daemon `adbd`, khiến thiết bị rơi vào `offline` hoặc biến mất vĩnh viễn khỏi ADB cho đến khi máy tính reboot để ngắt nguồn VBUS chớp nhoáng.

## 3. Quy Trình Khoanh Vùng & Thử Nghiệm A/B
1. **Kiểm tra tương quan tải FFmpeg:** Tạm dừng hoặc dời lịch render FFmpeg ra ngoài khung giờ chạy 2 phiên của ca nuôi; đối soát tỷ lệ rớt ADB để xác nhận mức độ ảnh hưởng của CPU/DPC latency.
2. **Kiểm tra nhánh Hub Box 4:** Chuyển cụm Box 4 sang card PCIe USB 3.0 rời (chip Renesas uPD720201 có nguồn phụ SATA) để tách hẳn tải khỏi 2 controller EHCI onboard của main X99.
3. **Đối soát nhiệt độ và cáp:** Vệ sinh cồn các chân tiếp xúc Micro-USB của dải máy hay rớt, thay thế các sợi cáp đã dão bằng cáp đồng ngắn AWG 24/28 chất lượng cao.
