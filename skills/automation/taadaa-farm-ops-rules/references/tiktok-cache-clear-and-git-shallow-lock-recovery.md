# TikTok Cache Clearing & Windows Git Shallow Lock Recovery Patterns

## 1. Dọn Dẹp Cache TikTok Ban Đêm (`clear-tiktok-cache.py` / `cron_clear_tiktok_cache.py`)

### A. Hiện tượng lỗi:
- Báo cáo cronjob `end-of-day-clear-tiktok-cache` (ID `79021fa79d8b`) ghi nhận hàng loạt máy bị `Timeout` (18-30 máy) ở khung 03:00 - 04:00 sáng.
- Màn hình các máy dính lỗi ở trạng thái đen (`mWakefulness=Dozing`, `Display Power: state=OFF`).

### B. Nguyên nhân cốt lõi (Anti-Patterns):
1. **Màn hình tắt (Dozing) làm chết Path 1 (Deep Link):**
   - Lệnh `am start -a android.intent.action.VIEW -d 'snssdk1180://clean_cache'` chỉ hoạt động khi thiết bị đã thức. Nếu không gọi `input keyevent KEYCODE_WAKEUP` và `wm dismiss-keyguard` trước khi bắn intent, Activity không hiển thị foreground và UI dump thất bại.
2. **Outer Subprocess Timeout (120s) quá ngắn cho Path 2 (In-App Settings):**
   - Khi Path 1 thất bại, script fallback về Path 2 (Profile -> Menu 3 gạch -> Cài đặt và quyền riêng tư -> vuốt 6 lần tìm "Giải phóng dung lượng" -> Xóa cache -> Verify 0,0MB).
   - Khi chạy đa luồng đồng thời (20-40 workers), hàng đợi ADB và ATX UI dump bị chậm lại, toàn bộ chu trình Path 2 cần từ 130s đến 160s.
   - Trần cứng `timeout=120` ở `cron_clear_tiktok_cache.py` làm tiến trình bị kill cưỡng bức ngay ở giây 120 (`subprocess.TimeoutExpired`).

### C. Quy chuẩn khắc phục chuẩn (Case 91 Invariant):
1. **Đánh thức bắt buộc:** Luôn gọi `KEYCODE_WAKEUP` và `wm dismiss-keyguard` ngay đầu hàm `clear_cache` trước khi thử bất kỳ Deep Link nào.
2. **Budget Timeout:** Outer timeout trong `cron_clear_tiktok_cache.py` bắt buộc đặt tối thiểu **240s – 300s**.
3. **Concurrency:** Giữ `MAX_WORKERS = 20` (tránh 40 workers làm nghẽn socket ADB daemon và USB bus).
4. **Delays tối ưu:** Giữ `PAGE_DELAY=1.2s`, `AFTER_TAP_DELAY=1.8s`, `AFTER_CONFIRM_DELAY=2.5s`, timeout ATX dump 10-12s, swipe sleep 0.6s.

---

## 2. Xử Lý Kẹt Git Shallow Lock & Timeout Trên Windows (`.git/shallow.lock`)

### A. Hiện tượng lỗi:
- Lệnh `git fetch`, `git pull --rebase`, hoặc `git push` bị treo vô tận và đụng trần timeout của terminal (180s).
- Lệnh xóa file lock báo lỗi: `rm: cannot remove '.git/shallow.lock': Device or resource busy`.

### B. Nguyên nhân:
- Repo shallow clone (`--depth`) trên Windows khi gặp lỗi mạng hoặc bị kill giữa chừng sẽ để lại tiến trình ngầm `git.exe` (chạy lệnh `git --shallow-file ... rev-list --objects`).
- Tiến trình này chiếm giữ file lock độc quyền ở tầng kernel Windows, chặn toàn bộ các lệnh git tiếp theo.

### C. Quy trình phục hồi 3 bước:
1. **Kill sạch các tiến trình Git mồ côi:**
   ```bash
   cmd.exe /c "taskkill /F /IM git.exe"
   ```
2. **Xóa triệt để các file lock chết:**
   ```bash
   rm -f .git/shallow.lock .git/objects/maintenance.lock .git/index.lock
   ```
3. **Sử dụng `--no-ahead-behind` hoặc fetch có giới hạn:**
   - Với shallow repo lớn trên Windows, thêm cờ `--no-ahead-behind` khi kiểm tra `git status` để tránh nghẽn CPU/Disk.
