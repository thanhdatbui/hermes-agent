# TikTok Account Switcher Touch Dispatch & Tọa độ Tap Pitfall

## Bối cảnh & Hiện tượng (Canary Máy 46 - 2026-09-07)
Trong bottom sheet "Chuyển đổi tài khoản" của TikTok (~v46.x) trên thiết bị Samsung:
- Row container (`com.ss.android.ugc.trill:id/lpw`): bounds `[0, y1][1080, y2]`, `clickable="true"`.
- Username TextView (`com.ss.android.ugc.trill:id/nba`): bounds `[252, y1_t][542, y2_t]`, `clickable="false"`.
- Checkmark "Dấu kiểm" (`com.ss.android.ugc.trill:id/fmc`): `[960, y1_c][1032, y2_c]`, `clickable="false"`.
- Avatar icon: vùng `[0, y1]` đến `[252, y2]`.

## Pitfall Touch Event Dispatching trên Samsung
1. **Tap trúng Child TextView (`clickable=false`):**
   - Khi tính toán `best_bounds` thu hẹp về TextView con (ví dụ `center = [397, 708]`), lệnh `input tap 397 708` gửi tọa độ rơi vào bên trong `id/nba`.
   - Trên một số bản Android/Samsung touch framework, sự kiện tap vào View con `clickable=false` có thể bị swallow hoặc không bubble ngược lên parent container `id/lpw` đúng cách, dẫn đến việc tap thành công về mặt OS (`input tap` exit code 0) nhưng TikTok không kích hoạt logic switch tài khoản (`Dấu kiểm` vẫn ở nick cũ).
2. **Khu vực tương tác an toàn cần kiểm tra:**
   - Cần kiểm tra kỹ giữa việc tap vào:
     - Avatar / Icon bên trái row container: `x ∈ [100, 200]`.
     - Vùng trung tâm container: `x = 540`.
     - Toàn bộ row container `id/lpw`.
   - Nếu tap vào text bị nuốt, phải kiểm tra XML sau tap (`ui.xml` tại `profile_preflight_verify_1_identity_guard` hoặc `profile_preflight_switcher_2_guard`) xem `Dấu kiểm` có đổi sang target account hay chưa.

## Quy trình Canary Verification chuẩn
1. **Compile check:**
   ```bash
   python -m py_compile python_runner/flows/feed_swipe_smoke.py
   ```
2. **Dọn stale lock trước khi chạy:**
   ```bash
   rm -f /c/Users/Kibe/.codex/device-locks/*<N>*.lock.json
   ```
3. **Kích hoạt Canary Test:**
   ```bash
   env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
   ```
4. **Kiểm tra hiện trường log:**
   - Không grep diện rộng.
   - Đọc trực tiếp file summary và log của máy:
     `.ai-runs/<timestamp>/machines/machine_<N>/<timestamp>/summary.txt`
     `.ai-runs/<timestamp>/machines/machine_<N>/<timestamp>/log.jsonl`
   - So sánh selector `center` của action `tap_expected_account` với trạng thái `current_username` và `Dấu kiểm` trong `ui.xml`.
