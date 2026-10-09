# Phone Farm USB Bus Saturation, Controller Reset & Hardware Invariants (80+ Devices)

## 1. Sai Lầm Phổ Biến: Đổ Lỗi Cho "Power Balance" (Power Plan)
- Khi dàn farm 80 máy cắm vào 1 PC bị văng kết nối đồng loạt trên ADB và phần mềm điều khiển (Tiểu Vi / 玖卫), nhiều người nhầm tưởng do Windows Power Plan ("Balanced", USB Selective Suspend, PCIe Link State Power Management ASPM).
- **Thực tế kỹ thuật:** USB Selective Suspend chỉ kích hoạt khi cổng USB ở trạng thái IDLE (nghỉ hoàn toàn). Khi 80 điện thoại đang kết nối và chạy automation hoặc stream video, bus USB luôn có dữ liệu truyền qua liên tục. Windows không bao giờ đưa cổng vào chế độ ngủ lúc này. Đổi Power Plan sang High Performance không giải quyết được gốc rễ.

## 2. Nguyên Nhân Gốc Rễ Trên Dàn Farm Lớn (80+ Thiết Bị)
1. **Nghẽn Bus USB 2.0 (EHCI Saturation):**
   - Trên các bo mạch chủ server/X99 (ví dụ Huananzhi X99-F8D), nếu cổng Intel USB 3.0 (xHCI Controller `8D31`) bị tắt trong BIOS (`Present: False` / `CM_PROB_PHANTOM`), toàn bộ 80 máy sẽ bị dồn vào 2 chip điều khiển USB 2.0 cổ điển (EHCI `8D26` và `8D2D`).
   - Tổng băng thông lý thuyết USB 2.0 chỉ là **480 Mbps (~40-50 MB/s)** cho toàn bộ thiết bị chung kênh.
   - Khi kịch bản auto đồng loạt kéo `adb screencap` (ảnh PNG 2MB), `uiautomator dump` (XML UI), hoặc nạp video qua ADB push, tốc độ bus bị quá tải tức thì, gây lỗi `Babble error` hoặc `Controller Hang`.
2. **Tràn Endpoint (Endpoint Exhaustion):**
   - Mỗi điện thoại Android (Composite Device: ADB + MTP + Modem) ngốn 4 đến 6 endpoints.
   - 80 điện thoại + cascaded USB hubs vượt quá số lượng endpoint contexts tối đa của controller bo mạch chủ $\rightarrow$ Windows báo lỗi `Port Reset Failed` hoặc `Set Address Failed` và ngắt hàng loạt cổng.

## 3. Cứu Nhanh Tại Chỗ (5 Giây, Không Cần Reset Toàn Bộ PC)
Khi thanh ghi phần cứng của chip USB Controller bị treo, không cần khởi động lại toàn bộ máy tính:
Tạo script `reset_usb_bus.bat` (chạy với quyền Administrator):
```cmd
@echo off
echo Dang kill ADB Server...
taskkill /F /IM adb.exe >nul 2>&1

echo Dang reset USB Host Controller...
powershell -Command "Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Enhanced Host Controller' } | Disable-PnpDevice -Confirm:$false; Start-Sleep 2; Get-PnpDevice | Where-Object { $_.FriendlyName -match 'Enhanced Host Controller' } | Enable-PnpDevice -Confirm:$false"

echo Dang khoi dong lai ADB Server...
"C:\Program Files (x86)\xiaowei\tools\adb.exe" -a nodaemon server
```
Lệnh PnP trên sẽ cắt xung nhịp và cấp lại điện cho controller, ép bus USB khởi tạo lại và toàn bộ máy Android bắt tay lại ngay lập tức.

