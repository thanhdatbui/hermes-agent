# Quy Chuẩn Lướt Warmup Feed Sau Reg & Fail-Safe Close App Về Home (2026-09-06)

## 1. Mục đích
- Ngăn ngừa TikTok Risk Engine gắn cờ tài khoản rác/bot do dwell time = 0s (vừa đăng ký xong tắt app ngay).
- Bảo đảm thiết bị luôn ở trạng thái màn hình Home sạch sẽ, không bị treo app TikTok lơ lửng khi script kết thúc (kể cả khi thành công hay thất bại).

## 2. Quy tắc Lướt Feed Nuôi Nick Ngay Sau Reg (`run_warmup_feed`)
- **TÁI SỬ DỤNG RUNNER CHÍNH THỨC (CẤM TỰ VIẾT CODE VUỐT / JITTER TAY):**
  - Mọi logic lướt feed chuẩn (anti-detect jitter, video play telemetry, dwell time, đóng benign popup) nằm ở repo `D:\Taadaa\tiktok-luot nuoi acc`.
  - Tuyệt đối CẤM code lại vòng lặp swipe, jitter, sleep trong `social_reg_v1.py`.
  - Gọi runner chính thức qua subprocess:
    ```bash
    D:/Taadaa/python-envs/automation/Scripts/python.exe \
      "D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py" \
      --device <serial> \
      --account <handle> \
      --machine <stt> \
      --mode feed-session-smoke \
      --max-swipes <N> \
      --allow-feed-swipe \
      --allow-navigation-only \
      --allow-benign-popup-dismiss \
      --no-verify-profile \
      --cleanup-on-stop
    ```
- **Random số lượng video:**
  - Tự động gán `random.randint(4, 8)` mỗi lần chạy (phá tính cố định deterministic của bot).
  - Tùy chỉnh qua CLI: `--feed-swipes <int>`.
  - Tắt khi cần reg tốc độ cao: cờ `--no-feed-after-reg` hoặc env `TIKTOK_REG_FEED_AFTER_REG=0`.
- **Cô lập môi trường & Lock:**
  - Xóa `PYTHONPATH` khỏi env con để không đụng thư viện runtime cha.
  - Gán `env["CODEX_DEVICE_LOCK_DIR"] = tempfile` riêng để không xung đột với device lock của tiến trình reg cha.
  - Kiểm tra `script_path.exists()` trước khi gọi để tránh ném exception ngầm.
  - Bọc `try/except` toàn bộ: nếu feed session lỗi chỉ log cảnh báo, tuyệt đối không làm fail kết quả đăng ký tài khoản đã thành công.
- **Thứ tự thực thi:**
  - Bắt buộc LƯU TRACKING XONG (ghi deferred tracking JSON hoặc ghi trực tiếp `taikhoan_dat_v2_updated .xlsx`) mới bắt đầu gọi `run_warmup_feed`.
  - Tránh gọi kép `_post_reg_cleanup`: `ensure_profile_completed_and_track` có khối `finally:` bọc ngoài, trong `run_warmup_feed` không gọi lặp lại.

## 3. Quy tắc Fail-Safe Đóng App Về Home (CẤM TREO MÁY KHI SCRIPT FAIL)
- Bất kể script dừng ở nhánh nào:
  1. `register()`: Khối `finally: if not reg_success: _post_reg_cleanup(device_id, stt=stt)`
  2. `_do_register()`: Nhánh `else:` (khi `wait_login_success` thất bại / pending) tự động gọi `_post_reg_cleanup(device_id, stt=stt)` sau khi chụp ảnh alert.
  3. `ensure_profile_completed_and_track()`: Khối `finally: _post_reg_cleanup(device_id, stt=stt)` bọc toàn bộ.
  4. Nhánh `--resume`: Khối `finally: if not resume_success: _post_reg_cleanup(device, stt=stt)`
- `_post_reg_cleanup`: Thực hiện `am force-stop com.ss.android.ugc.trill` và gửi `input keyevent 3` (KEYCODE_HOME).
