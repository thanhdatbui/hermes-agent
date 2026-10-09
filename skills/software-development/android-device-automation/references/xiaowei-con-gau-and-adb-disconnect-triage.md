# Xiaowei ("Con Gấu") & Farm ADB Disconnect Triage Reference

## Hiện Tượng (Symptoms)
- Farm vẫn chạy automation nền (feed session, upload, follow), máy báo vẫn lên qua `adb devices` / script.
- Giao diện Xiaowei ("Con gấu" - tool phản chiếu màn hình tập trung S7) bị đơ, trắng màn hình, hoặc hàng loạt máy không hiển thị hình ảnh dù cắm cáp.
- Xuất hiện một số máy bị văng hoặc offline.

---

## Cơ Chế Gây Lỗi (Root Cause Mechanics)

1. **Stuck `wait-for-device` Subprocesses:**
   - Khi một thiết bị S7 bị ngắt kết nối vật lý (tuột cáp, lỏng hub USB, sập nguồn), Xiaowei tự động spawn tiến trình con:
     `adb.exe -s <missing_serial> wait-for-device`
   - Khi thiết bị không còn tồn tại trên bus USB (`Present: False`), lệnh `wait-for-device` này bị block vĩnh viễn không bao giờ trả về.
   - Khi có nhiều máy bị văng (hoặc có serial cũ đã đổi máy nhưng Xiaowei còn giữ cache), hàng chục tiến trình `wait-for-device` kẹt ngầm làm nghẽn luồng IPC/Tauri backend của Xiaowei, khiến UI toàn bộ các máy khác bị đứng hình.

2. **Server Auth & Event Polling Timeout:**
   - File log tại `C:\Program Files (x86)\xiaowei\logs\app_rCURRENT.log` thường xuất hiện:
     `event connection error: ... dns error: No such host is known (os error 11001)` hoặc `deadline has elapsed` tới `https://tp.xiaowei.run/events`.
   - Kết hợp với việc bị kẹt luồng ADB, UI Xiaowei không thể refresh frame từ các máy đang chạy tốt.

3. **Cạn kiệt Socket Handle / File Descriptor (`Too many open files` - Tràn Socket Farm Lớn):**
   - **Hiện tượng đặc thù:** Hàng loạt màn hình (hoặc hầu hết màn hình) trên Xiaowei đồng loạt hiện thông báo cam: *"Điện thoại đã ngắt kết nối, vui lòng kiểm tra."* Nhưng khi chạy `adb devices` thì 100% thiết bị (ví dụ 74/74 máy) vẫn ở trạng thái `device`, pin/màn hình/launcher vẫn sống.
   - **Cơ chế:** Khi Xiaowei stream đồng thời ~74–80 máy, mỗi máy chiếm từ 2–4 socket/file descriptors (video stream, touch control, reverse forwarding). ADB server hoặc Tauri/C-runtime của Xiaowei trên Windows đụng giới hạn file descriptor / socket handle.
   - **Bằng chứng trong log (`C:\Program Files (x86)\xiaowei\logs\app_rCURRENT.log`):**
     ```text
     ERROR [xiaowei::android::client_center] client_center start serial: <serial>, err: DeviceError(Adb("adb error: cannot bind listener: Too many open files"))
     ERROR [xiaowei::android::client] ConnectionAborted: "An established connection was aborted by the software in your host machine." (os error 10053)
     ERROR [xiaowei::android::client_center] kill_reverse_all_ports err serial: <serial>, err: Io(Os { code: 10054/10061 ... })
     ```
   - **Khắc phục:** KHÔNG rút cắm cáp USB (phần cứng không lỗi). Chỉ cần restart app Xiaowei để xả socket handles. Khuyến nghị giảm độ phân giải/FPS trong cài đặt (`Chất lượng nhỏ`, `Tốc độ khung nhỏ`) hoặc chia tab hiển thị theo cụm thay vì mở full 80 màn hình cùng lúc.

