# USB Hub Hardware Outage vs Software Recovery Triage Guide

## 1. CÂU HỎI CỐT LÕI: KHI NÀO GIẢI CỨU ĐƯỢC BẰNG PHẦN MỀM & KHI NÀO BẮT BUỘC THAO TÁC VẬT LÝ?

Khi gặp Farm Alert thiết bị dính `device offline` hoặc `device not found`, Coordinator/Worker BẮT BUỘC phân biệt rõ 2 tình huống kỹ thuật trước khi quyết định hành động:

| Tiêu chí | Nhóm 1: Giải Cứu Bằng Phần Mềm (Software-Rescuable) | Nhóm 2: Sự Cố Phần Cứng Hub USB (Physical Action Required) |
| :--- | :--- | :--- |
| **Bản chất** | Lỗi logic ở tầng tiến trình ADB / Socket streaming / ATX agent. | Sụt áp adapter nguồn, kẹt chip controller Hub USB, lỏng cáp uplink. |
| **Trạng thái PnP Windows** | `Get-PnpDevice`: Thiết bị `Status: OK`, `Present: True`. Không có thiết bị con mang lỗi descriptor. | `Get-PnpDevice`: Xuất hiện `Unknown USB Device (Port Reset Failed)`, `Configuration/Device Descriptor Request Failed`. |
| **Hành vi ADB** | `adb reconnect` hồi sinh thiết bị về `device` trong 1-2 giây. | `adb reconnect` vẫn trả về `offline` hoặc `not found`, `adb shell` văng `device offline`. |
| **Khả năng can thiệp phần mềm** | 100% tự động qua ADB command / Watchdog healer. | 0% qua phần mềm. Windows kernel chặn reset (`0x80041001`), hub thiếu IC điều khiển nguồn từng cổng (PPPS). |
| **Phân tầng xử lý** | **L0 Retry / Healer**: Kích hoạt socket reset và tiếp tục workflow. | **L3 BLOCKED**: Báo cáo bằng chứng PnP và hướng dẫn thao tác vật lý tại dàn. |

---

## 2. NHÓM 1: CÁC TRƯỜNG HỢP GIẢI CỨU ĐƯỢC BẰNG PHẦN MỀM

### A. Triệu chứng nhận diện
- Thiết bị hiển thị `offline` trên `adb devices` hoặc shell bị đơ (latency > 2.5s) nhưng trên Windows Device Manager điện thoại vẫn nhận đủ driver `SAMSUNG Android ADB Interface`.
- Thường gặp khi:
  1. XiaoWei (app con gấu) stream video màn hình đồng thời trên 80 máy gây nghẽn socket reverse port 5037 (>15s timeout, OS error 10061).
  2. Máy vừa kết thúc swipe feed hoặc vừa chạy soft-reboot, socket ADB bị stall ở bước cleanup.
  3. Tiến trình `adb.exe` server trên máy chủ local bị quá tải bộ đệm I/O.

### B. Lệnh giải cứu phần mềm O(1)
1. **Reset socket riêng lẻ cho từng serial (Ưu tiên số 1 - An toàn nhất)**:
   ```bash
   "C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <serial> reconnect
   # hoặc:
   "C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <serial> reconnect offline
   ```
2. **Khởi động lại ADB Server Local Kibe (Khi nhiều máy bị nghẽn socket đồng thời)**:
   ```bash
   "C:\Program Files (x86)\xiaowei\tools\adb.exe" kill-server
   "C:\Program Files (x86)\xiaowei\tools\adb.exe" start-server
   ```
   *CẢNH BÁO TỬ HUYỆT*: TUYỆT ĐỐI CẤM chạy `kill-server` trên remote Admin (`192.168.110.119:5037`) vì nguy cơ sập daemon ADB từ xa không tự khởi động lại được.
3. **Cơ chế Watchdog Tự Hành**:
   Triển khai `farm-adb-transport-healer` chạy ngầm định kỳ 3 phút: kiểm tra `adb shell echo 1` timeout 2.5s; nếu kẹt thì tự động phát `adb reconnect` và `keyevent 224` để thông pipe.

---

## 3. NHÓM 2: SỰ CỐ PHẦN CỨNG HUB USB (BẮT BUỘC THAO TÁC VẬT LÝ)

### A. Căn nguyên kỹ thuật tầng sâu
1. **Sụt áp adapter nguồn (Under-voltage / Brownout)**:
   - Các Hub USB 20 cổng công nghiệp (sử dụng chip controller QinHeng/WCH như `CH334`, `CH335`, `CH338` mang VID `1A86`, PID `8095`) cấp nguồn đồng thời cho 20 máy Samsung S7.
   - Khi nhiều máy cùng bật màn hình hoặc sạc nhanh, adapter nguồn của Hub bị tụt áp dưới ngưỡng 4.75V. Bộ điều khiển Hub kích hoạt cơ chế bảo vệ quá dòng (Over-current protection) và ngắt bus truyền dữ liệu D+/D- của các cổng con bị sụt áp.
