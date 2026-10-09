# Canary Feed Swipe Smoke Runner Guide & Pitfalls

## 1. Context & Enforced CLI Constraints
Khi chạy kiểm thử canary đơn máy (`run_tiktok.py`) với chế độ `--mode feed-swipe-smoke`:
- Repo: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py`
- Fail-closed Argument Validation:
  1. `--account <account_name>`: Bắt buộc đối với các single-device mode (bao gồm `feed-swipe-smoke`). Thiếu cờ này script lập tức dừng với:
     `CONFIG_ERROR: --account is required for this mode unless feed-session-smoke loads --account-slots-file/--account-slot`
  2. `--allow-navigation-only`: Bắt buộc đi kèm khi chạy `feed-swipe-smoke` hoặc bất kỳ feed/navigation smoke nào. Thiếu cờ này script sẽ dừng với:
     `CONFIG_ERROR: feed-swipe-smoke requires --allow-navigation-only`
  3. `--allow-feed-swipe`: Bắt buộc để cho phép vuốt video.
  4. `--max-swipes`: Phải nằm trong khoảng `1 <= --max-swipes <= 3` đối với `feed-swipe-smoke`.

## 2. Standard Canary Execution Command
```bash
python "D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py" \
  --machine <MACHINE_NUM> \
  --device <DEVICE_SERIAL> \
  --account <TARGET_ACCOUNT> \
  --mode feed-swipe-smoke \
  --max-swipes 2 \
  --allow-navigation-only \
  --allow-feed-swipe \
  --allow-like \
  --allow-benign-popup-dismiss
```

## 3. Mandatory Teardown & Clean State
Sau khi chạy canary, luôn đưa thiết bị về trạng thái sạch:
```bash
# Force stop cả 2 package TikTok (global & SEA variant)
adb -s <DEVICE_SERIAL> shell am force-stop com.zhiliaoapp.musically
adb -s <DEVICE_SERIAL> shell am force-stop com.ss.android.ugc.trill

# Trở về màn hình Home
adb -s <DEVICE_SERIAL> shell input keyevent 3
```

## 4. Verification Evidence Screencap
Lưu ảnh chụp màn hình nghiệm thu sau teardown:
```bash
adb -s <DEVICE_SERIAL> exec-out screencap -p > "C:/Users/Kibe/AppData/Local/hermes/image_cache/canary_m<N>_after.png"
```
Báo cáo kết quả và dẫn link `MEDIA:C:/Users/Kibe/AppData/Local/hermes/image_cache/canary_m<N>_after.png`.
