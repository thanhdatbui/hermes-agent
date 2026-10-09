# Quy Trình Triage Sự Cố Phần Cứng Hub USB Qua Windows PnP Topology

## 1. Bối Cảnh & Nhận Diện Hiện Tượng
- **Dấu hiệu**: Farm alert bắn cảnh báo hàng loạt máy bị `device offline` hoặc `device '<serial>' not found` (ví dụ: `M1, M7, M14, M15, M16, M17, M20, M69, M74` dính `device offline`).
- **Nguyên nhân cốt lõi**:
  - Controller Hub USB 20 cổng (chip QinHeng/WCH `USB\VID_1A86&PID_8095`) bị kẹt trạng thái reset cổng vật lý (Port Reset Failed).
  - Sụt áp adapter nguồn cấp điện cho Hub 20 cổng.
  - Lỏng hoặc tiếp xúc kém cáp uplink USB nối từ Hub vào bo mạch máy tính.

---

## 2. Các Bước Điều Tra & Phân Cấp Hành Động (A–Z Triage)

### Bước 0: Preflight Live Batch Protection Gate (Chống Giết Nhầm Toàn Fleet)
- **CẤM TUYỆT ĐỐI**: Chạy ngay `taskkill -F -IM adb.exe` hoặc `adb kill-server` khi thấy danh sách máy lỗi!
- **Kiểm tra tiến trình đang chạy**:
  1. Rà soát file lock tại `~/.codex/device-locks/*.lock.json`.
  2. Kiểm tra PID tiến trình chạy batch:
     ```powershell
     powershell -Command "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Select-Object ProcessId, CommandLine"
     ```
  3. Nếu đang có một batch khác (ví dụ `row-5-200043` - PID 14956) đang chạy song song trên 50-70 máy còn lại, việc kill ADB server sẽ làm đứt kết nối và hỏng phiên của toàn bộ các máy khỏe.

---

### Bước 1: Sàng Lọc Trạng Thái Đích Danh Từng Máy (Per-Machine Filtering)
- Không bao giờ giả định toàn bộ danh sách trong alert đều đang chết. Luôn kiểm tra từng máy:
  ```bash
  python D:/Taadaa/tools/inspect_machine.py M<N>
  ```
  *(Lưu ý: Công cụ hỗ trợ cả định dạng `M1` lẫn `1`).*
- Nếu trong git-bash báo `adb: command not found`: Bắt buộc dùng đường dẫn tuyệt đối:
  ```bash
  "/c/Program Files (x86)/xiaowei/tools/adb.exe" devices
  ```
- **Bóc tách 2 nhóm**:
  - **Nhóm đã tự phục hồi (Online / Device)**: Xếp vào `NO_TOUCH_SCOPE`, không can thiệp (ví dụ M7, M17 đã online và đang chạy feed).
  - **Nhóm thực sự Offline**: Giữ lại để truy vết phần cứng.

---

### Bước 2: Truy Vấn Parent Hub Bằng Windows PnP Topology
Sử dụng PowerShell truy vấn thuộc tính `DEVPKEY_Device_Parent` để gom nhóm các serial lỗi theo Hub vật lý:

```powershell
$offline_serials = @('9885b64957334f5a46', 'ad061603104ee741e2', 'ad07170215e8f37ae0', 'ce011711201cae2704', 'ce0318237dec1ce60c', 'ce061606c21e153d03', 'ce12160c386c913101')
foreach ($s in $offline_serials) {
    $dev = Get-PnpDevice | Where-Object { $_.InstanceId -like "*$s*" } | Select-Object -First 1
    if ($dev) {
        $p = (Get-PnpDeviceProperty -InputObject $dev -KeyName 'DEVPKEY_Device_Parent').Data
        Write-Host "$s (Status: $($dev.Status), Present: $($dev.Present)) -> $p"
    } else {
        Write-Host "$s -> Not found in PnP"
    }
}
```

Nếu đa số máy (ví dụ 5/7 máy) cùng trỏ về 1 Hub chung (như `USB\VID_1A86&PID_8095\7&260de1da...`), ta xác định được Hub nghi vấn.

---

### Bước 3: Kiểm Tra Chi Tiết Trạng Thái Cổng Con Của Hub
Chạy lệnh kiểm tra toàn bộ các cổng con thuộc InstanceId của Hub:

```powershell
Get-PnpDevice | Where-Object { 
    $parent = (Get-PnpDeviceProperty -InputObject $_ -KeyName 'DEVPKEY_Device_Parent' -ErrorAction SilentlyContinue).Data
    $parent -like '*<Hub_Instance_Substring>*'
} | Select-Object FriendlyName, InstanceId, Status, Present, Problem | Format-Table -AutoSize
```

**Bằng chứng xác thực lỗi phần cứng**:
Nếu xuất hiện các dòng lỗi handshake descriptor:
- `Unknown USB Device (Port Reset Failed)`
- `Unknown USB Device (Configuration Descriptor Request Failed)`
- `Unknown USB Device (Device Descriptor Request Failed)`
- `Unknown USB Device (Set Address Failed)`

=> Khẳng định 100% chip điều khiển Hub USB hoặc nguồn adapter đã bị kẹt ở tầng bus phần cứng.

---

### Bước 4: Thử Nghiệm L0 & Giới Hạn Phần Mềm
- Thử khôi phục kết nối ADB transport:
  ```bash
  "/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> reconnect offline
  ```
- Nếu sau khi reconnect lệnh trả về thành công nhưng `adb devices` vẫn hiển thị `offline`, và PnP vẫn báo `Port Reset Failed` -> Phần mềm hoàn toàn không thể can thiệp được nữa.

---

### Bước 5: Phân Cấp Leo Thang (Escalation)
1. **Chuyển L3 BLOCKED**: Đánh dấu task BLOCKED kèm bằng chứng:
   - Danh sách serial bị ảnh hưởng.
   - Hub InstanceId cụ thể (`USB\VID_1A86&PID_8095\...`).
   - Danh sách lỗi PnP Descriptor (`Port Reset Failed`, `Configuration Descriptor Request Failed`).
2. **Hướng dẫn can thiệp vật lý dứt điểm**:
   - Yêu cầu người vận hành tắt công tắc nguồn adapter của Hub 20 cổng đó trong 5-10 giây rồi bật lại.
   - Rút và cắm lại cáp uplink USB nối từ Hub vào máy tính Kibe.
3. **Bảo toàn các máy khác**: Tiếp tục để các máy khỏe và các tiến trình batch độc lập khác chạy bình thường, tuyệt đối không dừng farm.
