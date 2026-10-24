# SystemUI Keyguard Occlusion & TikTok Launch Auto-Healing (Samsung S7)

> Case reference: Case 82 (24/10/2026).
> Repos: `tiktok-luot nuoi acc/python_runner/flows/device_prepare.py`, `automation-core/src/automation_core/startup.py`.

## 1. Bản chất sự cố
Trong các ca nuôi acc hàng loạt (Ca 1 Phiên 1/2), nhiều máy (ví dụ 10 máy: M14, M29, M46, M251, M261, M264, M271, M277, M278, M279) báo lỗi `Lỗi mở/focus App TikTok` (`prepare-tiktok failed to focus TikTok after launch`), cá biệt một số máy kẹt tới 56 phút trong vòng lặp kiểm tra focus SystemUI.

## 2. Hai lỗi kiến trúc cốt lõi
1. **Bẫy Keyguard SystemUI (`recover_systemui_occlusion`):**
   - Khi Samsung S7 rơi vào màn hình khóa Keyguard (`com.android.systemui`), hàm cũ chỉ gửi `am broadcast CLOSE_SYSTEM_DIALOGS` và `input keyevent 4` (phím BACK).
   - Trên Galaxy S7 Android 8, phím BACK không có tác dụng mở khóa Keyguard non-secure. Thiết bị tiếp tục bị occlude bởi `com.android.systemui`, khiến các nhịp dumpsys window/power bị nghẽn (45-60s/nhịp).
   - **Khắc phục:** Bắt buộc gửi `input keyevent 82` (KEYCODE_MENU) để giải phóng màn hình khóa non-secure, kèm fallback vuốt mở khóa `input swipe 540 1400 540 500 300` nếu keyevent 82 chưa qua.

2. **Auto-Healing Relaunch chỉ chờ 2s kiểm tra 1 lần:**
   - Trong `prepare_tiktok_app_for_automation`, khi `reason == "failed to focus target app after launch"`, logic cũ chỉ gọi `am start`, ngủ 2.0s (`time.sleep(2.0)`) và đọc `read_focus()` duy nhất 1 lần.
   - Khi farm tải cao (80 máy chạy đồng thời), TikTok cold boot mất 3-8 giây để `SplashActivity` chiếm focus. Kiểm tra 1 lần sau 2s khiến auto-healing luôn phán đoán sai và báo thất bại.
   - **Khắc phục:** Mở vòng lặp polling 4 nhịp x 1.0s; nếu nhịp 2 vẫn chưa focus thì chủ động kích hoạt thẳng SplashActivity tường minh:
     ```python
     ctx.adb.shell(
         ["am", "start", "-n", f"{package_name}/com.ss.android.ugc.aweme.splash.SplashActivity"],
         timeout=ctx.timeout("adb_seconds", 10),
     )
     ```

## 3. Canary Runner Routing cho `tiktok-luot nuoi acc`
Khi chạy canary trên `tiktok-luot nuoi acc`:
- Bắt buộc truyền `--account-workbook D:/OneDrive/TaadaaData/<cluster>/taikhoan_run_safe.xlsx` và `--device-map-workbook D:/OneDrive/TaadaaData/<cluster>/PROXYgandienthoai.xlsx`.
- Runner mode là `multi-machine-feed-session` với `--recovery-test-swipes 2 --cleanup-on-stop`.
- Kiểm tra kết quả qua `summary.txt` (`status: success`, `total_swipes_completed: 2`), không được bắt buộc file `follow_result.json` (chỉ dành riêng cho repo `tiktok-follow`).