4. **Văng Hàng Loạt Khi Mở Xiaowei/Jiuwei vs Hiểu Nhầm Về "Power Balance":**
   - **Ngộ nhận "Power Balance":** Tưởng rằng chỉ cần bật High Performance và tắt USB Selective Suspend / PCIe ASPM là hết văng. Thực tế: Selective Suspend/ASPM chỉ can thiệp khi đường truyền IDLE. Khi thiết bị đang hoạt động (stream Xiaowei hoặc auto script chạy), bus USB liên tục có traffic nên không bao giờ bị Windows ru ngủ.
   - **Hiện tượng văng khi Xiaowei ĐÃ TẮT (do auto script chạy):** Kể cả khi Xiaowei đã được watchdog đóng sau 20 phút, việc chạy script automation đa luồng đồng thời (kéo screencap PNG, uiautomator dump, push video) trên bo mạch chủ có chip Intel xHCI USB 3.0 bị tắt (`Present: False`) dồn cả 80 máy vào chip USB 2.0 EHCI (480 Mbps) sẽ gây nghẽn bus tức thời $\rightarrow$ Controller EHCI bị treo cứng thanh ghi phần cứng (Hardware Deadlock) $\rightarrow$ rớt hàng loạt thiết bị.
   - **Nguyên nhân thật sự khi văng hàng loạt:**
     * **Tràn xHCI/EHCI Endpoints & Saturation:** Bo mạch chủ PC có giới hạn phần cứng cứng (64–128 endpoints). 80 máy S7 + Hubs nối tầng đẩy controller đến giới hạn tới hạn. Chạy trên USB 2.0 làm trầm trọng hóa vấn đề do băng thông quá bé.
     * **Nghẽn băng thông & Lỗi truyền gói USB (Babble/Timeout):** Dữ liệu dồn dập khiến controller reset Root Hub hoặc halt Transfer Ring -> văng 1 nhánh 16–20 máy hoặc cả cụm.
     * **Kẹt luồng (Deadlock) ADB server:** Tiến trình `adb.exe` bị nghẽn socket I/O khi nhận đồng thời hàng chục luồng dữ liệu nặng.
     * **Quá nhiệt & Sụt áp Hub:** Hub 16/20 cổng chạy full video bị nóng hoặc sụt nguồn 5V tự ngắt bus.
   - **Tại sao Reset PC lại hết mà `adb kill-server` không giải quyết được?** Khi controller USB bị deadlock ở tầng thanh ghi phần cứng, hệ điều hành không thể tự re-enumerate. Reset PC giải phóng thanh ghi phần cứng, xóa hàng đợi driver kernel, kill socket treo của ADB, và gửi hardware USB bus reset ép các hub khởi động lại.
   - **Cứu nhanh không cần reboot PC:**
     1. Tắt app Xiaowei / Jiuwei (nếu đang bật).
     2. Gõ lệnh: `taskkill /F /IM adb.exe` -> `adb start-server`.
     3. Nếu ADB không nhận máy nào -> controller bị treo cứng ở mức phần cứng -> mới cần restart PC hoặc rút cắm lại cáp tổng Hub.
   - **Khắc phục triệt để tầng phần cứng:** Bật lại xHCI USB 3.0 (`8D31`) trong BIOS; lắp card PCIe USB 3.0 độc lập; bóp nghẹt tần suất gọi `screencap` đa luồng trong script.
     1. Kích hoạt Power Scheme High Performance và tắt Selective Suspend:
        ```cmd
        powercfg /SETACVALUEINDEX 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0
        powercfg /SETDCVALUEINDEX 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0
        powercfg /SETACTIVE 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
        ```
     2. Ghi Registry nhân cấm USB Suspend:
        ```powershell
        Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\USB" -Name "DisableSelectiveSuspend" -Value 1 -Type DWord -Force
        ```
     3. Tắt tiết kiệm điện trên toàn bộ USB Hubs/Controllers:
        ```powershell
        Get-PnpDevice -Class 'USB' | Where-Object { $_.FriendlyName -match 'Hub|Controller' } | ForEach-Object {
            $key = "HKLM:\SYSTEM\CurrentControlSet\Enum\$($_.InstanceId)\Device Parameters"
            if (Test-Path $key) {
                Set-ItemProperty -Path $key -Name "EnhancedPowerManagementEnabled" -Value 0 -Type DWord -ErrorAction SilentlyContinue
                Set-ItemProperty -Path $key -Name "AllowIdleIrpInWorkingState" -Value 0 -Type DWord -ErrorAction SilentlyContinue
                Set-ItemProperty -Path $key -Name "DeviceSelectiveSuspended" -Value 0 -Type DWord -ErrorAction SilentlyContinue
            }
        }
        ```

