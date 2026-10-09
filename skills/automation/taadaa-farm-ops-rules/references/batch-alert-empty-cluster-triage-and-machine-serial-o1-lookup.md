# Tra cứu O(1) Serial Máy & Xử lý Cảnh báo Văng Session / Login Screen

## 1. Bản chất Cảnh báo Dual-Threshold rỗng (0 cụm lỗi nhưng vẫn báo BATCH ALERT)
Khi hệ thống chạy batch và trả về alert với:
- `Số cụm lỗi hệ thống: 0`
- Dòng `CHI TIẾT LỖI VƯỢT NGƯỠNG KÉP` không có mục nào
- Nhưng vẫn có `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện N máy dính lỗi login/xác minh`

**Nguyên nhân cấu trúc trong `batch_aggregator.py`:**
- Bộ gom lỗi yêu cầu ngưỡng kép: $\ge 10\%$ toàn batch VÀ $\ge 3$ máy có cùng signature. Các lỗi khác biệt nhau rải rác bị xếp vào `sporadic` nên không hiện cụm.
- Tuy nhiên, chỉ cần có $\ge 1$ máy có keyword nhạy cảm (`login`, `account screen`, `verification`, `checkpoint`, `auth`, `văng`), cờ `should_alert` lập tức bật thành `True` để bảo vệ tài khoản farm.

## 2. Tra cứu Serial O(1) từ Máy N (CẤM scan đĩa/quét rộng)
Khi cần tra serial máy `N` (ví dụ M52):
- **CẤM TUYỆT ĐỐI**: dùng `os.walk`, `glob(recursive=True)` trên ổ `D:/` hoặc `D:/Taadaa`.
- **Nguồn O(1) chuẩn xác nhất**: Đọc cấu hình nguồn cron đã compile:
  ```python
  import json
  with open('D:/Taadaa/runtime/kibe/cron-source/hermes_cron_source_config.json', 'r', encoding='utf-8') as f:
      data = json.load(f)
  accounts = data.get('feed_source', {}).get('accounts', [])
  m = [a for a in accounts if a.get('machine') == N]
  # Lấy serial: m[0]['serial']
  ```
- Hoặc đọc mapping từ workbook: `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx`.

## 3. Quy trình Xử lý Hiện trường An toàn khi máy dính Login/Splash/Freeze
1. **Kiểm tra trạng thái kết nối ADB:**
   ```bash
   "/c/Program Files (x86)/xiaowei/tools/adb.exe" devices | grep "<serial>"
   ```
2. **Kiểm tra Activity đang focus:**
   ```bash
   "/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> shell "dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"
   ```
3. **Chụp ảnh hiện trường nghiệm thu:**
   ```bash
   "/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> shell "screencap -p /sdcard/inspect.png"
   "/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> pull /sdcard/inspect.png "D:/Taadaa/reports/mN_inspect.png"
   ```
4. **Teardown & Force-Stop về HOME (bảo vệ máy và tránh tiêu hao tài nguyên):**
   ```bash
   "/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> shell "am force-stop com.ss.android.ugc.trill && input keyevent 3"
   ```
5. **Nghiệm thu ảnh chụp màn hình sau khi về HOME:**
   Chụp lại screencap và đính kèm `MEDIA:<path_slash>` trong báo cáo cuối theo Gate 6.