2. **Kẹt chu kỳ Port Reset (Port Reset Loop)**:
   - Khi điện thoại cố gắng kết nối lại, controller Hub gửi tín hiệu reset cổng nhưng điện áp đường truyền không ổn định, khiến handshake thất bại.
   - Windows USB Hub Driver (`usbhub3.sys` / `usbhub.sys`) đánh dấu cổng ở trạng thái `Port Reset Failed` (Problem Code 43 / `CM_PROB_FAILED_POST`).
3. **Vì sao phần mềm không thể cứu?**:
   - **Không có phần cứng PPPS (Per-Port Power Switching)**: Các hub USB thương mại không trang bị IC đóng/ngắt nguồn điện riêng lẻ cho từng cổng (như chip TPS2553). Nguồn 5V VBUS được đấu song song trên cùng 1 rail. Do đó, các công cụ phần mềm như `uhubctl` hay script WMI không thể cắt điện để buộc điện thoại khởi động lại giao tiếp USB.
   - **Windows Driver Lockout**: Khi gọi `Disable-PnpDevice` qua PowerShell đối với thiết bị composite hoặc port lỗi, Windows kernel trả về `Generic failure (0x80041001)` vì driver bus USB khóa quyền can thiệp cấp người dùng.
   - **ADB mất hoàn toàn Endpoint**: ADB chỉ hoạt động khi Windows đã cấp Descriptor và thiết lập USB Pipe. Khi Hub đã chặn cổng ở tầng vật lý, ADB hoàn toàn không thể gửi bất kỳ gói tin nào tới điện thoại.

### B. Quy trình Triage O(1) kiểm chứng lỗi phần cứng Hub
Khi có danh sách máy nghi vấn, chạy script PowerShell truy vấn topology PnP:
```powershell
$offline_serials = @('<serial1>', '<serial2>', ...)
foreach ($s in $offline_serials) {
    $dev = Get-PnpDevice | Where-Object { $_.InstanceId -like "*$s*" } | Select-Object -First 1
    if ($dev) {
        $p = (Get-PnpDeviceProperty -InputObject $dev -KeyName 'DEVPKEY_Device_Parent' -ErrorAction SilentlyContinue).Data
        Write-Host "$s -> Parent: $p"
    }
}
```
Sau đó kiểm tra trạng thái toàn bộ các thiết bị con trên Hub Controller chung:
```powershell
Get-PnpDevice | Where-Object { 
    $parent = (Get-PnpDeviceProperty -InputObject $_ -KeyName 'DEVPKEY_Device_Parent' -ErrorAction SilentlyContinue).Data
    $parent -like '*<Hub_Instance_ID>*'
} | Select-Object FriendlyName, InstanceId, Status, Present | Format-Table -AutoSize
```

**BẰNG CHỨNG XÁC THỰC 100% LỖI PHẦN CỨNG**:
- Xuất hiện các dòng:
  * `Unknown USB Device (Port Reset Failed)`
  * `Unknown USB Device (Configuration Descriptor Request Failed)`
  * `Unknown USB Device (Device Descriptor Request Failed)`
  * `Unknown USB Device (Set Address Failed)`
- Đa số máy lỗi (ví dụ 5–7 máy) cùng chia sẻ một chuỗi Parent Hub chung (ví dụ: `USB\VID_1A86&PID_8095\...`).

---

## 4. HƯỚNG DẪN XỬ LÝ VẬT LÝ DÀNH CHO NGƯỜI VẬN HÀNH (RUNBOOK)

Khi Coordinator xác định lỗi thuộc Nhóm 2:
1. **DỪNG MỌI LỆNH PHẦN MỀM**: Không cố chạy vòng lặp reconnect ngầm gây nghẽn bus ADB của 70+ máy còn lại.
2. **XÁC ĐỊNH VỊ TRÍ HUB**:
   - Dựa vào dải máy bị ảnh hưởng (ví dụ: M1, M14, M15, M16, M20 -> Hub dải M1–M20).
3. **THỰC HIỆN 1 TRONG 2 THAO TÁC VẬT LÝ TẠI DÀN**:
   - **Cách 1 (Hiệu quả nhất - Xả nguồn Hub)**:
     * Bấm công tắc nguồn của Hub USB 20 cổng sang vị trí OFF (hoặc rút phích cắm adapter nguồn của Hub ra khỏi ổ điện).
     * **Chờ 3 đến 5 giây** để toàn bộ tụ điện trên bo mạch Hub xả sạch điện tích.
     * Bật lại công tắc ON (hoặc cắm lại nguồn adapter).
   - **Cách 2 (Reset bus dữ liệu)**:
     * Rút đầu cáp USB vuông (cáp uplink Type-B hoặc Type-A) nối từ Hub vào máy tính điều phối Kibe.
     * Chờ 2 giây rồi cắm chắc chắn trở lại cổng USB trên PC.
4. **NGHIỆM THU SAU THAO TÁC VẬT LÝ**:
   - Chạy lệnh kiểm tra O(1): `python D:/Taadaa/tools/inspect_machine.py <N>`.
   - Toàn bộ máy sẽ chuyển sang trạng thái `device` và sẵn sàng nhận job nuôi acc / upload tiếp theo.
