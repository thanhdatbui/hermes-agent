# USB Power Management, Selective Suspend & ADB Offline Recovery on High-Density Farm PCs

## 1. Bản Chất Sự Cố: "Đèn Box Sáng Nhưng Máy Văng ADB / Offline"
- **Nghịch lý thực tế:** Trên box 80 máy, đèn LED tại từng cổng sạc vẫn sáng trưng, điện thoại vẫn hiển thị đang sạc pin, nhưng trong lệnh `adb devices` máy lại rơi vào trạng thái `offline` hoặc biến mất hoàn toàn (`missing`).
- **Nguyên nhân gốc rễ:**
  1. **Nguồn cấp 5V vs Kênh truyền dữ liệu D+/D-:** Đèn box sáng và sạc pin chỉ cần 2 chân VBUS (5V) và GND. Kênh dữ liệu ADB yêu cầu 2 chân dữ liệu D+ và D- cùng bộ điều khiển USB trên Host PC duy trì polling liên tục.
  2. **Windows Power Management (USB Selective Suspend & PCIe ASPM):** Trên profile mặc định (`Balanced`), khi cổng USB hoặc PCIe tạm lắng, Windows kernel gửi Suspend IRP hoặc hạ xung PCIe. Tuy nhiên, **đây KHÔNG PHẢI nguyên nhân gây văng hàng loạt khi farm đang chạy (dù là stream Xiaowei hay chạy script auto)**. Tính năng Selective Suspend/ASPM chỉ kích hoạt khi link IDLE. Khi thiết bị đang hoạt động hoặc auto script đang polling ADB, bus liên tục có traffic, Windows không bao giờ ru ngủ cổng. Đổi Power Plan sang High Performance / tắt Selective Suspend là điều kiện cần (hygiene), nhưng KHÔNG giải quyết được gốc rễ văng hàng loạt.
  3. **Tràn Băng Thông & Đơ Hardware Controller USB 2.0 (EHCI) Khi Chạy Auto Script (NGUYÊN NHÂN GỐC KHI XIAOWEI ĐÃ TẮT):**
     - **Hiện trạng phần cứng:** Trên các mainboard server/dual CPU (như Huananzhi X99-F8D), chip Intel xHCI (USB 3.0 controller `8D31`) thường bị Disable trong BIOS hoặc không nhận diện (`Present: False / CM_PROB_PHANTOM`). Toàn bộ 80 máy dồn hết vào 2 bộ điều khiển cổ lỗ sĩ USB 2.0 (EHCI `8D26` và `8D2D`).
     - **Băng thông USB 2.0 quá thấp (480 Mbps):** Chia cho 40 máy/controller chỉ còn ~1 MB/s mỗi máy.
     - **Nghẽn do I/O của Automation Script:** Dù Xiaowei đã tắt (watchdog đóng sau 20 phút), khi 10-20 workers auto đồng loạt gọi `screencap` (ảnh PNG 1080p ~1.5-2MB), `uiautomator dump` (kéo XML), hoặc `adb push` video, lưu lượng dữ liệu burst tức thời làm nghẽn nghẹt bus USB 2.0.
     - **Lỗi phần cứng trong Event Log:** Windows System Log ghi nhận: `Unknown USB Device (Port Reset Failed)`, `Set Address Failed`, `Configuration Descriptor Request Failed`. Controller EHCI bị treo cứng thanh ghi phần cứng (Hardware Registers Hang / Babble Error) $\rightarrow$ ngắt luôn cổng hub $\rightarrow$ hàng loạt máy biến mất khỏi Device Manager $\rightarrow$ ADB rớt $\rightarrow$ auto script văng toàn bộ.
  4. **Tại sao Reset PC lại hết mà `adb kill-server` vô tác dụng?** Khi thanh ghi chip điều khiển USB trên bo mạch chủ bị treo ở tầng phần cứng (hardware deadlock), tầng phần mềm Windows không thể re-enumerate lại các cổng hub. Lệnh `adb kill-server` chỉ restart tiến trình user-space, không chạm được vào phần cứng. **CHỈ CÓ reboot PC (hoặc rút cắm lại cáp USB tổng của Hub)** mới kích hoạt tín hiệu System Hardware Bus Reset để xóa sạch thanh ghi và cấp lại địa chỉ (`Set Address`) cho các hub.
  5. **Kẹt luồng & Deadlock trong tiến trình `adb.exe`:** Một tiến trình `adb.exe` duy nhất trên PC quản lý 80 cặp read/write threads. Khi bus USB bị chập chờn hoặc rớt gói tin, vòng lặp socket I/O của adb server bị starvation/deadlock.
  6. **Nhiệt độ & Sụt áp nguồn trên Hub công nghiệp:** Hub 16/20 cổng gánh 80 máy liên tục rất nóng chip điều khiển và có thể sụt áp 5V, khiến hub tự ngắt tín hiệu bảo vệ.

