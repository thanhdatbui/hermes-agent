# Cơ chế xử lý & Phục hồi khi màn hình com.github.uiautomator (ATX Agent) xuất hiện

## 1. Hiện tượng & Triệu chứng
- Khi chạy automation trên farm (đặc biệt các máy yếu hoặc sau khi ATX agent / UIAutomator khởi động lại / crash):
  - Màn hình điện thoại hiển thị app `com.github.uiautomator` (giao diện ATX agent / UIAutomator helper / nút "Stop atx agent").
  - Màn hình này thường tự động xoay ngang (landscape) hoặc làm che khuất hoàn toàn TikTok.
  - Package foreground: `com.github.uiautomator`, Activity: `com.github.uiautomator.MainActivity`.

## 2. Điểm yếu & Lỗ hổng hiện tại trong `tiktok-luot nuoi acc`
Hiện tại repo `tiktok-luot nuoi acc` **chưa có cơ chế tự phục hồi toàn diện** cho lỗi này:
1. **Preflight dừng máy ngay lập tức (`device_prepare.py` & `multi_machine_feed_session.py`)**:
   - `prepare_tiktok_app_for_automation` (qua `core_prepare_app_for_automation`) chỉ `am force-stop` TikTok rồi gọi `monkey` mở TikTok.
   - Hoàn toàn KHÔNG force-stop `com.github.uiautomator`.
   - Nếu màn ATX đang chiếm foreground, focus poll 10 lần đều fail vì `focused_package == com.github.uiautomator != com.ss.android.ugc.trill`.
   - Hàm `popup_dismisser` (`dismiss_tiktok_popups`) không nhận diện được màn ATX.
   - Kết quả: Ném `ExitStatus.FAIL: prepare-tiktok failed to focus TikTok after launch`, script coi là lỗi nghiêm trọng và **DỪNG MÁY NGAY TẠI PREFLIGHT**.
2. **Observe coi là mất focus nghiêm trọng (`flows/observe.py` & `core/safety.py`)**:
   - `core/safety.py` thấy `focus_package == com.github.uiautomator` (không nằm trong `SYSTEM_OVERLAY_PACKAGES` hay TikTok packages).
   - Trả về `SAFETY_FAILED` ("TikTok focus lost").
   - Vô hiệu hóa toàn bộ nhánh blanket dismiss và trả về `ExitStatus.FAIL`.
3. **Swipe recovery bị abort do ngoại lai (`flows/feed_swipe_smoke.py`)**:
   - Tại `_swipe_recovery_on_stuck` (dòng 7630 & 8042), code kiểm tra:
     `if pre_dismiss_pkg not in tiktok_pkgs: return None` (kèm `pre_dismiss_external_focus_abort`).
   - Màn ATX bị coi là package ngoài luồng và script từ chối dismiss, dẫn đến kẹt và fail session.
4. **Handler trong `benign_popup_registry.py` là code chết**:
   - Dù có đăng ký `uiautomator_app_overlay`, handler này không bao giờ được gọi ở preflight/observe, và cũng không có lệnh `am force-stop com.github.uiautomator`.

## 3. Kiến trúc chuẩn 3 tầng phòng thủ ATX từ `Tiktok_Reg` (`social_reg_v1.py`)
Bên repo `Tiktok_Reg`, cơ chế phòng vệ được xây dựng 3 tầng cực kỳ chặt chẽ:
```python
# TẦNG 1: Pre-launch cleanup (trước khi bật TikTok)
fg_before = _foreground_focus(device_id)
xml_before = get_ui_xml(device_id)
if "com.github.uiautomator" in fg_before or 'package="com.github.uiautomator"' in xml_before:
    log("   [preflight] uiautomator foreground before launch -> force-stop uiautomator and HOME")
    shell(device_id, "am", "force-stop", "com.github.uiautomator")
    shell(device_id, "am", "force-stop", "com.github.uiautomator.test")
    shell(device_id, "input", "keyevent", "3")
    time.sleep(0.5)

# TẦNG 2: In-launch polling loop (trong vòng lặp chờ TikTok foreground)
if 'package="com.github.uiautomator"' in xml or "com.github.uiautomator" in _foreground_focus(device_id):
    if not uia_retry:
        log("   [preflight] uiautomator foreground -> force-stop uiautomator, HOME and relaunch TikTok")
        shell(device_id, "am", "force-stop", "com.github.uiautomator")
        shell(device_id, "am", "force-stop", "com.github.uiautomator.test")
        shell(device_id, "input", "keyevent", "3")
        time.sleep(0.8)
        shell(device_id, "am", "force-stop", APP_PACKAGE)
        time.sleep(0.3)
        _launch_tiktok(device_id)
        time.sleep(2.5)
        uia_retry = True
        continue
    else:
        log("   [preflight] uiautomator still blocking after retry -> force-stop and HOME")
        shell(device_id, "am", "force-stop", "com.github.uiautomator")
        shell(device_id, "am", "force-stop", "com.github.uiautomator.test")
        shell(device_id, "input", "keyevent", "3")

# TẦNG 3: Post-timeout fallback (hết timeout vẫn bị ATX chặn)
if "com.github.uiautomator" in fg_after or 'package="com.github.uiautomator"' in xml:
    log("   [preflight] com.github.uiautomator in foreground -> force-stop uiautomator, HOME and retry TikTok launch")
    shell(device_id, "am", "force-stop", "com.github.uiautomator")
    shell(device_id, "am", "force-stop", "com.github.uiautomator.test")
    shell(device_id, "input", "keyevent", "3")
    time.sleep(1.0)
    shell(device_id, "am", "force-stop", APP_PACKAGE)
    time.sleep(0.5)
    _launch_tiktok(device_id)
    time.sleep(2.5)
    # Poll thêm 25s để TikTok kịp lên
```

## 4. Quy tắc áp dụng khi sửa / nâng cấp `tiktok-luot nuoi acc`
Khi gặp tình trạng máy bị dừng do màn ATX:
1. Bắt buộc force-stop **cả 2 packages**: `com.github.uiautomator` VÀ `com.github.uiautomator.test`.
2. Bắt buộc gửi phím **HOME (`input keyevent 3`)** để phá lock xoay màn hình ngang của Activity trước khi mở lại TikTok.
3. Vị trí ưu tiên cần vá:
   - `flows/device_prepare.py` (hoặc `automation_core/startup.py`): thêm tầng preflight dọn dẹp uiautomator trước khi gọi `launch_app`.
   - `core/safety.py`: không coi `com.github.uiautomator` là terminal failure ngay nếu có handler phục hồi.
   - `flows/feed_swipe_smoke.py`: cập nhật `_swipe_recovery_on_stuck` để không abort khi gặp màn ATX mà thực hiện chuỗi force-stop uiautomator + HOME + relaunch.

## 5. Cập nhật giải pháp triển khai (Implemented in 2026-09)
Chi tiết triển khai tự động phục hồi và loại bỏ hoàn toàn các lệnh `am start / monkey com.github.uiautomator`: xem file tham chiếu `references/uiautomator-foreground-occlusion-recovery.md`.
- `capture_recovery.py`: Bỏ toàn bộ `am start -n com.github.uiautomator/.MainActivity` và `monkey -p com.github.uiautomator 1`.
- `flows/observe.py`: Thêm `recover_uiautomator_occlusion` kích hoạt khi `focus.get("package") in UIAUTOMATOR_PACKAGES`.
- `flows/device_prepare.py`: Gọi `recover_uiautomator_occlusion` trong `_verify_tiktok_focus_with_retries` và `read_focus()`.
