# In-flight Self-Healing vs Post-Session Recovery (S7 ADB/USB Transient Stalls)

> Date: 2026-10-16
> Ref: `python_runner/core/vpn_preflight.py`, `python_runner/flows/device_prepare.py`

## 1. Bẫy Kiến Trúc: "Chạy Xong Mới Cứu Hộ Là Vô Dụng"
- **User Invariant (2026-10-16):** *"Tại sao không tự động cứu hộ lúc cron chạy? Giờ chạy xong rồi cứu hộ làm gì?"*
- **Bản chất vấn đề:** Khi 25–40 workers khởi động đồng loạt trong `multi_machine_feed_session`, bus USB 2.0 EHCI bị nghẽn đệm tức thời.
- Một số máy bị delay lệnh ADB (`settings get global http_proxy` hoặc `dumpsys window`) vượt quá timeout 15s.
- Nếu runner chỉ bắt lỗi và fail-closed ngay lập tức (đánh dấu `blocked-proxy-vpn` hoặc `prepare-tiktok failed to focus`), máy bị loại khỏi toàn bộ ca nuôi. Sau khi ca kết thúc, dù watchdog hay coordinator có chạy `batch_recover_s7.py` kéo máy online trở lại thì **lượt nuôi của phiên đó đã bị mất hoàn toàn**.

## 2. Nguyên Tắc Cốt Lõi: In-flight Self-Healing (Tự Cứu Tại Chỗ Trước Khi Fail-Closed)
Mọi điểm kiểm tra thiết bị trong runner bắt buộc phải có cơ chế tự cứu phân tầng ngay tại hiện trường (in-flight self-healing):

### a) Tại Cửa Ngõ Proxy Preflight (`vpn_preflight.py`):
- Khi kiểm tra `settings get global http_proxy`:
  - Lần thử 1 (attempt 0): Nếu gặp `timed out` hoặc mất kết nối ADB/USB (`is_connection_lost`), **BẮT BUỘC** gọi ngay `adb.reconnect()` (hoặc `adb._reconnect_device()`).
  - Sleep 1.0s để socket handshake lại với daemon `adbd`.
  - Lần thử 2 (attempt 1): Thực thi lại lệnh. Nếu lần 2 vẫn hỏng mới ném `ConsumerPreflightError` để fail-closed.
- **Hiệu quả:** Cứu sống ngay lập tức các máy bị nghẽn microframe USB mà không bị văng oan sang `blocked-proxy-vpn`.

### b) Tại Cửa Ngõ Chuẩn Bị Ứng Dụng (`device_prepare.py`):
- Khi mở TikTok gặp lỗi `failed to focus target app after launch`:
  - Trước khi trả về `ExitStatus.FAIL`, runner tự động kích hoạt 1 nhịp `adb.reconnect()`.
  - Sleep 1.0s và gọi lại `read_focus()`.
  - Nếu focus đã vào đúng package TikTok (`com.ss.android.ugc.trill`), chuyển đổi kết quả thành công ngay lập tức (`prepare-tiktok-app completed after reconnect`).

## 3. Checklist Kiểm Tra Cho Mọi Runner Farm
1. **Có retry mù quáng không?** CẤM vòng lặp `except Exception: time.sleep(1); retry` mà không có hành động reset socket (`adb reconnect`).
2. **Có để rò rỉ IP không?** In-flight reconnect chỉ khôi phục socket ADB để đọc lại trạng thái thật; nếu sau reconnect mà proxy vẫn chết thì bắt buộc giữ nguyên fail-closed, cấm bypass VPN gate.
3. **Budget thời gian in-flight:** Mỗi nhịp reconnect tối đa 2s, không làm trễ tổng thời lượng ca nuôi.
