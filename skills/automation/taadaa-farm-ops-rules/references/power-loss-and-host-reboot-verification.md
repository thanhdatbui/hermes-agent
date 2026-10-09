# Quy trình xác minh sụp nguồn / cúp điện máy Host & Phone Farm

## 1. Mục đích
Xác định chính xác máy tính host hoặc dàn máy phone farm có bị cúp điện / sụp nguồn đột ngột hay không, thời điểm sụp nguồn và thời điểm hồi phục.

## 2. Các bước kiểm tra O(1)

### Bước 1: Truy vấn Windows Event Log trên máy Host
Dùng PowerShell truy vấn Event ID 41 (Kernel-Power) và Event ID 6008 (Unexpected Shutdown):
```powershell
powershell -NoProfile -Command "Get-WinEvent -FilterHashtable @{LogName='System'; Id=41,6008} -MaxEvents 5 | Format-Table TimeCreated, Id, Message -AutoSize"
```
- **Event 6008:** Ghi nhận thời điểm chính xác máy bị tắt đột ngột (thời điểm cúp điện).
- **Event 41:** Ghi nhận thời điểm máy boot lại không sạch sẽ (thời điểm có điện lại).
- **LastBootUpTime:**
```powershell
powershell -NoProfile -Command "Get-CimInstance Win32_OperatingSystem | Select-Object LastBootUpTime"
```

### Bước 2: Định vị công cụ ADB trên Host
Nếu lệnh `adb` không nằm trong PATH của terminal Git-Bash/MSYS:
- Đường dẫn mặc định: `C:\Program Files (x86)\xiaowei\tools\adb.exe`
- Hoặc script trích xuất nhanh O(1): `python D:/Taadaa/tools/inspect_machine.py all`

### Bước 3: Đối chiếu chéo Uptime của dàn Phone Farm
Kiểm tra uptime trên toàn bộ các máy đang kết nối:
```bash
"C:\Program Files (x86)\xiaowei\tools\adb.exe" devices
```
Với từng serial:
```bash
"C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <SERIAL> shell uptime
```
- **Đối chiếu:** Nếu uptime của toàn bộ các máy phone farm khớp thời gian với `LastBootUpTime` của Windows host, kết luận sự cố cúp điện toàn bộ khu vực / cụm nguồn farm.

### Bước 4: Nghiệm thu bằng chứng (Gate 6)
Chụp screencap O(1) của ít nhất 1 máy làm bằng chứng hiện trường:
```bash
"C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <SERIAL> exec-out screencap -p > "C:/Users/Kibe/AppData/Local/Temp/inspect_kibe.png"
```
Đính kèm `MEDIA:<path>` trong báo cáo kết thúc task.
