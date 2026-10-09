# Universal Teardown & Device Lock Fail-Safe (Reaper 5p / Watchdog 90p)

## 1. Cơ chế Watchdog & Reaper Device Lock
- **Vấn đề thực tế:** Khi TTL của `blocked` lock là 60 phút, nếu Watchdog cảnh báo ngay tại mốc 60 phút và Reaper quét định kỳ 15 phút, sẽ xuất hiện cảnh báo ảo ("giật mình") trên Telegram trong khoảng thời gian lock đã hết hạn nhưng Reaper chưa tới tick quét.
- **Quy tắc phối hợp:**
  - **Reaper (`reap-dead-owner-locks.py`):** Quét định kỳ 5 phút/lần (`*/5 * * * *`). Tự động thu hồi các lock hết hạn (>60p) hoặc dead owner, đồng thời gọi `am force-stop` và `input keyevent 3` đưa máy về HOME.
  - **Watchdog (`watch_device_locks.py`):** Đặt ngưỡng cảnh báo là **90 phút** (`ALERT_THRESHOLD = 90`). Chỉ cảnh báo Telegram khi lock bị kẹt bất thường sau nhiều chu kỳ quét của Reaper (tiến trình zombie hoặc lỗi hệ thống).

## 2. Triết lý Universal Teardown: Luôn đóng app về HOME & Giải phóng Lock
- **Nguyên tắc cốt lõi:** KHÔNG BAO GIỜ giữ màn hình thiết bị thật để "chờ operator xem" và CẤM giữ lock `blocked` khi lỗi. Mọi hiện trường lỗi đều phải số hóa qua: **Log + XML hierarchy dump + Screencap** lưu vào artifact directory để debug O(1).
- **Giải phóng lock triệt để:** Giữ lock `blocked` trên đĩa sẽ giam thiết bị tới 60 phút, làm các phiên nuôi/batch kế tiếp bị `skipped-device-locked` hàng loạt. Dù phiên chạy thành công hay gặp lỗi/popup lạ, sau khi chụp hiện trường thì BẮT BUỘC phải force-stop app, đưa máy về HOME và **giải phóng device lock ngay lập tức** (`lease.release()` hoặc `lease.finish(succeeded=True)`).

## 3. Implementation Pattern chuẩn (Vượt qua Closeout AI Review)
Reviewer tại Closeout Gate kiểm tra rất gắt gao các anti-pattern teardown sau:

### Anti-Pattern 1: Ép Home và force-stop trong cùng 1 lệnh try
- **Rủi ro:** Nếu lệnh `force-stop` quăng ngoại lệ (timeout, transport error), lệnh gửi `input keyevent 3` sẽ bị bỏ qua.
- **Chuẩn hóa:** Thực thi độc lập từng lệnh:
```python
stop_ok = False
try:
    res1 = actual_adb.shell(["am", "force-stop", package], check=False)
    stop_ok = bool(getattr(res1, "ok", True))
except Exception as exc:
    logger.warning("force-stop exception: %s", exc)

home_ok = False
try:
    res2 = actual_adb.shell(["input", "keyevent", "3"], check=False)
    home_ok = bool(getattr(res2, "ok", True))
except Exception as exc:
    logger.warning("home exception: %s", exc)
```

### Anti-Pattern 2: Teardown làm chặn release lock hoặc giữ lock 'blocked' khi lỗi
- **Rủi ro:** Gọi `lease.finish(succeeded=goal_completed)` khi lỗi sẽ đánh dấu status thành `blocked`/`handoff` và giữ nguyên file lock trên đĩa, khiến phiên tiếp theo bị từ chối chạy (`skipped-device-locked`). Ngoài ra, bọc `try ... except Exception:` quanh teardown vẫn có thể bị vượt qua bởi `KeyboardInterrupt` hoặc `SystemExit` (`BaseException`), làm bỏ qua khối giải phóng lock.
- **Chuẩn hóa cấu trúc lồng `finally:` (luôn release lock):**:
```python
finally:
    try:
        try:
            teardown_app_to_home(target, package)
        except Exception as _td_exc:
            sys.stderr.write(f"[TEARDOWN_WARN] teardown error: {_td_exc}\n")
    finally:
        # Luôn giải phóng lock về trạng thái released, không giữ blocked
        try:
            lease.finish(succeeded=True)
        except Exception:
            lease.release()
```

### Anti-Pattern 3: Vi phạm Dry-Run Semantics
- **Rủi ro:** Khi gọi `teardown` trong failure branch mà không kiểm tra cờ `dry_run`, các ca dry-run test sẽ vô tình gửi lệnh ADB thật tới máy hoặc ném lỗi do thiếu ADB client.
- **Chuẩn hóa:** Hàm teardown hoặc khối gọi phải kiểm tra an toàn `not dry_run and adb_client is not None`.

## 4. Kỷ luật Khóa cho Tiện ích Phụ / Cron dọn dẹp (Clear Cache, Repair, Maintenance)
- **Bắt buộc khóa từng máy (`DeviceLock`):** Mọi script cron bảo trì (như `cron_clear_tiktok_cache.py`, dọn log, reset app) khi chạm vào thiết bị BẮT BUỘC phải acquire `DeviceLock(serial=serial, machine=str(m), project="clear-cache", bypass_proxy_readiness=True)`.
- **CẤM PHÁ LOCK KHI MÁY BẬN:** Nếu gặp `DeviceLockUnavailable` hoặc `DeviceLockNeedsUserDecision` (máy đang lướt feed, follow, reg, up video):
  - **TUYỆT ĐỐI CẤM** chạy lệnh ADB can thiệp.
  - **CẤM** `am force-stop` và **CẤM** `input keyevent KEYCODE_HOME`.
  - Bỏ qua máy, ngồi chờ máy rảnh nhả lock rồi dọn ở tick cron kế tiếp (chạy cuốn chiếu).
- **Chạy cuốn chiếu 1 lần/ngày:** Duy trì `STATE_FILE` ghi nhận `cleared_machines_today`. Máy nào đã dọn xong thì không dọn lại trong ngày. Toàn farm dọn xong thì script thoát im lặng (`silent`).
- **Rà soát & xóa bỏ tàn dư "Preserve Blocker Screen" trên toàn Farm:**
  - `multi_machine_feed_session.py`: Bắt buộc bật `_cleanup_close_all_on_error = True` (chụp screencap/XML lưu artifact xong là lập tức force-stop về Home, cấm treo app ở foreground).
  - `run_follow.py`: Luôn luôn force-stop TikTok và về Home trong `finally:`, không giữ màn hình lỗi.
  - `state_machine.py` (Upload): Sau khi dọn về Home thì giải phóng `lease.release()`, cấm giữ lock `handoff` giam máy 60 phút.
  - `tiktok_reg_live_email_v1.py`: Luôn bọc `am force-stop` và `input keyevent 3` trong `finally:` trước khi `device_lock.release()`.

