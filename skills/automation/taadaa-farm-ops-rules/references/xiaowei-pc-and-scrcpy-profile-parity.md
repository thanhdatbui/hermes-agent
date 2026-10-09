# Xiaowei (Con Gấu) PC & Scrcpy Profile Parity (Kibe vs Admin)

Tài liệu chuẩn hóa đối chiếu cấu hình phần mềm Xiaowei, độ phân giải / DPI màn hình PC và tham số tiến trình scrcpy trên thiết bị điện thoại Android thuộc hệ thống Taadaa Farm.

---

## 1. Cấu hình màn hình PC Host (Kibe / Admin)

Để giao diện hiển thị ma trận máy của Xiaowei và tọa độ click / preview không bị lệch hoặc mờ:
- **Độ phân giải chuẩn:** `1920 x 1080` (Primary Display).
- **DPI / Scaling chuẩn:** `96 DPI` (tương ứng Windows Scale `100%`).

### Lệnh PowerShell kiểm tra nhanh:
```powershell
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Screen]::AllScreens | Select-Object DeviceName, Bounds, Primary
(Get-ItemProperty "HKCU:\Control Panel\Desktop").LogPixels
```
*Nếu `LogPixels` khác `96` (ví dụ 120 là 125%, 144 là 150%), cần chỉnh lại về 100% để đảm bảo tương thích hiển thị.*

---

## 2. File cấu hình Xiaowei (`config.toml`)

- **Đường dẫn chuẩn:**
  `%APPDATA%\xiaowei_wecan88888\config.toml`
  *(Tương đương `C:\Users\<User>\AppData\Roaming\xiaowei_wecan88888\config.toml`)*

- **Nội dung cấu hình chuẩn (Parity Kibe vs Admin):**
  ```toml
  [input]
  switch = true

  [activation]
  activation_id = "<activation_key>"

  [encoder]
  use_soft_encoder = true

  [mode]
  hid = false
  ```

- **Ý nghĩa các khóa:**
  - `use_soft_encoder = true`: Sử dụng bộ giải mã phần mềm trên PC, giảm thiểu lỗi treo crash GPU khi giải mã đồng thời 80-160 luồng video màn hình.
  - `hid = false`: Không bật chế độ phần cứng HID (chuột/phím ảo qua board cứng), dùng ADB input stream thông thường.
  - `switch = true`: Cho phép switch stream/input linh hoạt.

---

## 3. Vị trí ADB đi kèm Xiaowei

Trên Windows host chạy Xiaowei, công cụ `adb.exe` mặc định nằm tại:
- `C:\Program Files (x86)\xiaowei\tools\adb.exe`

Nếu terminal bash báo `adb: command not found`, luôn ưu tiên fallback về path trên (như đã định nghĩa trong `D:\Taadaa\tools\inspect_machine.py`).

---

## 4. Tham số tiến trình `scrcpy` (`app_process`) trên điện thoại Android

Xiaowei kích hoạt server truyền màn hình trên điện thoại thông qua `app_process` gọi `com.genymobile.scrcpy.Server 2.4`.

### Tham số tối ưu tải cho dàn S7:
```text
app_process / com.genymobile.scrcpy.Server 2.4 scid=20 audio=false video_encoder=OMX.google.h264.encoder max_size=480 max_fps=2 video_bit_rate=50000 tunnel_forward=true cleanup=false clipboard_autosync=false stay_awake=true
```

- **`video_encoder=OMX.google.h264.encoder`**: Bắt buộc dùng software encoder của Google thay vì phần cứng Samsung Exynos, tránh treo chip GPU máy điện thoại khi cắm sạc nóng 24/7.
- **`max_size=480`**: Giới hạn độ dài cạnh lớn màn hình về 480p, đủ để quan sát và OCR mà không ngốn băng thông USB/Wi-Fi.
- **`max_fps=2`**: Khóa cứng trần 2 FPS cho preview Xiaowei để giữ CPU máy mát và nhường tài nguyên cho TikTok / GMS chạy mượt.
- **`video_bit_rate=50000`**: Giới hạn bitrate video ở mức 50 kbps.
- **`audio=false`**: Tắt âm thanh truyền về máy tính.
- **`stay_awake=true` & `cleanup=false`**: Giữ màn hình sáng trong khi stream và không tự dọn dẹp tiến trình khi ngắt socket đột ngột.

### Lệnh trích xuất kiểm tra trên thiết bị:
```bash
adb -s <serial> shell "ps -A | grep app_process"
adb -s <serial> shell "cat /proc/<PID>/cmdline | tr '\0' ' '"
```
