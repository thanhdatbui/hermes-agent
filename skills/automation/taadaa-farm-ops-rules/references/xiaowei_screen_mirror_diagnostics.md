# Chẩn đoán phân biệt Mất kết nối ADB Thật vs XiaoWei ("Con gấu") Mất Stream

## 1. Hiện tượng
- Trên phần mềm chiếu màn hình XiaoWei (玖卫安卓投屏 / Jiwei VIP): Một hoặc nhiều máy (thậm chí hàng loạt chục máy) chuyển sang nền nâu cam hiển thị:
  `Phone disconnected, please check.`
- User thường lo lắng máy bị sập nguồn, văng toàn bộ hoặc mất kết nối ADB.

## 2. Bản chất kỹ thuật (Thật vs Ảo)
- **XiaoWei stream qua socket ADB**: XiaoWei đẩy agent (minicap/scrcpy) và forward/reverse socket qua ADB server port 5037.
- **Ngưỡng timeout 15s**: Nếu một cụm USB bị nghẽn (do chập chờn cáp, tụt áp hoặc xung đột ADB server), độ trễ socket vượt 15s. XiaoWei sẽ log:
  `ERROR [xiaowei::android::client] ... 连接断开或是超过15秒未连接 (os error 10061)`
  và tự động chuyển trạng thái slot sang Disconnected.
- **XiaoWei KHÔNG tự động reconnect**: Khi đã mark disconnect, slot đó sẽ giữ nguyên màn hình cam cho tới khi người dùng quét lại / restart XiaoWei, dù thiết bị và ADB vẫn đang online 100%.

## 3. Quy trình đối soát 3 bước (Tối đa 1 phút)

### Bước 1: Lấy danh sách máy từ Admin ADB Server
Kiểm tra thiết bị cluster Admin từ Kibe qua:
```bash
python -c '
import openpyxl, subprocess

excel_path = r"D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx"
wb = openpyxl.load_workbook(excel_path, data_only=True, read_only=True)
ws = wb.active
machine_serial = {int(r[0]): str(r[1]).strip() for r in ws.iter_rows(min_row=2, values_only=True) if r and r[0] is not None and r[1]}

adb_bin = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
res = subprocess.run([adb_bin, "-H", "192.168.110.119", "-P", "5037", "devices"], capture_output=True, text=True, timeout=10)
adb_devices = {line.split()[0]: line.split()[1] for line in res.stdout.strip().splitlines()[1:] if len(line.split()) >= 2}
'
```

### Bước 2: Test ping `adb shell` có timeout (Phân loại 3 nhóm & Cứu O(1))
Chạy test nhanh `adb shell echo 1` với timeout 2.5s - 3s:
1. **Rớt ADB THẬT (Mất nguồn / Tuột cáp)**: Serial không có trong `adb devices` (`device not found`) hoặc báo `offline`.
   - *Kiểm tra phần cứng từ xa qua Windows PnP (SSH sang Admin)*:
     ```bash
     ssh admin-farm "powershell -Command \"Get-PnpDevice | Where-Object { \$_.InstanceId -like '*<serial>*' } | Select-Object FriendlyName, Status, Present, Problem\""
     ```
     Nếu trả về `Present: False` và `Problem: CM_PROB_PHANTOM`: Khẳng định 100% ngắt kết nối vật lý (tuột cáp, sập nguồn máy, hỏng cổng hub). Không tốn thời gian mò phần mềm.
2. **Kẹt USB / Treo I/O Socket (Cứu sống O(1) qua `reconnect`)**: Thiết bị báo `device` nhưng lệnh `adb shell` bị timeout > 3s.
   - *CẤM vội `kill-server` làm rớt toàn bộ 80 máy!*
   - *Lệnh cứu sống nguyên tử từng máy*:
     ```bash
     adb -H 192.168.110.119 -P 5037 -s <serial> reconnect
     ```
     Lệnh này lập tức reset pipe endpoint của riêng thiết bị đó, đưa máy thoát treo I/O và phản hồi lại bình thường chỉ sau 1-2 giây.