---

## 2. Phân Biệt 3 Tầng Trạng Thái Khi Triage 80 Máy Farm

| Trạng Thái | Hiện Tượng trong `adb devices` | Tầng Giao Tiếp Bị Lỗi | Bản Chất Kỹ Thuật | Phương Án Xử Lý |
|---|---|---|---|---|
| **ONLINE (`device`)** | `<serial>    device` | Bình thường | Cáp tốt, USB nhận diện, ADB daemon handshake RSA thành công. | Sẵn sàng chạy workflow. |
| **OFFLINE Protocol** | `<serial>    offline` | Phần mềm / Daemon | Cáp và chip USB composite vẫn nhận diện trong Windows Device Manager (`Status: OK`), nhưng daemon `adbd` trên điện thoại bị crash, đơ OS Android, hoặc bị Xiaowei lock handle. | 1. `adb -s <serial> reconnect`<br>2. Bấm sáng màn hình / reboot điện thoại.<br>3. Kiểm tra Hub USB. |
| **MISSING Vật Lý** | Serial biến mất hoàn toàn khỏi danh sách | Phần cứng / Bus USB | Windows Device Manager không còn nhìn thấy thiết bị (`CM_PROB_PHANTOM` hoặc mất hẳn khỏi bus). Cáp USB tuột, cổng hub mất điện, hoặc điện thoại sập nguồn cạn pin. | Cắm lại cáp USB vật lý, kiểm tra nguồn sạc box. |

---

## 3. Quy Trình Chuẩn Hóa Windows Host Toàn Diện (PC Kibe & PC Admin)

Mọi máy tính PC đóng vai trò Controller cho Phone Farm (cắm >30 thiết bị USB) BẮT BUỘC phải thực hiện các bước tối ưu hóa sau:

### Bước 1: Kích hoạt High Performance Power Scheme
```bash
# Kích hoạt profile High Performance
powercfg -s 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
```

### Bước 2: Tắt Triệt Để USB Selective Suspend (Cả AC và DC)
```bash
powercfg /SETACVALUEINDEX 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0
powercfg /SETDCVALUEINDEX 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0
powercfg /SETACTIVE 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
```

### Bước 3: Tắt PCIe Link State Power Management (ASPM)
```bash
powercfg /SETACVALUEINDEX 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 501a4d13-42af-4429-9fd1-a8218c268e20 ee12f906-d277-404b-b6da-e5fa1a576df5 0
powercfg /SETDCVALUEINDEX 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 501a4d13-42af-4429-9fd1-a8218c268e20 ee12f906-d277-404b-b6da-e5fa1a576df5 0
powercfg /SETACTIVE 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
```

### Bước 4: Khóa Cứng Registry Nhân Windows Cho Dịch Vụ USB & Hubs (PowerShell)
```powershell
# Khóa dịch vụ USB hệ thống
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\USB"
if (!(Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
Set-ItemProperty -Path $regPath -Name "DisableSelectiveSuspend" -Value 1 -Type DWord -Force

# Tắt chế độ tiết kiệm điện trên toàn bộ các Hubs và Controllers trong Device Manager
$hubs = Get-PnpDevice -Class 'USB' | Where-Object { $_.FriendlyName -match 'Hub|Controller' }
foreach ($h in $hubs) {
    $instanceId = $h.InstanceId
    $keyPath = "HKLM:\SYSTEM\CurrentControlSet\Enum\$instanceId\Device Parameters"
    if (Test-Path $keyPath) {
        Set-ItemProperty -Path $keyPath -Name "EnhancedPowerManagementEnabled" -Value 0 -Type DWord -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $keyPath -Name "AllowIdleIrpInWorkingState" -Value 0 -Type DWord -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $keyPath -Name "DeviceSelectiveSuspended" -Value 0 -Type DWord -ErrorAction SilentlyContinue
    }
}
```

