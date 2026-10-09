# Case 191: Sáng Màn Hình Hàng Loạt Do uiautomator Ép Timeout 25 Ngày (2147483647) & Treo App TikTok Do Teardown Thiếu Remote Host (24/09/2026)

## 1. Hiện Tượng & Phản Ánh Từ Người Vận Hành
- Người vận hành quan sát hiện trường dàn điện thoại (cả cụm Admin máy 201-280 lẫn cụm Kibe máy 1-80) đồng loạt bị sáng màn hình rực sáng, ngâm hàng giờ không tự tắt sau 10 phút nhàn rỗi dù trước đó hệ thống đã thiết kế cơ chế 10 phút tự tắt màn.
- Đồng thời, hàng loạt máy (như Máy 220 bên Admin) bị treo nguyên ứng dụng TikTok trên màn hình, không tự động đóng app và không quay về màn hình chính (Android Home Launcher).

## 2. Triệu Chứng Kỹ Thuật Hiện Trường (O(1) ADB Inspection)
1. **Kiểm tra `settings get system screen_off_timeout`:**
   - Trên các máy bị sáng màn hình, giá trị timeout trả về là `2147483647` (chính là $2^{31} - 1 = \text{Integer.MAX_VALUE}$ trong Java Android, tương đương **24,85 ngày**).
   - Kiểm tra `dumpsys power`:
     ```text
     Display Power: state=ON
     Screen off timeout: 2147483647 ms
     Looper state: Message 0: { when=+24d18h31m55s723ms }
     Wake Locks: size=0
     ```
     Android lên lịch hơn 24 ngày sau mới tắt màn hình. Dù không có ứng dụng nào giữ WakeLock, một khi màn hình đã sáng lên thì máy không bao giờ tự tắt sau 10 phút.
2. **Kiểm tra log Máy 220 (`runtime/admin/.../machine_220/log.jsonl`):**
   - Phiên chạy Ca 1 gặp nghẽn mạng Remote ADB server (`192.168.110.119:5037`) khi chạy 40 workers song song.
   - Các lệnh chụp màn hình, `am force-stop com.ss.android.ugc.trill` và `cleanup_close_all` bị timeout 15s.
   - Các ca nuôi kế tiếp (Row 4, Row 6) không có tài khoản cho Máy 220 trong Excel `taikhoan_run_safe.xlsx` nên runner skip ngay từ đầu (`account row 4 is empty... skipping`), bỏ mặc app TikTok mở trên màn hình suốt từ sáng đến chiều.

## 3. Hai Nguyên Nhân Cốt Lõi (Root Causes)

### Nguyên nhân 1: Cơ chế tự động ép sáng của uiautomator test stub & Thiếu Teardown Reset
- Khi runner nuôi feed hoặc recovery kích hoạt `dump_ui_xml` / `reset_atx_agent`, tiến trình con của APK test `com.github.uiautomator` bên trong Android tự động gọi ngầm:
  `Settings.System.putInt(..., SCREEN_OFF_TIMEOUT, Integer.MAX_VALUE)` (`2147483647`) để chống tắt màn hình làm đứt phiên automation.
- Trong `device_prepare.py`, hàm cấu hình 10 phút (`configure_device_screen_stay_on`) chỉ được gọi **duy nhất 1 lần ở đầu phiên**.
- Trong `multi_machine_feed_session.py`, khối `finally: teardown` ở cuối phiên (dòng ~5018) hoàn toàn **không có bước hoàn trả `screen_off_timeout` về lại `600000`** (10 phút) và `stay_on_while_plugged_in` về `0`. Kết quả: Bất kỳ máy nào từng chạy qua uiautomator thì timeout bị gán 25 ngày vĩnh viễn.

### Nguyên nhân 2: Fallback `_force_stop_tiktok_and_home` thiếu Remote Host & Nuốt lỗi Timeout
- Hàm `_force_stop_tiktok_and_home` có đoạn fallback qua `subprocess.run`:
  ```python
  if serial:
      resolved_adb = adb_path or r"C:/Program Files (x86)/xiaowei/tools/adb.exe"
      subprocess.run([resolved_adb, "-s", serial, "shell", "am", "force-stop", target_package], timeout=15)
  ```
  Đoạn này gọi trực tiếp ADB cục bộ trên Kibe mà **thiếu hoàn toàn `-H 192.168.110.119 -P 5037`** cho các máy Admin (`machine >= 200`), dẫn đến lỗi `device not found`.
