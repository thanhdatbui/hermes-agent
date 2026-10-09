# Tra cứu O(1) Serial Máy Farm & Xử lý Cảnh báo Dual-Threshold Rỗng

## 1. Cơ chế Cảnh báo Dual-Threshold Rỗng (0 Cụm Lỗi nhưng Vẫn Phát Alert)
Khi nhận cảnh báo:
- `• Số cụm lỗi hệ thống: 0`
- Mục `📋 CHI TIẾT LỖI VƯỢT NGƯỠNG KÉP` bị rỗng
- Nhưng có: `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện N máy dính lỗi login/xác minh`

**Bản chất logic trong `automation_core/batch_aggregator.py`:**
- Bộ gom lỗi lọc theo ngưỡng kép: $\ge 10\%$ toàn batch VÀ $\ge 3$ máy có cùng signature. Các lỗi rải rác bị đẩy vào nhóm `sporadic` nên không hiện cụm.
- Tuy nhiên, chỉ cần có $\ge 1$ máy dính các từ khóa nhạy cảm auth (`login`, `account screen`, `verification`, `checkpoint`, `auth`, `văng`), cờ `should_alert` bật `True` lập tức để bảo vệ tài khoản farm.

## 2. Tra cứu Serial O(1) Tuyệt Đối Không Quét Đĩa
Khi nhận máy `M<N>` (ví dụ M52):
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

## 3. Quy trình Triage & Teardown Máy Văng Session / Màn Hình Lạ
1. **Kiểm tra trạng thái ADB & Activity:**
   ```bash
   "/c/Program Files (x86)/xiaowei/tools/adb.exe" devices | grep "<serial>"
   "/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> shell "dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"
   ```
2. **Chụp ảnh hiện trường:**
   ```bash
   "/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> shell "screencap -p /sdcard/inspect.png"
   "/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> pull /sdcard/inspect.png "D:/Taadaa/reports/mN_inspect.png"
   ```
3. **Teardown & Force-Stop về HOME an toàn:**
   ```bash
   "/c/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> shell "am force-stop com.ss.android.ugc.trill && input keyevent 3"
   ```
4. **Nghiệm thu ảnh chụp màn hình sau khi về HOME:**
   Chụp lại screencap và đính kèm `MEDIA:<path_slash>` trong báo cáo cuối theo Gate 6.
