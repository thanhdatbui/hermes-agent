# ADB Binary Resolution & Direct Invocation Pattern on Windows Farm

## Bối cảnh & Vấn đề
Trên môi trường Windows Farm (đặc biệt khi chạy terminal qua Git Bash / MSYS / POSIX shell):
- Binary `adb` thường **không có sẵn trong biến môi trường `$PATH`** của shell hệ thống (`adb: command not found`).
- Việc chạy tìm kiếm mù (`find /c/ -name "adb.exe"`, recursive grep, hoặc dò quét đĩa) gây timeout lãng phí lượt gọi tool (iteration exhaustion) và vi phạm kỷ luật chống quét đĩa diện rộng.

## Vị trí ADB chuẩn trên hệ thống
Binary ADB chính thức đã được tích hợp sẵn và chuẩn hóa trong các repo automation:
1. `C:\Program Files (x86)\xiaowei\tools\adb.exe` (đường dẫn chuẩn được import tự động bởi `gmail_reg_v10.ADB_EXE`)
2. `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe`

## Cách gọi chuẩn xác từ Python script & Shell

### 1. Import trực tiếp qua module nghiệp vụ
Trong các script Python (ví dụ: `hook_chatgpt_register.py`, `gmail_reg_v10.py`):
```python
from gmail_reg_v10 import shell, tap, screenshot, get_ui_xml, ADB_EXE
# ADB_EXE đã được định nghĩa sẵn tới "C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe"
```

### 2. Khi chạy adb từ terminal / bash
Tuyệt đối không gõ `adb devices` chay khi chưa export PATH. Sử dụng đường dẫn tuyệt đối hoặc export một lần:
```bash
export PATH="/c/Program Files (x86)/xiaowei/tools:$PATH"
adb devices
```
Hoặc gọi trực tiếp:
```bash
"/c/Program Files (x86)/xiaowei/tools/adb.exe" devices
```
