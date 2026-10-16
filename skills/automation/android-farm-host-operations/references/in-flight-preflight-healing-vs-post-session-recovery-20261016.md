# In-Flight & Pre-Session Auto-Recovery vs Post-Session Reactive Triage (2026-10-16)

> Ref: User critique 2026-10-16: "Tại sao k tự động cứu hộ lúc cron chạy. H chạy xong r cứu hộ làm lol gì"

---

## 1. Bẫy Vận Hành: "Cứu Hộ Vuốt Đuôi" Sau Khi Ca Chạy Đã Kết Thúc
- **Hiện tượng:** Khi cronjob báo cáo Ca nuôi (ví dụ: `tiktok-feed-session-watchdog`) hoàn tất với 20–25 máy báo lỗi (`blocked-proxy-vpn`, `device is offline or ADB/USB disconnected`, `prepare-tiktok failed to focus`), Coordinator mới nhảy vào chạy `recover_stuck_s7.py` hoặc `batch_recover_s7.py` để kéo máy lên `device`.
- **Tác hại nghiêm trọng:** 
  - Toàn bộ các máy bị lỗi đã bị rớt mất lượt nuôi acc trong phiên đó.
  - Cứu hộ sau khi runner đã tắt chỉ có tác dụng chuẩn bị cho ca sau, hoàn toàn không cứu vãn được sản lượng và tỷ lệ thành công của ca hiện tại.

---

## 2. Nguyên Nhân Kỹ Thuật Khiến Máy Bị Rớt Oan Lúc Khởi Chạy
1. **Lỗ hổng Fast Fail-Closed tại `python_runner/core/vpn_preflight.py`:**
   - Khi 25 workers đồng loạt mở máy, bus USB 2.0 EHCI bị nghẽn tức thời (microframe contention).
   - Bước kiểm tra đầu tiên (`adb.shell(["settings", "get", "global", "http_proxy"], timeout=15.0)`):
     * Attempt 0 bị timeout -> code chỉ `time.sleep(1.0)` rồi gọi lại đúng lệnh đó mà **KHÔNG hề gọi `adb reconnect`**.
     * Attempt 1 tiếp tục timeout -> lập tức raise `ConsumerPreflightError(f"device is offline or ADB/USB disconnected for {serial}: {p_err}")`.
     * Runner bắt lỗi này, gán nhãn `blocked-proxy-vpn` và hủy hoàn toàn nhiệm vụ của máy đó trong cả phiên.
   - Trong khi cơ chế tự cứu `adb.reconnect()` lại nằm ở Bước 2 phía dưới (trong khối `check_android_vpn`), nhưng máy đã bị loại từ Bước 1 nên không bao giờ chạm tới được!

2. **Thiếu Pre-Session Readiness Gate tại `tiktok_runner.py`:**
   - Trước khi phát lệnh chạy `run-feed-session.ps1`, cron launcher chỉ kiểm tra tài khoản trống (`_preflight_ensure_accounts`).
   - Hoàn toàn thiếu bước kiểm tra nhanh và giải phóng socket/shell (`batch_recover_s7.py`) trước khi đổ tải.

---

## 3. Quy Chuẩn Kiến Trúc Cứu Hộ Tự Động 2 Tầng (In-Flight & Preflight)

### Tầng 1: In-Flight Self-Healing tại `vpn_preflight.py`
- Ngay tại bước đọc `settings get global http_proxy`:
  * Nếu attempt 0 gặp `timed out` hoặc connection lost:
    1. Kích hoạt Level 3 Reconnect: `adb.reconnect()` (hoặc `adb -s <serial> reconnect`).
    2. Chờ 2.0 giây để daemon ADB hoàn tất bắt tay `A_SYNC`.
    3. Thực hiện attempt 1 với timeout đầy đủ.
  * Chỉ khi đã thực hiện reconnect mà vẫn không có phản hồi mới raise `ConsumerPreflightError`.

### Tầng 2: Preflight Device Readiness Gate tại `tiktok_runner.py`
- Trước khi spawn `run-feed-session.ps1` (hoặc trước mỗi batch máy):
  * Chạy quét nhanh `batch_recover_s7.py --cluster <cluster> --max-workers 8` (Level 1 soft recovery + Level 3 reconnect) trong 10–15s.
  * Đưa toàn bộ các máy đang đơ shell hoặc kẹt pipe USB về trạng thái `device` và tắt màn hình (`223`) trước khi phát lệnh nuôi.
