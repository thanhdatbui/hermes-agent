# UIAutomator Stub Monkey Call Chain & Screen Trap Diagnostic (2026-09-05)

## 1. Bản đồ lệnh khởi động com.github.uiautomator

### Core (`D:\Taadaa\automation-core\src\automation_core\persistent_ui.py`)
- **`reset_atx_agent(adb, timeout=20)`** (Đã FIX 2026-09-05):
  - Loại bỏ hoàn toàn `monkey -p com.github.uiautomator 1`.
  - Khởi động background stub không có UI qua control endpoint:
    `adb.shell([ATX_AGENT_PATH, "curl", "-X", "POST", f"http://127.0.0.1:{ATX_DEVICE_PORT}/uiautomator"], timeout=min(3.0, remaining()), check=False)`
  - Polling `ps -A` chờ stub sẵn sàng (tối đa 8s) + sleep ổn định `min(0.5, remaining())`.
  - Quét `dumpsys window windows`: nếu `com.github.uiautomator` lọt vào foreground thì mới gửi `adb.shell(["input", "keyevent", "3"], timeout=min(2.0, remaining()), check=False)` để hạ xuống background.
- **`_session_dump_attempt`** (Dòng 350 - 351):
  - Khi `attempt_number > 1` (trong `capture_atx_session_ui` có `restart_attempts >= 1`): gọi `reset_atx_agent(adb, timeout=min(15.0, timeout))` (an toàn, không còn làm bung UI monkey).

### Consumer (`D:\Taadaa\tiktok-luot nuoi acc`)
- **`python_runner/core/ui_capture.py::capture_required_ui_result`** (Dòng 109 - 221):
  - **Dòng 194**: Sau khi 3 lần `capture_atx_session_ui` ban đầu fail, gọi `reset_atx_agent(adb, timeout=reset_timeout)`.
  - **Dòng 201**: Gọi `capture_atx_session_ui(adb, timeout=min(20.0, rem_attempt), restart_attempts=1)` -> nếu fail tiếp, `_session_dump_attempt` (dòng 351) gọi `reset_atx_agent` lần thứ 2.
- **`python_runner/core/capture_recovery.py::_direct_shell_recapture`** (Dòng 4468 - 4541):
  - **Dòng 4514 - 4519**: Khi `uiautomator dump` trả exit code 137:
    ```python
    if getattr(dumped, "exit_code", None) == 137:
        try:
            adb.shell(["monkey", "-p", "com.github.uiautomator", "1"], timeout=6.0, check=False)
        except Exception:
            pass
    ```
    *(Cảnh báo: Hàm này gọi monkey nhưng KHÔNG hề gửi `keyevent 3` để hạ MainActivity).*
- **`python_runner/core/capture_recovery.py` - các vị trí `am start` trực tiếp**:
  - Dòng 2553: `ForegroundServiceDirectPortFeedSession.start()`
  - Dòng 5319: `recover_uiautomator_bridge_repair()`
  - Dòng 5647: `recover_uiautomator_bridge_jsonrpc()`
  - Dòng 6053: `recover_uiautomator_reboot_jsonrpc()`
  - Dòng 6451: `recover_uiautomator_post_reboot_online_jsonrpc()`

---

## 2. Call Chains chi tiết từ Entry Points

### Chain 1: Feed session smoke / Multi-machine feed (Primary Flow)
```
run_tiktok.py / run-feed-session.ps1
  └─► flows/multi_machine_feed_session.py::execute_multi_machine_feed_session()
        └─► flows/feed_swipe_smoke.py::feed_session_smoke()
              ├─► flows/device_prepare.py::prepare_android_device_for_automation() (read_ui / close_all_recent_apps)
              ├─► flows/observe.py::observe_current_screen() (_capture_xml)
              ├─► flows/feed_swipe_smoke.py::_capture_xml_text() (dòng 1728)
              ├─► flows/feed_swipe_smoke.py::like_video() (dòng 13319)
              ├─► flows/calibrate_screens.py (calibrate_screens)
              └─► flows/benign_popup.py (dismiss_*)
                    │
                    ▼
              core/ui_capture.py::capture_required_ui()
                └─► core/ui_capture.py::capture_required_ui_result()
                      ├─► 3 attempts capture_atx_session_ui fail
                      ├─► Dòng 194: reset_atx_agent()  [KÍCH HOẠT 1]
                      │     └─► persistent_ui.py:581: monkey -p com.github.uiautomator 1
                      └─► Dòng 201: capture_atx_session_ui(restart_attempts=1)
                            └─► persistent_ui.py:351: reset_atx_agent()  [KÍCH HOẠT 2]
                                  └─► persistent_ui.py:581: monkey -p com.github.uiautomator 1
```