## 4. Giải Pháp Phần Cứng Bền Vững Cho Farm
1. **Bật xHCI trong BIOS:** Vào BIOS mainboard (tab `Advanced` hoặc `PCH-IO Configuration` $\rightarrow$ `USB Configuration`), bật `XHCI Mode = Enabled` và `Route USB ports to XHCI = Enabled`. USB 3.0 có băng thông 5.000 Mbps (gấp 10 lần USB 2.0).
2. **Cắm sang cổng USB 3.0 màu Xanh Dương:** Cắm tản các dây USB tổng của Hub sang các cổng USB 3.0 ở mặt sau case, tránh cắm dồn vào 1 cụm cổng USB 2.0 màu đen.
3. **Trang bị Card PCIe USB 3.0 Rời:** Đối với farm 80–100 máy, bắt buộc dùng thêm card mở rộng PCIe x1/x4 dùng chip chuyên dụng (Renesas/NEC uPD720201 hoặc VIA VL805) có đầu cấp nguồn phụ SATA/Molex trực tiếp từ PSU để tách biệt hoàn toàn tải bus khỏi bo mạch chủ.

## 5. Giảm Tải Cấp Code Automation (Stagger Delay & Phase Drift)
- Tránh gọi `adb screencap` hoặc đẩy video đồng loạt cùng một giây cho 20–30 máy.
- Chèn độ trễ so le (stagger) từ 1.5 – 2.0 giây giữa các lượt kích hoạt máy để giữ lưu lượng truyền tải trên bus USB luôn ổn định.
- **Bẫy lệch pha (Phase Drift):** Giới hạn `max_workers = 40` và stagger lúc khởi động (`build_machine_launch_plan`) chỉ có tác dụng lúc bắt đầu ca. Sau 10–15 phút chạy lướt feed, độ dài video khác nhau làm phân rã tính so le ban đầu. Tại các thời điểm ngẫu nhiên, 15–20 máy kết thúc video và đồng loạt chụp màn hình / dump XML cùng 1 giây, tạo đỉnh nhọn (I/O Spike 30MB/s) đánh sập bus USB 2.0. Do đó, việc nâng cấp phần cứng lên USB 3.0 (xHCI) là điều kiện tiên quyết.

## 6. Chốt Chặn Phục Hồi Tự Động Trước Script (Safe USB Preflight Guard)
Khi người dùng muốn tự động reset bus USB trước mỗi kịch bản/batch nhưng yêu cầu **tuyệt đối không được reset nếu có máy đang bận lock**, không được phép "reset mù" vô điều kiện. Áp dụng quy chuẩn 2 tầng trong `safe_usb_guard.py`:

1. **Tầng 1 (Chốt an toàn Device Locks):**
   - Quét thư mục lock trung tâm `~/.codex/device-locks/*.lock.json`.
   - Nếu phát hiện **BẤT KỲ máy nào đang giữ lock** (`status` thuộc `active`, `running`, `locked`, `busy`) VÀ tiến trình sở hữu vẫn còn sống (`owner_process_alive(data)`):
     $\rightarrow$ **CHẶN ĐỨNG RESET (HARD BLOCK):** Thoát ngay lập tức với mã lỗi, cấm tuyệt đối can thiệp vào USB controller để bảo vệ luồng đang chạy.
2. **Tầng 2 (Khám sức khỏe ADB có điều kiện):**
   - Khi và chỉ khi **toàn bộ fleet rảnh (0 active locks)**:
     * Chạy lệnh `adb devices` có timeout chặt chẽ (8 giây).
     * Nếu ADB phản hồi nhanh và số lượng máy online đạt chuẩn (ví dụ $\ge 50/80$ máy): **BỎ QUA RESET**, nhả cho script chạy ngay (độ trễ < 0.05s).
     * Chỉ kích hoạt `reset_usb_bus.bat` khi: ADB bị treo timeout (>8s) HOẶC số lượng máy online giảm nghiêm trọng do rớt cụm Hub.
   - Sau khi reset, chờ 5s để USB bus bắt tay lại và kiểm tra lại `adb devices` trước khi bàn giao cho worker chính.

