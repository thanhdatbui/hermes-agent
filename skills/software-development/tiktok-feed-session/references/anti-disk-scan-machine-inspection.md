# Anti-Disk-Scan Machine Inspection & Screen Lock Fix (Case 75 / Farm Rule)

## 1. Context & Pitfall (Anti-Pattern)
- **Sự cố:** Khi nhận alert `[MÁY N] DỪNG PHIÊN`, agent có xu hướng tự viết script Python dùng `os.walk`, `glob(recursive=True)`, `find`, `grep -r` để lùng sục file log trên toàn bộ thư mục `.ai-runs` hoặc ổ `D:\`.
- **Hậu quả:** Gây treo timeout 900s, vi phạm quy tắc vận hành farm, làm user ức chế do phản xạ chậm và quét đĩa tràn lan.

## 2. Standard Triage Tool (`inspect_machine.py`)
Khi nhận alert `[MÁY N]`, **100% chạy công cụ trích xuất nhanh duy nhất**:
```bash
python D:/Taadaa/tools/inspect_machine.py <N>
```
Tool thực thi trong < 1.0s:
1. Map serial và danh sách nick từ `taikhoan_run_safe.xlsx`.
2. Đọc nông tầng 1 run mới nhất trong `.ai-runs`, trích xuất `summary.txt` và 20 dòng cuối `log.jsonl`.
3. Gọi trực tiếp ADB lấy focus hiện tại (`dumpsys window`), trạng thái keyguard (`dumpsys window policy`), timeout màn hình (`settings`).
4. Chụp screencap hiện trường lưu ra `MEDIA:D:\Taadaa\m{N}_current.png`.

## 3. Lỗi Màn hình khóa Samsung (Keyguard Focus Loss - Máy 10)
- **Dấu hiệu:** `TikTok focus lost to launcher` hoặc mất focus về `StatusBar`/Keyguard.
- **Nguyên nhân:** Cài đặt `screen_off_timeout` bị set thấp (vd 600000ms = 10p) và `lock_screen_lock_after_timeout` = 5000ms khiến máy tự tắt và khóa màn hình khi cắm sạc.
- **Lệnh Fix qua ADB:**
```bash
adb -s <SERIAL> shell "
settings put system screen_off_timeout 2147483647
settings put global stay_on_while_plugged_in 7
settings put secure lock_screen_lock_after_timeout 2147483647
input keyevent 224
input keyevent 82
input swipe 360 1000 360 200 200
"
```