3. **ẢO do XiaoWei (Đa số)**: `adb shell` trả lời ngay lập tức (<0.5s), máy vẫn ở Launcher hoặc app bình thường. Chỉ là XiaoWei bị đứt socket stream video. Người dùng chỉ cần click chuột vào slot trên XiaoWei để mở lại stream.

### Bước 3: Soi log XiaoWei & Kiểm tra xung đột ADB Server trên Admin
- **Log XiaoWei**: `C:\Program Files (x86)\xiaowei\logs\app_rCURRENT.log`.
- **Tiến trình ADB chiếm port 5037**:
  Kiểm tra xem có tool khác (như `SamFwTool.exe`) chiếm port 5037 với ADB version cũ không:
  ```bash
  ssh admin-farm "wmic process where \"name='adb.exe'\" get ProcessId,ExecutablePath,CommandLine"
  ```
  Nếu SamFwTool mở `C:\SamFwTool\data\adb.exe` (v29.0.6 rất cũ từ 2019), nó rất dễ nghẽn socket và sinh hàng ngàn kết nối `TIME_WAIT` khi XiaoWei mở đồng thời 80 luồng stream.

## 4. Quy trình khắc phục triệt để khi "Rút cắm lại & restart XiaoWei vẫn bị cam"
Khi người vận hành rút cáp cắm lại và tắt bật XiaoWei nhưng màn hình vẫn báo "Phone disconnected":
*Nguyên nhân cốt lõi*: `SamFwTool.exe` hoặc tiến trình `adb.exe` cũ đang kẹt hàng ngàn kết nối `TIME_WAIT` và chiếm port 5037. Bật lại XiaoWei nó vẫn kết nối vào ADB Server cũ đang bị nghẽn nên lập tức văng stream tiếp.

### Các bước can thiệp dứt điểm:
1. **Kill tool gây xung đột và ADB cũ**:
   ```cmd
   ssh admin-farm "taskkill /F /IM SamFwTool.exe"
   ssh admin-farm "taskkill /F /IM adb.exe"
   ```
2. **Khởi động lại ADB Server bằng đúng bản v34 của XiaoWei**:
   ```cmd
   ssh admin-farm "\"C:\Program Files (x86)\xiaowei\tools\adb.exe\" start-server"
   ```
3. **Restart XiaoWei vào đúng Interactive Console (Session 1)**:
   *Lưu ý*: Lệnh PowerShell `Start-Process` chạy qua SSH sẽ bị đẩy vào Session 0 (chạy ngầm không lên GUI). BẮT BUỘC dùng Task Scheduler để kích hoạt GUI trên màn hình Console của user `Admin`:
   ```cmd
   ssh admin-farm "taskkill /F /IM xiaowei.exe"
   ssh admin-farm "schtasks /Create /TN RunXiaoWei /TR \"\\\"C:\\Program Files (x86)\\xiaowei\\xiaowei.exe\\\"\" /SC ONCE /ST 00:00 /RU \"Admin\" /F && schtasks /Run /TN RunXiaoWei && schtasks /Delete /TN RunXiaoWei /F"
   ```
4. **Kiểm tra ping xác nhận 80 máy**:
   Chạy script ping đồng thời 80 máy qua port 5037 để nghiệm thu `TIMEOUT: 0`.

## 5. Trực quan hóa nghiệm thu cho Người vận hành (Visual Mosaic Evidence)
- User không đọc log text dài dòng, duyệt mắt qua ảnh.
- Khi điều tra một nhóm máy bị ngắt kết nối (ví dụ 8 máy bị cam trên XiaoWei):
  1. Với các máy còn online ADB: Dùng `exec-out screencap -p` chụp trực tiếp màn hình hiện tại của máy.
  2. Tổng hợp tất cả ảnh vào 1 ảnh ghép tổng quan (Mosaic Grid) bằng OpenCV / PIL:
     - Resize các thumbnail về kích thước đồng nhất (ví dụ 170x300).
     - Gắn header nhãn máy rõ ràng: `MAY <N>`.
     - Với máy mất kết nối vật lý (như Máy 255): Tạo ô tối màu kèm chữ đỏ `MAT KET NOI / USB OFF / TUOT CAP`.
  3. Gửi ngay ảnh tổng quan qua cú pháp `MEDIA:<path_anh>` kèm phân loại 3 nhóm ngắn gọn (Mất kết nối vật lý, Kẹt USB đã cứu sống qua reconnect, Rớt stream XiaoWei chỉ cần click lại).

