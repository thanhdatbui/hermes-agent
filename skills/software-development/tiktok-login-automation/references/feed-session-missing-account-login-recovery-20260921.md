# Văng Acc / Thiếu Nick Trong Feed Session — Quy Trình Xử Lý Bắt Buộc (2026-09-21)

## NGUYÊN TẮC BẮT BIẾN — USER RULE
> "Ủa chứ bị văng acc thì sao k gọi script tiktok log in đăng nhập lại acc bị văng"

**BẮT BUỘC khi phát hiện `account-switcher-missing-expected` / nick thiếu trên thiết bị:**
KHÔNG CHỈ báo cáo bị động. PHẢI đề xuất và thực thi ngay lệnh đăng nhập lại:
```bash
# Đăng nhập nick cụ thể bị thiếu:
python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <MACHINE_ID> --email <USERNAME_OR_EMAIL> --ss
```

---

## 3 BƯỚC XỬ LÝ CHUẨN (PHẢI ĐỦ CẢ 3)

### B0: Phân Biệt False Positive Trước Khi Đăng Nhập
- Mở TikTok → Profile Tab → Tap header → Chụp ảnh Switcher thực tế.
- Dùng WinRT OCR đọc danh sách nick đang có trong app.
- So với `taikhoan_run_safe.xlsx`: nick nào chưa hiển thị trong Switcher mới là nick **thực sự thiếu**.
- ⚠️ Alert `account-switcher-missing-expected` của batch aggregator có thể là **false positive**: nick bị báo lỗi thực tế vẫn LIVE trong máy nhưng có nick khác ở slot khác bị thiếu, hoặc `tiktok_tracker.db` bị lệch mapping `tik` (slot number).

### B1: Fix DB Mapping Nếu Lệch
```python
import sqlite3
conn = sqlite3.connect('D:/Taadaa/data/tiktok_tracker.db')
cur = conn.cursor()
# Đồng bộ cả 2 bảng
cur.execute("UPDATE farm_account_info SET tik = ? WHERE username = ? AND may = ? AND host_id = 'kibe'", (correct_slot, username, machine_id))
cur.execute("UPDATE account_mapping SET tik = ? WHERE username = ? AND may = ?", (correct_slot, username, machine_id))
conn.commit()
conn.close()
```

### B2: Đăng Nhập Lại Nick Thiếu
```bash
cd D:/Taadaa/Tiktok_Reg
python tiktok_login_v1.py <MACHINE_ID> --email <USERNAME_OR_EMAIL> --ss
```
- Script tự đọc TOTP secret từ workbook và xử lý email OTP Hotmail/Gmail — **không ngắt giữa chừng**.
- Chụp ảnh Switcher nghiệm thu sau khi xong (`MEDIA:D:/Taadaa/reports/m<N>_switcher_after_login.png`).

---

## PITFALL: Auto-Login Recovery Trong Feed Session Bị Nghẽn Ngầm
`_maybe_recover_missing_account_via_login` trong `feed_swipe_smoke.py` tự động gọi:
`D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py`

Môi trường này có thể bị lỗi chéo (ví dụ: `ImportError: cannot import name '_imaging' from 'PIL'`), khiến subprocess crash âm thầm (`returncode != 0`), feed session tiếp tục như không có gì. Coordinator phải fallback sang gọi `tiktok_login_v1.py` thủ công nếu auto-recovery không hoạt động.

---

## PITFALL: grep.exe Quét Rộng Trên Windows MSYS Bash = I/O Deadlock
CẤM `grep -rn <pattern> D:/Taadaa` bất kỳ. Trên Windows MSYS bash, `grep.exe` khi quét nhiều file lớn/ổ đĩa sẽ bị kẹt I/O vô thời hạn, chiếm CPU và buộc các tiến trình subagent sau bị timeout. Luôn dùng Python `open()` chỉ đọc file cụ thể, hoặc `grep -n <pattern> /path/to/specific/file.py`.