5. **Thói Quen Quên Tắt Xiaowei Sau Khi View Màn & Watchdog Tự Tắt Khi Idle (Ngưỡng Chuẩn: 20 Phút):**
   - **Thói quen vận hành của User:** Operator mở Xiaowei lên xem xét màn hình farm (QA/kiểm tra nick/thao tác nhanh), sau đó rời máy tính hoặc chuyển sang làm việc khác mà quên đóng Xiaowei.
   - **Hậu quả:** Xiaowei tiếp tục stream 80 luồng video USB liên tục suốt hàng giờ liền, làm nghẽn bus USB 2.0, nóng chipset PC, và giữ chặt exclusive handles khiến các luồng automation nền bị lag hoặc rớt ADB.
   - **Giải pháp chuẩn hóa (Đã triển khai Dual-Cluster Kibe & Admin):**
     - Đặt watchdog chạy ngầm mỗi 5 phút kiểm tra `GetLastInputInfo` (đếm mili-giây từ lần click chuột/gõ phím cuối cùng).
     - **Ngưỡng chuẩn tối ưu: 20 phút (1200 giây)**. Dưới 15 phút thì quá ngắn (dễ tắt nhầm khi đang đọc số liệu), trên 30 phút thì quá dài (bào mòn bus USB).
     - **Đã deploy cronjob 2 bên:**
       * PC Kibe: job `xiaowei-idle-auto-close-kibe` (schedule `*/5 * * * *`, deliver `telegram:-5373649734`).
       * PC Admin: job `xiaowei-idle-auto-close-admin` (schedule `*/5 * * * *`, deliver `telegram:-5188753741`).
     - Script chuẩn hóa: `~/AppData/Local/hermes/scripts/xiaowei_idle_auto_close_watchdog.py`.
     - **Pitfall quan trọng (Windows cp1252 charmap):** Console mặc định của Windows chạy codepage cp1252/1258. Nếu script in tiếng Việt có dấu trực tiếp sẽ văng `UnicodeEncodeError: 'charmap' codec can't encode character...`. Bắt buộc reconfigure stdout hoặc dùng tiếng Việt không dấu:
       ```python
       if hasattr(sys.stdout, "reconfigure"):
           sys.stdout.reconfigure(encoding="utf-8")
       ```

6. **Phía Thiết Bị (Android Phone):**
   - Tiến trình `app_process` (scrcpy backend) trên các máy online vẫn chạy bình thường (`ps -A | grep app_process`). Lỗi 100% nằm ở phía quản lý tiến trình của Xiaowei trên PC.

---

## Quy Trình Chẩn Đoán Nhanh (Fast Triage Checklist)

### Bước 1: Đối soát nhanh số máy nhận ADB vs Cấu hình Farm
So sánh thiết bị attached với file nguồn `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`:
- Kiểm tra danh sách thiếu:
  ```bash
  python D:/Taadaa/tools/inspect_machine.py
  ```
- Hoặc qua Python check nhanh số lượng `device`, `offline`, `unauthorized`.

### Bước 2: Kiểm tra vật lý phần cứng USB (Windows PnP)
Xác định máy văng do cáp/hub USB hay do ADB daemon:
```powershell
Get-PnpDevice | Where-Object { $_.InstanceId -like '*VID_04E8&PID_6860\*' } | Select-Object Status, Present, InstanceId
```
- Nếu `Present: False`: Thiết bị đã bị ngắt kết nối vật lý khỏi cổng USB (tuột cáp, hub lỏng nguồn, máy sập nguồn).
- Nếu `Present: True` nhưng không có trong `adb devices`: ADB daemon bị treo cổng, cần toggle USB debugging hoặc `adb kill-server`.

### Bước 3: Phát hiện tiến trình Xiaowei bị treo
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'adb.exe' -and $_.CommandLine -like '*wait-for-device*' } | Select-Object ProcessId, CommandLine
```
Nếu thấy nhiều dòng `wait-for-device` với các serial máy đã rút: Đây là lý do chính khiến Xiaowei bị đơ giao diện.

---

## Hướng Khắc Phục Chuẩn (Standard Remediation)

1. **Cắm chặt lại phần cứng:** Cắm lại cáp USB/kiểm tra nguồn cho các máy báo `Present: False`.
2. **Khởi động lại Xiaowei:**
   - Tắt tiến trình Xiaowei: `taskkill /F /IM xiaowei.exe` (hoặc đóng từ Taskbar).
   - Dọn sạch các `adb.exe wait-for-device` mồ côi nếu còn sót.
   - Mở lại Xiaowei: Xiaowei sẽ bắt lại ngay 100% các máy đang online (`device`) mà không còn bị nghẽn luồng.
3. **Lưu ý máy thay thế (máy mới thay máy cũ):**
   - Serial mới nhất luôn lấy từ `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` dòng máy tương ứng.
   - Nếu máy mới chưa cập nhật vào các workbook phụ (`Tik1..Tik8.xlsx`, `taikhoan_run_safe.xlsx`), các runner sẽ dùng serial cũ gây lỗi `config-error: ADB validation failed: Device serial not found`. Cần đồng bộ serial mới qua toàn bộ workbook.
