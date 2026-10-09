# Xiaowei ("Con Gấu") & Farm ADB Disconnect Triage Reference

## Hiện Tượng (Symptoms)
- Farm vẫn chạy automation nền (feed session, upload, follow), máy báo vẫn lên qua adb devices / script.
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

3. **Phía Thiết Bị (Android Phone):**
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
