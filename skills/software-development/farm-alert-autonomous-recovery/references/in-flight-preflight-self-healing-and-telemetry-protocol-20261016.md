# In-flight Preflight Self-Healing & Telemetry Protocol (2026-10-16)

## 1. Triết Lý Vận Hành: In-flight Self-Healing vs Post-Hoc Rescue
- **Chống cứu hộ muộn màng (Post-Hoc Trap):** Chờ ca nuôi chạy xong rồi mới kích hoạt script cứu hộ (`batch_recover_s7.py`) là quá muộn — hàng chục máy đã bị loại bỏ oan trong phiên, gây lãng phí tài nguyên farm và làm ô nhiễm log watchdog thành nhãn "Lỗi App TikTok/Script".
- **Nguyên tắc In-flight Self-Healing:** Hệ thống phải tự cứu hộ ngay tại thời điểm xảy ra sự cố (in-flight) trong từng luồng worker trước khi quyết định loại bỏ máy khỏi ca.

## 2. Hai Điểm Neo In-flight Tối Quan Trọng
1. **Chốt chặn Proxy Preflight (`vpn_preflight.py`):**
   - Khi lệnh kiểm tra proxy (`settings get global http_proxy`) bị timeout do nghẽn I/O USB 2.0 hoặc socket LAN ở lần thử đầu (`_attempt == 0`):
     - Ghi nhận: `logger.info("[auto-healing] reconnecting client...")`
     - Kích hoạt: `adb.reconnect(timeout=5.0)`
     - Chờ 1.0s để socket ADB thiết lập lại và thử lại attempt 1.
     - Vẫn giữ nguyên cơ chế Fail-Closed: nếu sau khi reconnect mà lần 2 vẫn timeout thì mới ném `ConsumerPreflightError` để đảm bảo an toàn IP.

2. **Chốt chặn Khởi Chạy App (`device_prepare.py`):**
   - Khi app TikTok được khởi chạy nhưng hệ điều hành trễ cập nhật window/focus dẫn đến `failed to focus target app after launch`:
     - Ghi nhận: `logger.info("[auto-healing] reconnecting client...")`
     - Kích hoạt: `ctx.adb.reconnect(timeout=5.0)`
     - Đọc lại focus sau 1.0s; nếu khớp với target package (`com.ss.android.ugc.trill`), tự động hoàn tất `SUCCESS` thay vì trả về `FAIL`.

## 3. Tiêu Chuẩn Kỹ Thuật Khi Viết Recovery Code (Closeout Gate Approved >= 85)
- **CẤM Bare Except Pass:** Tuyệt đối không nuốt lỗi âm thầm bằng `except Exception: pass`. Mọi failure khi cứu hộ bắt buộc phải được ghi log:
  ```python
  try:
      logger.info("[auto-healing] reconnecting client...")
      if hasattr(adb, "reconnect"):
          adb.reconnect(timeout=5.0)
  except Exception as exc:
      logger.warning("[auto-healing] reconnect failed: %s", exc)
  ```
- **Không Dò Tìm Private API:** Không dùng `hasattr(adb, "_reconnect_device")`. Chỉ tương tác qua public contract `adb.reconnect(timeout=5.0)`.
- **Test Evidence Bắt Buộc:** Mọi nhánh logic auto-healing mới bổ sung bắt buộc phải có unit test mô phỏng kịch bản (mock `reconnect` được gọi và focus/status hồi phục thành công).