---

## 4. Kỷ Luật An Toàn Tuyệt Đối: Cấm Giết ADB Server Bừa Bãi
- Khi phát hiện một vài thiết bị rơi vào trạng thái `offline`, **CẤM TUYỆT ĐỐI chạy `adb kill-server`** nếu trên cùng máy tính đó đang có các luồng automation khác (`tiktok_workflow`, `run_post.py`, feed sessions) đang thực thi.
- Lệnh `adb kill-server` sẽ lập tức bẻ gãy socket kết nối của toàn bộ 70-80 máy khác, khiến tất cả các tiến trình automation đang chạy bị crash đồng loạt và rơi vào trạng thái fail hàng loạt.
- **Thao tác an toàn:**
  1. Chỉ gọi reconnect đích danh trên serial bị lỗi: `adb -s <serial> reconnect` hoặc `adb -s <serial> reconnect offline`.
  2. Nếu không lên, can thiệp bấm màn hình vật lý trên đúng thiết bị đó, giữ nguyên trạng thái các thiết bị đang online.

---

## 5. Chiến Lược Giải Quyết Triệt Để Tầng Phần Cứng (Mainboard & USB Controller)

Khi gặp hiện tượng hàng loạt máy văng trong ADB/Xiaowei và **chỉ reset PC mới nhận lại**:

### Bước 1: Kiểm Tra Hiện Trạng Controller USB Trên Host PC (Triage O(1))
```powershell
Get-PnpDevice | Where-Object { $_.Class -match 'USB' -and $_.FriendlyName -match 'Controller' } | Select-Object Status, Problem, FriendlyName, HardwareID, Present
```
- **Red Flag nghiêm trọng:** Nếu thấy `Intel(R) USB 3.0 eXtensible Host Controller` mang cờ `Present: False / CM_PROB_PHANTOM` trong khi các máy chỉ bám vào `USB Enhanced Host Controller (EHCI 8D26/8D2D)`:
  $\rightarrow$ Bo mạch chủ đang chạy 100% bằng chuẩn USB 2.0 cổ (tối đa 480 Mbps chia cho 80 máy).
  $\rightarrow$ Mọi tinh chỉnh Power Plan Windows đều vô nghĩa nếu controller USB 2.0 bị quá tải I/O phần cứng.

### Bước 2: Khắc Phục Phần Cứng Triệt Để
1. **Kiểm tra BIOS Bo Mạch Chủ (Huananzhi X99 / Server Boards):**
   - Vào BIOS $\rightarrow$ mục **Advanced / USB Configuration**:
   - Kiểm tra **XHCI Mode / USB 3.0 Controller**: Bắt buộc chuyển từ *Disabled/Auto* sang **Enabled**.
   - Bật lại xHCI sẽ mở ra băng thông 5.000 Mbps (gấp 10 lần) và khả năng xử lý packet đa thiết bị ổn định hơn gấp nhiều lần.
2. **Trang Bị Card PCIe USB 3.0 Mở Rộng Độc Lập:**
   - Chuẩn bắt buộc cho các trạm Farm $\ge 80$ máy: Cắm thêm card PCIe USB 3.0 có chip điều khiển riêng (Renesas/NEC uPD720201, ASMedia ASM1142 hoặc FL1100).
   - Tách các nhánh Hub 16/20 cổng cắm vào các controller độc lập, không cắm dồn toàn bộ 80 máy vào cổng USB sau của bo mạch chủ.
3. **Cơ Chế Bóp Nghẹt I/O (Rate-Limiting) Cho Automation Scripts:**
   - Khi chạy đa luồng (multi-workers), tuyệt đối không để 10-20 máy đồng loạt kéo ảnh `screencap` 1080p hay `adb push` file video nặng cùng một giây.
   - Bổ sung semaphore hoặc stagger delay (1-2s) giữa các lệnh truyền file/screencap để chống tràn bộ đệm USB transfer ring.

