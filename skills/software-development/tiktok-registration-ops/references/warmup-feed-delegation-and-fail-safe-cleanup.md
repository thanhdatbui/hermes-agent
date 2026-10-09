# Warmup Feed Delegation and Fail-Safe Cleanup Invariant

## 1. User Mandate & Anti-Reinvention Rule
- Khi cần thực hiện thao tác lướt feed làm ấm nick (warmup feed / telemetry dwell time) sau khi đăng ký tài khoản mới:
  - **CẤM:** Tự code tay vòng lặp swipe thô, tự tính tọa độ jitter, tự sleep thủ công trong `social_reg_v1.py`.
  - **BẮT BUỘC:** Tái sử dụng runner chuẩn hóa của repo `tiktok-luot nuoi acc` (`run_tiktok.py`) qua `subprocess.run`, chỉ cấu hình số lần vuốt ngẫu nhiên (`random.randint(4, 8)`).
- **Yêu cầu dọn dẹp:** Dù script thành công hay thất bại ở bất kỳ khâu nào, luôn luôn phải force-stop app TikTok và đưa máy về Home màn hình chính (`_post_reg_cleanup`), tuyệt đối không để app treo ở màn hình lỗi hay popup.

## 2. Cross-Consumer Subprocess Isolation Pattern
Khi gọi `run_tiktok.py` từ bên trong `Tiktok_Reg` (`social_reg_v1.py`):
- **Python Binary:** Ưu tiên `D:/Taadaa/python-envs/automation/Scripts/python.exe`, fallback `sys.executable`.
- **Script Path:** `D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py`.
- **Environment Isolation:**
  - `env.pop("PYTHONPATH", None)`: Bắt buộc xóa `PYTHONPATH` khỏi subprocess env. Nếu không, Python sẽ nạp site-packages của môi trường host/Hermes (ví dụ PIL `_imaging` binary mismatch dẫn đến ImportError).
  - `env["CODEX_DEVICE_LOCK_DIR"] = str(Path(tempfile.gettempdir()) / "tiktok_feed_lock")`: Chuyển lock dir của runner con sang thư mục temp riêng để không va chạm lock máy của phiên đăng ký hiện tại.
- **Command flags chuẩn:**
  ```python
  cmd = [
      python_bin,
      str(script_path),
      "--device", str(device_id),
      "--account", str(account_handle or "feed_warmup"),
      "--mode", "feed-session-smoke",
      "--max-swipes", str(num_videos),
      "--allow-feed-swipe",
      "--allow-navigation-only",
      "--allow-benign-popup-dismiss",
      "--no-verify-profile",
      "--cleanup-on-stop",
  ]
  if stt is not None:
      cmd.extend(["--machine", str(stt)])
  ```

## 3. Fail-Safe Cleanup Architecture across All Abort/Error Paths
Tất cả các điểm dừng hoặc lỗi trong luồng đăng ký phải được bảo vệ bằng `_post_reg_cleanup(device_id, stt=stt)`:
1. `run_warmup_feed`: Bọc `try ... except Exception as e` (ghi nhận warning mà không ngắt flow), trong khối `finally:` gọi `_post_reg_cleanup(device_id, stt=stt)`.
2. `ensure_profile_completed_and_track`: Bọc toàn bộ phần thực thi từ đầu đến cuối trong `try ... finally: _post_reg_cleanup(device_id, stt=stt)`. Khi phát hiện CAPTCHA blocker, thiếu TikTok username, duplicate handle, hoặc lỗi ghi workbook, hàm sẽ ném ngoại lệ nhưng vẫn bảo đảm dọn dẹp app về Home.
3. `register`: Khối `finally: if not reg_success:` gọi `_post_reg_cleanup(device_id, stt=stt)` và giải phóng reservation token.
4. `_do_register`: Nhánh `else:` khi `not ok` gọi `_post_reg_cleanup(device_id, stt=stt)`.
5. Nhánh `--resume` trong `__main__`: Khối `finally: if not resume_success:` gọi `_post_reg_cleanup(device, stt=stt)`.