### Chain 2: Shell Dump OOM Exit 137 Recovery Ladder
```
Legacy recovery handler (recover_uiautomator_foreground_service / recover_capture_stack)
  └─► core/capture_recovery.py::_direct_shell_recapture()
        └─► uiautomator dump trả exit code 137
              └─► Dòng 4517: adb.shell(["monkey", "-p", "com.github.uiautomator", "1"])
                    (Không có KEYEVENT 3, com.github.uiautomator.MainActivity chiếm trọn foreground)
```

---

## 3. Root Cause: Tại sao màn hình UIAutomator bị treo / đè màn hình?

1. **Timeout Exhaustion làm rớt `input keyevent 3`**:
   - Trong `persistent_ui.py::reset_atx_agent`, lệnh hạ màn hình nằm ở cuối:
     ```python
     if monkey_called and remaining() > 0:
         adb.shell(["input", "keyevent", "3"], timeout=min(2.0, remaining()), check=False)
     ```
   - Khi caller truyền `timeout` ngắn (hoặc `remaining_budget` trong `ui_capture.py` chỉ còn vài giây), các bước `pkill`, `server -d`, `curl`, và vòng lặp `ps -A` tiêu hao hết thời gian khiến `remaining() <= 0` $\rightarrow$ `keyevent 3` **bị bỏ qua hoàn toàn**.
2. **Timing Asynchronous của ActivityManager**:
   - `monkey -p com.github.uiautomator 1` kích hoạt `MainActivity` qua ActivityManager. Trên các dòng máy Samsung S7 (Android 7/8) phần cứng yếu, `MainActivity` mất 0.5s - 1.5s mới render xong.
   - Nếu `keyevent 3` được gửi đi khi `MainActivity` chưa hoàn thành khởi động, phím Home chỉ tác động lên màn hình cũ; ngay sau đó `MainActivity` mới bật lên và kẹt lại ở foreground.
3. **Mất định hướng (Orientation Trap)**:
   - `MainActivity` của stub UIAutomator thường xoay ngang màn hình (landscape 1920x1080), phá vỡ layout portrait của TikTok và gây lỗi `TikTok not foreground after clean launch`.

---

## 4. Tình trạng tại repo `tiktok-luot nuoi acc`: ĐÃ ĐƯỢC GIẢI QUYẾT TRIỆT ĐỂ (2026-09-05)

Trước đây, khi màn hình `com.github.uiautomator` xuất hiện, repo `tiktok-luot nuoi acc` bị dừng phiên do:
1. **Safety Gate ngắt phiên ngay lập tức (`core/safety.py`)**: `safety_check()` trả về `SAFETY_FAILED` ("TikTok focus lost").
2. **Vòng lặp startup chờ trong vô vọng (`flows/device_prepare.py`)**: `_verify_tiktok_focus_with_retries` chờ 15s rồi quăng `prepare-tiktok failed to focus TikTok after launch`.

### Các bước đã fix và verify (2026-09-05):
1. **Dọn dẹp triệt để `capture_recovery.py`**:
   - Loại bỏ lệnh gọi `monkey -p com.github.uiautomator 1` trong `_direct_shell_recapture` (dòng 4517).
   - Thay thế toàn bộ các lệnh `am start -n com.github.uiautomator/.MainActivity` (dòng 2553, 5319, 5647, 6053, 6451) sang recording evidence `{attempted: False}`, không còn kích hoạt MainActivity của uiautomator.
2. **Thêm hàm `recover_uiautomator_occlusion(ctx, package_name)` trong `flows/observe.py`**:
   - `am force-stop com.github.uiautomator`
   - Gửi phím Home: `input keyevent 3`
   - Relaunch lại TikTok: `monkey -p <package_name> -c android.intent.category.LAUNCHER 1`
   - Đọc lại focus activity.
3. **Tích hợp tự động vào các chốt chặn chính**:
   - Trong `observe_current_screen()` (`flows/observe.py`): Nếu phát hiện `focus.get("package") in UIAUTOMATOR_PACKAGES`, tự động chạy recovery trước khi kiểm tra Safety Gate, ngăn chặn false-alarm `SAFETY_FAILED`.
   - Trong `_verify_tiktok_focus_with_retries()` (`flows/device_prepare.py`): Khi xác minh focus sau launch app, nếu thấy uiautomator lập tức kích hoạt recovery để đưa TikTok lên thay vì chờ timeout 15s.
4. **Verification**:
   - Bộ unit test `python_runner/tests/test_uiautomator_occlusion_recovery.py` (4/4 tests passed).
   - Test regression `test_ui_dump.py` và `test_observe.py` pass.
