# TikTok Upload: Xử lý Popup Thành tích "Tổng lượt thích" & Thoát màn Camera LIVE (2026-10-17)

## 1. Popup Milestone "Tổng lượt thích" che Switcher
- **Hiện tượng:** Khi runner mở Profile để chuyển sang nick đích, TikTok hiện popup chúc mừng thành tích: *"Tổng lượt thích: <username> đã nhận tổng cộng X lượt thích cho tất cả video"* kèm nút `[OK]`. Popup này đè lên vùng header và làm sai lệch hierarchy XML khiến `prepare_switcher_anchor` không phát hiện được anchor row hoặc tap trượt, dẫn đến `ACCOUNT_SWITCHER_FAILED / SWITCHER_NOT_CONFIRMED`.
- **Giải pháp vá chuẩn O(1) trong `scripts/tiktok_workflow/adapter.py` (`prepare_switcher_anchor`):**
  ```python
  if any(m in lowered for m in ("tổng lượt thích", "tổng số lượt thích")):
      dismissed = False
      for lbl in ("OK", "ok", "Đóng", "Close", "Xong"):
          if self._tap_if_found(xml_text, text=lbl) or self._tap_if_found(xml_text, content_desc=lbl):
              logger.info("[PREPARE_SWITCHER] Dismissed 'Tổng lượt thích' via %s", lbl)
              dismissed = True
              break
      if not dismissed:
          self.tap(540, 1400)
          logger.info("[PREPARE_SWITCHER] Dismissed 'Tổng lượt thích' via tap(540, 1400)")
      time.sleep(1.0)
      xml_text = self.dump_ui()
      lowered = xml_text.casefold()
  ```
  Đồng thời sắp xếp candidates theo tọa độ $y$ (`candidates.sort(key=lambda c: c[2])`) để luôn ưu tiên header trên cùng.

## 2. Kẹt Màn hình Camera LIVE sau khi Đăng Video (`CAMERA / TẠO / LIVE`)
- **Hiện tượng:** Sau khi bấm Đăng ở state `POST`, app TikTok đôi khi tự động chuyển người dùng sang màn hình Camera tạo video/phát LIVE (`CAMERA / TẠO / LIVE`).
- **Bẫy:** App TikTok nuốt/chặn phím `BACK` của Android trên màn hình này. Phương thức `adapter.back()` không làm màn hình camera biến mất, dẫn đến `_is_live_surface` vẫn trả `True` và runner văng lỗi fail-closed `POST_VERIFY_LIVE_SURFACE_BLOCKED`.
- **Giải pháp vá chuẩn O(1) trong `scripts/tiktok_workflow/state_machine.py` (`_dismiss_live_surface`):**
  Tap trực tiếp vào tọa độ nút đóng `[X]` ở góc trên bên trái `(60, 140)` kết hợp với lệnh `adapter.back()`:
  ```python
  # On TikTok LIVE camera screen, tap 'X' button (top-left: x~60, y~140) or send BACK
  adapter.tap(60, 140)
  adapter.back()
  ```

## 3. CẢNH BÁO BẪY 'proxy watcher did not publish post-reboot readiness'
- **Bản chất:** Khi runner soft-reboot máy để cứu hộ UI, lúc máy khởi động lại nó chờ cờ file marker readiness tại `C:\Users\Kibe\.codex\device-readiness\<hash>.json`. Nếu không có, nó báo lỗi timeout proxy watcher.
- **CẤM TUYỆT ĐỐI BẬT VICHANGER:** Farm Kibe đã bỏ hoàn toàn ViChanger từ tháng 9/2026. Toàn bộ 80 máy chạy qua proxy Wi-Fi / MikroTik Singbox (`192.168.110.2:20001..20080`). Tuyệt đối CẤM bật Scheduled Task `GanProxyWatcherTray` hay chạy lại `gan_proxy_fleet.py`!
- **Giải phóng cờ:** Dùng `automation_core.readiness.mark_proxy_state(serial, 'proxy_ready')` nếu cần bypass cờ readiness, không đụng vào watcher cũ.
