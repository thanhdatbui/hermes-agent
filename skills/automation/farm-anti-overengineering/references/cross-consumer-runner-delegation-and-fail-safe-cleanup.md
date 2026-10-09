# Cross-Consumer Runner Delegation and Fail-Safe Cleanup Invariant

## 1. Bài học từ User Correction (06/09/2026)
- **Tình huống:** Trong luồng đăng ký tài khoản (`social_reg_v1.py`), agent tự viết tay vòng lặp swipe nuôi feed For You: tự tính tọa độ jitter, tự `time.sleep`, tự gọi `swipe(device_id, ...)`.
- **Phản ứng của User:** *"Random jitter video quần què gì thế cái đó có trong hàm script lướt feed r mày chỉ gọi lại và cài random số lần vuốt chơi thôi. Mà có fail script cũng close app về home chứ k đc treo."*
- **Nguyên tắc cốt lõi:**
  1. **Không phát minh lại bánh xe:** Hệ thống Taadaa đã có các runner chuyên trách được kiểm thử kỹ lưỡng (như `run_tiktok.py` trong repo `tiktok-luot nuoi acc`). Khi một consumer khác (như `Tiktok_Reg`) cần thao tác lướt feed, BẮT BUỘC ủy quyền trực tiếp cho runner đó qua subprocess, chỉ truyền số lần swipe ngẫu nhiên (`random.randint(4, 8)`).
  2. **Fail-Safe Cleanup Invariant:** Bất kể tiến trình chạy thành công hay gặp lỗi (CAPTCHA, missing profile handle, duplicate handle, timeout, script crash), app trên điện thoại PHẢI ĐƯỢC ĐÓNG và thiết bị PHẢI VỀ HOME. Tuyệt đối không để app treo ở màn hình lỗi.

## 2. Kỹ thuật cách ly môi trường khi gọi Subprocess giữa các Consumer Repo
Khi gọi runner Python từ repo khác qua `subprocess.run`:
- **Python Executable:** Dùng môi trường venv chuẩn của hệ thống:
  `D:/Taadaa/python-envs/automation/Scripts/python.exe` (fallback `sys.executable`).
- **Xóa `PYTHONPATH` khỏi `env` (`env.pop("PYTHONPATH", None)`):**
  Tránh lỗi Import / Binary mismatch khi subprocess vô tình nạp các thư viện từ virtualenv của Hermes host (ví dụ lỗi `ImportError: cannot import name '_imaging' from 'PIL'`).
- **Cách ly thư mục Device Lock (`CODEX_DEVICE_LOCK_DIR`):**
  Đặt biến môi trường `env["CODEX_DEVICE_LOCK_DIR"] = str(Path(tempfile.gettempdir()) / "tiktok_feed_lock")`. Nếu không đổi, runner con sẽ kiểm tra lock thư mục mặc định và bị chặn bởi chính lock của tiến trình mẹ đang giữ.
- **Tham số dòng lệnh runner chuẩn:**
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

## 3. Kiến trúc Fail-Safe Cleanup (`finally: _post_reg_cleanup`)
Mọi điểm rẽ nhánh và hàm thực thi chính phải được bọc `finally:` để đảm bảo cleanup:
- `ensure_profile_completed_and_track()`: Bọc toàn bộ logic trong `try ... finally: _post_reg_cleanup(device_id, stt=stt)`. Bất kỳ RuntimeError (CAPTCHA blocker, thiếu handle) đều kích hoạt force-stop TikTok và ấn KEYCODE_HOME.
- `run_warmup_feed()`: Bọc trong `try ... except Exception ... finally: _post_reg_cleanup(device_id, stt=stt)`.
- `register()`: Khối `finally: if not reg_success: release_machine_reg_reservation(stt); _post_reg_cleanup(device_id, stt=stt)`.
- `_do_register()`: Nhánh `else:` khi `not ok` gọi `_post_reg_cleanup(device_id, stt=stt)`.
- Nhánh `--resume` trong `__main__`: Khối `finally: if not resume_success: release_machine_reg_reservation(stt); _post_reg_cleanup(device, stt=stt)`.
