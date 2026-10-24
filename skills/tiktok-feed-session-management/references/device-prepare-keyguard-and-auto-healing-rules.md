# TikTok Feed Device Prepare & Keyguard Auto-Healing (Samsung S7)

> Case: Case 82 (24/10/2026)
> Target: `python_runner/flows/device_prepare.py`

## 1. Keyguard / SystemUI Occlusion Invariant
- Trên Samsung Galaxy S7 (Android 8), khi `get_focused_activity` trả về `com.android.systemui`, việc chỉ gửi `am broadcast CLOSE_SYSTEM_DIALOGS` và `input keyevent 4` (phím BACK) **hoàn toàn vô hiệu với màn hình khóa Keyguard**.
- Bắt buộc phải gửi `input keyevent 82` (KEYCODE_MENU) để mở khóa non-secure Keyguard.
- Bổ sung fallback vuốt mở khóa `input swipe 540 1400 540 500 300` nếu sau keyevent 82 trạng thái vẫn là `com.android.systemui`.

## 2. Multi-Pass Polling Auto-Healing
- Khi TikTok không focus được sau lệnh launch khởi động, auto-healing nhánh `reason == 'failed to focus target app after launch'` không được chỉ chờ 2.0s và kiểm tra 1 lần.
- Bắt buộc polling 4 nhịp x 1.0s.
- Nếu ở nhịp 2 vẫn chưa focus, chủ động bắn Intent tường minh tới `com.ss.android.ugc.aweme.splash.SplashActivity` (`am start -n <package>/com.ss.android.ugc.aweme.splash.SplashActivity`).
- Thoát ngay vòng lặp khi `recheck_pkg == package_name`.

## 3. Canary Runner Contract for Feed Repo
- Repo `tiktok-luot nuoi acc`:
  - `--account-workbook D:/OneDrive/TaadaaData/<cluster>/taikhoan_run_safe.xlsx`
  - `--device-map-workbook D:/OneDrive/TaadaaData/<cluster>/PROXYgandienthoai.xlsx`
  - `--recovery-test-swipes 2 --cleanup-on-stop`
  - Kiểm tra kết quả qua `summary.txt` (`status: success`, `total_swipes_completed: 2`).
