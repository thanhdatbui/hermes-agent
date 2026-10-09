# Consumer Startup Recents Fallback Fail-Safe & Recovery Ladder Invariant

## 1. Bối cảnh & Cạm bẫy (Pitfall: Uncaught ADBError in Startup Fallbacks)
Trong các consumer script (như `scripts/tiktok_workflow/state_machine.py`), khi `prepare_android_for_automation` từ `automation_core.startup` trả về `startup.ok = False` (do Samsung hiển thị empty recents bằng text tiếng Việt "Không có ứng dụng đã dùng gần đây" mà detector cũ chưa bắt được), consumer thường có hàm fallback như `_verify_localized_empty_recents(adb)` để kiểm tra lại:
- Gửi `input keyevent 187` mở Recent apps.
- Gọi `dump_current_ui()` để đọc text UI rỗng.
- Gửi `input keyevent 3` trong `finally` để quay về màn hình chính.

### Cạm bẫy:
1. `adb.shell(["input", "keyevent", "187"], timeout=10, check=False)` khi gặp timeout tầng transport (`subprocess.TimeoutExpired`) sẽ bị `AdbClient` raise `ADBError("adb command timed out: ...")`.
2. Nếu lệnh shell này nằm ngoài khối `try ... except`, exception sẽ bắn thẳng ra ngoài state handler (`_handle_connect_device`).
3. Khi state handler bị crash bởi unhandled exception, **toàn bộ Ladder Recovery 3 bước (B1 ATX-kill -> B2 relaunch -> B3 soft reboot)** theo chuẩn `PROJECT_RULES.md` bị bỏ qua hoàn toàn, dẫn đến job bị abort sớm hoặc chuyển sang `MANUAL_REVIEW` sai lệch mà không chạy đủ các tầng hồi phục.
4. Tương tự, nếu lệnh `keyevent 3` trong khối `finally` không được bọc `try...except`, một transport hang khác sẽ nuốt mất kết quả và làm vỡ luồng dọn dẹp.

---

## 2. Quy tắc thiết kế Fail-Safe bắt buộc (Fail-Safe Contract)

Mọi hàm phụ trợ kiểm tra / fallback trong pha startup và connect device BẮT BUỘC tuân thủ:

1. **Top-level fail-safe:** Bọc toàn bộ logic trong `try ... except Exception as exc: logger.warning(...); return False`. Không bao giờ để ngoại lệ từ ADB hoặc XML dump lọt ra ngoài.
2. **Guarded Finally:** Trong khối `finally`, mọi lệnh gọi ADB (như bấm Home `keyevent 3`) BẮT BUỘC bọc trong `try ... except Exception: pass`.
3. **Defense-in-depth tại Caller:** Tại vị trí gọi fallback trong `_handle_connect_device()`, bọc tiếp bằng try-except riêng:
   ```python
   empty_recents_ok = False
   try:
       empty_recents_ok = self._verify_localized_empty_recents(self.context.adb_client)
   except Exception as exc:
       logger.warning("[ANDROID_STARTUP] Lỗi kiểm tra fallback empty recents: %s", exc)
       empty_recents_ok = False
   ```
4. **Bảo toàn Recovery Ladder:** Chỉ khi `empty_recents_ok` là `True` mới bypass lỗi. Nếu `False`, BẮT BUỘC để luồng đi vào nhánh `else` thực thi tuần tự đủ:
   - **B1:** ATX-kill (`_recover_uiautomator` + reset atx-agent).
   - **B2:** Relaunch (`prepare_android_for_automation` retry).
   - **B3:** Bounded soft reboot (`_maybe_soft_reboot_recovery`).
