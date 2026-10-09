# Protocol Xử Lý Lỗi P0: `account-switcher-missing-expected` (Văng / Mất Phiên / Lệch Slot)

## Hiện Tượng & Dấu Hiệu
Trong batch nuôi acc/lướt feed (`tiktok-luot nuoi acc`), hệ thống Batch Aggregator phát tín hiệu cảnh báo P0:
```text
⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện máy dính lỗi login/mất phiên:
   • Máy M<N>: manual-needed:account-switcher-missing-expected: expected account not found in account switcher
```

## Quy Trình Xử Lý O(1) Chống Quét Rộng (Zero-Wide-Scan)

### 1. Trích xuất hiện trường O(1) (BẮT BUỘC)
- Chạy: `python D:/Taadaa/tools/inspect_machine.py <N>` để kiểm tra trạng thái màn hình, pin, current focus.
- Lấy ảnh hiện trường kiểm chứng Gate 6:
  ```bash
  adb -s <SERIAL> shell screencap -p /sdcard/m<N>_inspect.png
  adb -s <SERIAL> pull /sdcard/m<N>_inspect.png D:/Taadaa/reports/m<N>_inspect.png
  ```
  Đính kèm `MEDIA:D:/Taadaa/reports/m<N>_inspect.png` vào báo cáo điều phối.

### 2. Đối soát O(1) Workbook ↔ SQLite `tiktok_tracker.db`
Truy vấn trực tiếp DB local để xác định 3 nguyên nhân cốt lõi:
```python
import sqlite3
conn = sqlite3.connect('D:/Taadaa/data/tiktok_tracker.db')
cur = conn.cursor()
cur.execute('''
    SELECT may, tik, username, host_id
    FROM farm_account_info
    WHERE may = ? AND host_id = 'kibe'
    ORDER BY tik
''', (machine_num,))
rows = cur.fetchall()
```

- **Trường hợp A — Lệch Mapping Slot (Slot Mismatch):**
  - Tài khoản trong DB được gán ở slot $S_1$ (ví dụ slot 3), nhưng trong workbook `taikhoan_run_safe.xlsx` lại được xếp ở slot $S_2$ (ví dụ slot 7).
  - Hoặc slot trong ca chạy hiện tại hoàn toàn trống trong DB.
  - **Khắc phục:** Đồng bộ lại bảng `farm_account_info` và `account_mapping` ngay bằng SQL:
    ```sql
    UPDATE farm_account_info SET tik = <slot_chuan> WHERE username = '<target>' AND may = <m> AND host_id = 'kibe';
    UPDATE account_mapping SET tik = <slot_chuan> WHERE username = '<target>' AND may = <m>;
    ```

- **Trường hợp B — Văng Session / Nick Chưa Được Đăng Nhập Trên App:**
  - Nick có mapping khớp giữa DB và Workbook, nhưng khi mở Account Switcher trên app TikTok, handle của nick không xuất hiện.
  - **Khắc phục:** Tuyệt đối không chữa cháy tay qua adb input thô. Dùng flow nạp session chuẩn bằng tool chính thức của farm:
    ```bash
    python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID_HOAC_MAIL> --ss
    ```

- **Trường hợp C — Cảnh Báo Văng Phiên Giả (False-Positive Session Lost):**
  - Nick bị báo lỗi (ví dụ ca Slot 7) thực chất **VẪN ĐANG NẰM TRÊN SWITCHER VÀ HOÀN TOÀN LIVE**.
  - Thiết bị chỉ bị thiếu 1 nick ở slot khác (ví dụ slot 3 chưa được nạp hoặc từng bị logout làm nick ký sinh, khiến máy chỉ có 7 nick).
  - Mở Switcher trực tiếp để xác minh O(1) bằng deep link:
    ```bash
    adb -s <SERIAL> shell "am start -a android.intent.action.VIEW -d 'snssdk1180://user/profile' com.ss.android.ugc.trill"
    adb -s <SERIAL> shell "input tap 540 550"
    adb -s <SERIAL> shell "screencap -p /sdcard/sw.png"
    adb -s <SERIAL> pull /sdcard/sw.png D:/Taadaa/reports/m<N>_sw.png
    python C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py D:/Taadaa/reports/m<N>_sw.png
    ```

### 3. Kỷ Luật Điều Phối (Anti-Insanity & Proactiveness)
- **CẤM Hỏi Lại Khi Đã Có Lệnh Fix ("fix đi"):** Khi user đã chỉ đạo "fix did" (fix đi), Coordinator PHẢI CHỦ ĐỘNG THỰC THI (proactive execution) — cập nhật mapping DB, dọn dẹp orphan processes, kiểm tra hiện trường, nạp lại nick thiếu — TUYỆT ĐỐI KHÔNG dừng lại hỏi những câu hỏi lựa chọn hiển nhiên để user phải nhắc `?`.
- **Triệt Tiêu Orphan `grep.exe` Treo I/O Trên Windows:**
  - CẤM TUYỆT ĐỐI `grep -rn` quét sâu codebase trên Windows Git Bash / MSYS vì lệnh sẽ sinh ra các tiến trình `grep.exe` treo vĩnh viễn gây nghẽn I/O và CPU.
  - Lệnh dọn dẹp khẩn cấp:
    ```powershell
    powershell -Command "Get-Process -Name grep -ErrorAction SilentlyContinue | Stop-Process -Force"
    ```

### 4. Verification & Canary Nghiệm Thu
- Sau khi khôi phục session và chuẩn hóa DB, chạy canary 1 machine với 1-2 swipe:
  ```powershell
  scripts\run-feed-session.ps1 -Row <ROW> -Machines <N> -RecoveryTestSwipes 2 -Run
  ```
- Chụp ảnh nghiệm thu chuyển nick thành công và gửi `MEDIA:<path>` trước khi mở lại batch cho fleet.
