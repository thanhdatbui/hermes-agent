# Kiến Trúc Gate Guard Khóa Thiết Bị Cho Cronjob & Quy Trình Review Đối Kháng 5 Vòng Đến APPROVED (19/10/2026)

## 1. Hiện Tượng Thực Tế & Root Cause

### Hiện tượng
Khi quan sát màn hình Phone Farm (Ruanwei), Operator thấy: Một cron đang mở tài khoản A, bất ngờ hàng loạt máy đồng loạt đóng sập TikTok rồi mở lại, hoặc bị dập về màn hình HOME liên tục.

### Root Cause
1. **Cron thiếu Device Lock:** Script đổi tên (`tiktok_rename_rolling_watchdog.py`) chỉ đọc danh sách lock của tiến trình khác (`get_locked_machines()`), nhưng khi kích hoạt chạy thì **không hề tạo lock file** (`~/.codex/device-locks/machine_XX.lock.json`).
2. **Nổ đồng loạt 25 Workers (Burst Mode):** Watchdog đặt `MAX_WORKERS = 25`, bốc 25 máy cùng lúc gọi `am force-stop` rồi `monkey` mở lại app để switch account.
3. **Va chạm Watchdog dọn dẹp:** Watchdog `farm-idle-screen-and-app-healer` chạy cùng chu kỳ 15 phút, quét thấy 25 máy trên mở TikTok mà không có lock ➔ Gửi lệnh `am force-stop com.ss.android.ugc.trill` + `input keyevent 3` đưa về HOME. Cron đổi tên thấy app bị sập lại cố mở lại ➔ Hai bên thi nhau đóng/mở đè lên nhau.

---

## 2. Chuẩn Hóa Kiến Trúc `farm_contract` & Chốt Chặn Cơ Học

### Schema Hợp đồng `farm_contract` bắt buộc khi tạo/sửa Cron can thiệp thiết bị:
```yaml
farm_contract:
  touches_device: true              # Bắt buộc khai báo; phát hiện lệnh thiết bị mà để false -> DENY
  device_lock: required             # Bắt buộc acquire_device_lock per-device
  mode: rolling                     # Bắt buộc 'rolling'; cấm tuyệt đối 'all' / 'burst'
  max_workers: 3                    # Trần 1..5; vượt quá 5 -> DENY
  release: per_device               # Xong máy nào nhả lock ngay máy đó
  lock_ttl_s: 300                   # TTL 5 phút mỗi máy, chống giữ lock chết
  on_device_fail: skip_continue     # Lỗi 1 máy không làm sập cả batch
```

### Triển khai Chốt chặn G1 tại `guard_cronjob_safety.py`:
- `ALLOWED_CONTRACT_KEYS` & `REQUIRED_CONTRACT_KEYS`: Chặn đứng contract rỗng, thiếu key hoặc chứa key lạ.
- `touches_device=false` Anti-Bypass: Quét chéo mã nguồn script thật; nếu phát hiện token/lệnh thiết bị (`monkey`, `am force-stop`, `input tap`, `com.ss.android.ugc.trill`) ➔ **DENY ngay lập tức (`FARM_CONTRACT_MISMATCH`)**.
- AST Device Lock Verification (`_has_ast_device_lock`):
  * Import bắt buộc khớp chính xác `automation_core.device_lock` (chặn import từ module giả mạo hay def local).
  * Thân khối `with acquire_device_lock(...)` bắt buộc chứa câu lệnh thực thi thiết bị thật (chặn `with lock: pass` hoặc lock rỗng).
- Evaluator Worker Cap: Đánh giá cả hằng số literal, biểu thức `BinOp` nhân (`5*5`), và `ThreadPoolExecutor(max_workers=...)`. Mọi giá trị > 5 hoặc <= 0 đều bị từ chối.

---

## 3. Bài Học Qua 5 Vòng Review Đối Kháng Với Claude Sonnet 5.5

Để đạt được `VERDICT: APPROVED` từ Claude Reviewer, Coordinator đã giải quyết dứt điểm các kẽ hở:

1. **Bẫy Hằng Số Chết trong Watchdog Orchestrator (Dead Constants Trap):**
   - File watchdog điều phối (`tiktok_rename_rolling_watchdog.py`) chỉ spawn runner con, nhưng còn sót lại hai hằng số cũ: `PKG = "com.ss.android.ugc.trill"` và `ADB_IME`.
   - Bộ quét của Guard phát hiện chuỗi này và đánh dấu watchdog là script can thiệp thiết bị trực tiếp nhưng thiếu lock, dẫn đến việc watchdog bị chính guard của mình chặn (`DEVICE_LOCK_REQUIRED`).
   - **Khắc phục:** Xóa bỏ triệt để các hằng số chuỗi chết không dùng trong orchestrator.

2. **Bẫy Ngoại Lệ Device Lock trong Runner:**
   - Khi bọc `acquire_device_lock(release_on_terminal=True)`, nếu chỉ bắt `DeviceLockUnavailable` thì khi gặp xung đột phân quyền hoặc readiness timeout sẽ bị crash bởi `DeviceLockNeedsUserDecision` hoặc `DeviceLockReadinessError`.
   - **Khắc phục:** Bắt trọn vẹn cả 3 ngoại lệ:
     ```python
     except (DeviceLockUnavailable, DeviceLockNeedsUserDecision, DeviceLockReadinessError) as e:
         print(f"SAFE_SKIP: May {MACHINE_ID} ({SERIAL}) dang ban hoac chua san sang: {e}")
         return 0
     ```

3. **Bẫy Console Window trong Mọi Lệnh Subprocess:**
   - Trong môi trường Windows, mọi lệnh `subprocess.run` / `Popen` trong cron/runner (kể cả gọi runner con, adb, hay powershell OCR) nếu thiếu `creationflags=subprocess.CREATE_NO_WINDOW` (`0x08000000`) đều bị `guard_cronjob_safety.py` chặn đứng vì nguy cơ giật pop-up console cướp focus.

4. **Kỷ Luật Kiểm Thử Bằng File Thật (Integration Tests):**
   - Claude Reviewer từ chối nghiệm thu nếu test suite chỉ toàn mock/fake data.
   - Bắt buộc bổ sung các bài test tích hợp chạy trực tiếp trên file script thật (`test_real_watchdog_passes_guard`, `test_real_runner_passes_guard`) chứng minh 100% file vận hành thực tế vượt qua guard.
