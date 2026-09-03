# Samsung Screen Lock Timeout & Direct Log Triage (2026-09-02)

## Context & Root Cause
- **Triệu chứng:** Alert `[MÁY N] DỪNG PHIÊN: TikTok focus lost to launcher`. Màn hình thiết bị hiển thị màn hình khóa Samsung ("Vuốt màn hình để mở khóa"), `dumpsys window policy` báo `showing=true`, `mCurrentFocus=StatusBar`.
- **Nguyên nhân cốt lõi:**
  1. Máy bị cấu hình sai timeout: `settings get system screen_off_timeout` bị set thành giá trị nhỏ (vd: 600000 ms / 10 phút) thay vì `2147483647` (không bao giờ tắt).
  2. `lock_screen_lock_after_timeout` bị set 5000 ms. Khi hết timeout hoặc nguồn sạc chập chờn, máy tắt màn hình và tự động kích hoạt Keyguard Samsung.
  3. Keyguard che khuất TikTok làm mất focus về StatusBar, kịch bản feed-session phát hiện focus lost và dừng phiên an toàn.

## Khắc phục trực tiếp trên thiết bị (ADB)
1. Mở khóa màn hình:
   ```bash
   adb -s <SERIAL> shell "input keyevent 224 && input keyevent 82 && input swipe 360 1000 360 200 200"
   ```
2. Cài đặt chuẩn vĩnh viễn không tắt màn hình và không khóa:
   ```bash
   adb -s <SERIAL> shell "settings put system screen_off_timeout 2147483647"
   adb -s <SERIAL> shell "settings put global stay_on_while_plugged_in 7"
   adb -s <SERIAL> shell "settings put secure lock_screen_lock_after_timeout 2147483647"
   ```
3. Xác minh:
   ```bash
   adb -s <SERIAL> shell "dumpsys window policy | grep showing" # showing=false
   adb -s <SERIAL> exec-out screencap -p > mN_unlocked.png
   ```

## Quy tắc đọc Log khi nhận Alert [MÁY N]
- **BẮT BUỘC:** Đi thẳng vào đúng thư mục run gần nhất: `.ai-runs/<latest_run>/machines/machine_N/` hoặc đọc trực tiếp `summary.txt` / `log.jsonl` / `ui.xml` cụ thể.
- **CẤM TUYỆT ĐỐI:** Dùng `os.walk`, `glob(recursive=True)`, `search_files`, `find`, `grep -r` quét đệ quy qua ổ `D:` hoặc thư mục `.ai-runs` vì số lượng file rất lớn sẽ gây nghẽn timeout và vi phạm quy tắc vận hành.