- Khi `child_ctx.adb` bị timeout 15s do nghẽn socket ADB, ngoại lệ bị nuốt bởi `except Exception: pass`, fallback thất bại, khiến TikTok không bao giờ bị tắt.

## 4. Giải Pháp Chuẩn (Patch Contract & Tooling)

### 1. Patch `multi_machine_feed_session.py` (Repo `tiktok-luot nuoi acc`)
Nâng cấp hàm `_force_stop_tiktok_and_home` thành một quy trình Teardown hoàn chỉnh thực thi 5 lệnh bắt buộc:
```python
def _force_stop_tiktok_and_home(
    child_ctx: Any | None = None,
    *,
    serial: str | None = None,
    machine: int | None = None,
    adb_path: str | None = None,
) -> None:
    """Force-stop TikTok package, restore screen power timeout to 10m, and return device to Android Home screen.

    Prevents devices from sitting on feed/profile/gallery screens and keeps screen timeout
    from being stuck at 2147483647 (Integer.MAX_VALUE) caused by uiautomator stubs.
    """
    target_package = "com.ss.android.ugc.trill"
    if child_ctx is not None and hasattr(child_ctx, "config") and isinstance(child_ctx.config, dict):
        target_package = str(child_ctx.config.get("tiktok_package", target_package))

    teardown_cmds = (
        ["am", "force-stop", target_package],
        ["input", "keyevent", "3"],
        ["svc", "power", "stayon", "false"],
        ["settings", "put", "global", "stay_on_while_plugged_in", "0"],
        ["settings", "put", "system", "screen_off_timeout", "600000"],
    )

    # 1. Via child_ctx.adb if available
    adb_client = getattr(child_ctx, "adb", None) if child_ctx is not None else None
    if adb_client is not None and hasattr(adb_client, "shell"):
        for cmd in teardown_cmds:
            try:
                adb_client.shell(cmd, timeout=15)
            except Exception:
                pass
        return

    # 2. Fallback via serial and adb subprocess (ho tro Remote Admin)
    if serial:
        resolved_adb = adb_path or r"C:/Program Files (x86)/xiaowei/tools/adb.exe"
        base_cmd = [resolved_adb]
        if (machine is not None and machine >= 200) or os.environ.get("ADB_SERVER_SOCKET"):
            base_cmd.extend(["-H", "192.168.110.119", "-P", "5037"])
        base_cmd.extend(["-s", serial, "shell"])
        for cmd in teardown_cmds:
            try:
                subprocess.run(base_cmd + cmd, timeout=15, capture_output=True)
            except Exception:
                pass
```

### 2. Truyền `machine=account.machine` tại các Call Site Teardown
- Tại nhánh follow hard timeout (~dòng 2570):
  `_force_stop_tiktok_and_home(child_ctx, serial=account.serial, machine=account.machine)`
- Tại khối `finally: teardown` cuối phiên (~dòng 5018):
  `_force_stop_tiktok_and_home(child_ctx, serial=account.serial, machine=account.machine)`

### 3. Đồng bộ Unit Tests (`test_session_teardown_home.py`)
- Cập nhật test case kiểm tra `adb.shell` nhận đủ 5 lệnh teardown.
- Kiểm tra fallback `subprocess.run` với `machine=201` sinh đúng tham số `-H 192.168.110.119 -P 5037`.

### 4. Triển Khai Watchdog Dọn Dẹp Màn Hình & App Treo (`farm_idle_screen_and_app_healer.py`)
- Quét định kỳ song song 25 luồng trên cả Kibe Local và Admin Remote.
- Bỏ qua các máy đang có tiến trình giữ device lock (`~/.codex/device-locks/`).
- Với các máy rảnh: nếu phát hiện `screen_off_timeout != 600000` hoặc `stay_on != 0`, reset ngay về chuẩn 10 phút. Nếu phát hiện TikTok đang focus trên màn hình rảnh, `am force-stop` và bấm phím Home về Launcher.
