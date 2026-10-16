# In-Flight Self-Healing vs Post-Hoc Recovery (Chống Cứu Hộ Vuốt Đuôi Sau Ca)

## 1. Sự Cố Thực Tế (16/10/2026)
- **Triệu chứng:** Ca 1 Phiên 1 (Row 2 Sáng) có 20/80 máy Kibe và 25/80 máy Admin báo fail. Watchdog báo "Mất kết nối ADB/USB" và "Lỗi App TikTok/Script".
- **Hành vi sai lầm của Coordinator:** Chờ toàn bộ phiên nuôi 45 phút chạy xong xuôi, ra báo cáo rồi mới chạy script cứu hộ `recover_stuck_s7.py` / `batch_recover_s7.py` để kéo máy lên xanh.
- **Phản ứng của User:** *"Tại sao k tự động cứu hộ lúc cron chạy. H chạy xong r cứu hộ làm lol gì"*.
- **Hậu quả:** 45 máy bị mất lượt nuôi oan trong phiên sáng, tài khoản không được lướt feed, dưỡng sinh hay tương tác, làm giảm hiệu suất farm.

## 2. Điểm Mù Kiến Trúc Trong `vpn_preflight.py`
- Khi 25–40 worker cùng khởi động đồng loạt, bus USB 2.0 EHCI bị nghẽn đệm microframe.
- Bước đầu tiên của mỗi máy là kiểm tra proxy:
  `adb.shell(["settings", "get", "global", "http_proxy"], timeout=15.0)`
- **Lỗ hổng:**
  ```python
  # Code cũ:
  for _attempt in range(2):
      try:
          p_res = adb.shell(["settings", "get", "global", "http_proxy"], timeout=15.0, check=False)
          ...
          break
      except Exception as exc:
          p_err = str(exc)
          if _attempt == 0 and ("timed out" in p_err.lower() or is_connection_lost(p_err)):
              time.sleep(1.0)
              continue  # <--- BẪY: Chỉ sleep 1s rồi gọi lại y hệt, KHÔNG reset pipe transport!
          break

  if is_connection_lost(p_err) or "timed out" in p_err.lower():
      raise ConsumerPreflightError(f"device is offline or ADB/USB disconnected for {serial}: {p_err}")
  ```
- Khi attempt 0 bị timeout do kẹt transport, việc sleep 1s không giải phóng được pipe socket `/dev/android_adb`. Attempt 1 tiếp tục timeout $\rightarrow$ ném `ConsumerPreflightError` $\rightarrow$ runner đánh dấu `blocked-proxy-vpn` và loại bỏ máy khỏi toàn bộ phiên chạy ngay từ giây thứ 30.
- Trong khi đó, nhánh tự động `adb.reconnect()` lại nằm ở Bước 2 phía dưới (sau khi đã đọc xong proxy), khiến máy bị văng từ Bước 1 vĩnh viễn không được cứu.

## 3. Bản Vá Tự Cứu Hộ Tại Chỗ (In-Flight Transport Self-Healing)
Ngay tại vòng lặp retry của `require_proxy_connected`, nếu attempt 0 dính timeout hoặc connection lost:
```python
if _attempt == 0 and ("timed out" in p_err.lower() or is_connection_lost(p_err)):
    try:
        if hasattr(adb, "reconnect"):
            adb.reconnect()
        elif hasattr(adb, "_reconnect_device"):
            adb._reconnect_device()
    except Exception:
        pass
    time.sleep(1.0)
    continue
```
- Khi gọi `adb -s <serial> reconnect`, gói `A_SYNC` được bắn trực tiếp xuống daemon `adbd`, giải phóng socket bị nghẽn đệm. Attempt 1 đọc lại lệnh `settings get global http_proxy` thành công 100%, cứu sống máy ngay trong ca mà không cần human/coordinator can thiệp sau ca.

## 4. Kỷ Luật Vận Hành: Chống Cứu Hộ Thụ Động Sau Khi Đã Mất Lượt
1. **Quan niệm "Cứu hộ sau ca" là thất bại:** Máy online sau ca nuôi không bù lại được lượt nuôi đã mất của tài khoản. Mọi cơ chế tự phục hồi phải là **In-Flight (ngay khi gặp sự cố trong ca)** hoặc **Pre-Session (trước khi phát lệnh ca)**.
2. **Pre-Session Health Gate:** Trước khi `tiktok_runner.py` phát lệnh chạy phiên, nếu phát hiện có máy đang ở trạng thái `offline` hoặc kẹt shell, phải chạy fast soft-recovery / reconnect O(1) trong 10-15s trước khi đổ tải.
3. **Fail-Closed vs Self-Healing:** Fail-closed là để bảo vệ IP farm (chống leak direct IP FPT). Nhưng trước khi kết luận fail-closed và bỏ rơi thiết bị, hệ thống BẮT BUỘC phải thực hiện tối thiểu 1 lần active transport recovery (`adb reconnect`).
