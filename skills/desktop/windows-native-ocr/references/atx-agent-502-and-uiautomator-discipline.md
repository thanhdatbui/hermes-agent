# Kỷ Luật Phục Hồi ATX 502 Bad Gateway & Cấm Gõ Lệnh UiAutomator Trên Farm S7

## 1. Cội Nguồn Lỗi 502 Bad Gateway Trên Samsung S7
- Dàn máy Samsung S7 (Android 7/8, RAM yếu) chạy TikTok 47.x rất nặng.
- Tiến trình stub ngầm `com.github.uiautomator` do `atx-agent` quản lý dễ bị Linux kernel kill ngầm (SIGKILL 137). Khi đó, các lệnh gọi JSON-RPC (port 7912) như `click` hay `dumpWindowHierarchy` sẽ trả về `HTTP Error 502: Bad Gateway`.

## 2. Kỷ Luật Phục Hồi Chuẩn Xác (Không Gõ Lệnh Bậy)
1. **CẤM TUYỆT ĐỐI gõ tay lệnh shell `am instrument` hay `uiautomator dump`:**
   - Việc cố chạy `am instrument ... AndroidJUnitRunner` bằng tay hoặc qua ADB shell sẽ làm đè màn hình, chiếm dụng binder IPC, gây kẹt lock và làm hỏng toàn bộ cơ chế daemon của `atx-agent`.
2. **Quy trình phục hồi chuẩn 1 dòng:**
   - Chỉ cần force-stop và restart daemon `atx-agent`:
     ```bash
     adb -s <serial> shell "am force-stop com.github.uiautomator; am force-stop com.github.uiautomator.test; /data/local/tmp/atx-agent server --stop; sleep 1; /data/local/tmp/atx-agent server -d"
     ```
   - Chờ 1–2 giây để daemon tự hồi phục.
3. **Tuân thủ WinRT OCR Primary:**
   - Mọi thao tác kiểm chứng UI text bắt buộc qua **WinRT OCR (`automation_core.ui_extract.ocr_screen_boxes`)** chạy trên CPU máy tính Host Windows 10, giải phóng hoàn toàn tải cho điện thoại.