## 6. Cơ chế Khắc phục Triệt để Tự động (Fix dứt điểm kẹt kết nối & mất stream)
Khi người vận hành thắc mắc: *"Lí do kẹt kết nối vs lỗi hình ảnh. Fix dứt điểm đi chứ cứ bị hoài"*:

### A. Căn nguyên kỹ thuật kép (Kẹt kết nối & Mất frame hình ảnh):
1. **Lí do kẹt kết nối (ADB USB Transport Deadlock)**:
   - Các dòng máy Samsung S7 (Android 8.0) chỉ có 1 pipeline USB vật lý duy nhất.
   - Khi XiaoWei stream video 24/7 (chiếm dụng băng thông USB liên tục) kết hợp với bão lệnh shell từ các cronjob/watchdog (quét wifi, screen, lock mỗi 5–15 phút), buffer USB của thiết bị bị drop packet hoặc race condition.
   - `adbd` trên Android rơi vào khóa socket ngầm (`futex_wait_queue_me` / half-closed socket). ADB Server trên PC vẫn thấy trạng thái `device`, nhưng mọi lệnh `adb shell` gửi tới đều bị treo cứng vô hạn (>10s–30s).
   - Nếu không có cơ chế tự động can thiệp, máy sẽ bị kẹt vĩnh viễn cho đến khi có người can thiệp thủ công.
2. **Lí do mất frame hình ảnh (Màn hình cam Xiaowei)**:
   - XiaoWei thu hình qua `XWCaptureScreen.jar` (hook trực tiếp Surface Display).
   - Khi điện thoại tắt màn hình (do watchdog screen healer ép `stay_on_while_plugged_in = 0` và timeout 10 phút), Android tự động ngắt render GPU surface để tiết kiệm pin (FPS về 0).
   - XiaoWei nhận định luồng stream bị đứt và chuyển slot sang icon cam ngắt kết nối.
   - Nếu máy đồng thời dính kẹt socket ADB ở mục 1, XiaoWei không thể gửi lệnh đánh thức máy lại được nữa, dẫn đến slot bị đóng băng.

### B. Giải pháp tự hành vĩnh viễn — Watchdog `farm-adb-transport-healer`:
- **Đã thiết lập cronjob tự hành 3 phút/lần (`*/3 * * * *`)**:
  - Script: `C:\Users\Kibe\AppData\Local\hermes\scripts\farm_adb_transport_auto_healer.py` (và bản sync `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\farm_adb_transport_auto_healer.py`).
  - Job ID: `farm-adb-transport-healer`.
- **Cơ chế hoạt động**:
  1. Quét song song 160 máy trên cả 2 cụm (Kibe Local + Admin Remote `192.168.110.119:5037`).
  2. Ping kiểm tra với timeout cực ngắn (2.5 giây).
  3. Nếu phát hiện máy bị `HUNG` (timeout) hoặc `offline`:
     - Tự động phát lệnh `adb reconnect` đến serial máy đó để lập tức reset USB transport endpoint và bẻ gãy deadlock trong < 2 giây.
     - Tự động bắn `input keyevent 224` (KEYCODE_WAKEUP) để đánh thức màn hình, buộc Android phục hồi frame rendering cho `XWCaptureScreen.jar` giúp XiaoWei bắt lại luồng video ngay lập tức.
  4. Tuân thủ **Silent Watchdog**: Hoàn toàn im lặng khi toàn farm khỏe mạnh, chỉ log khi có máy được cứu sống.
