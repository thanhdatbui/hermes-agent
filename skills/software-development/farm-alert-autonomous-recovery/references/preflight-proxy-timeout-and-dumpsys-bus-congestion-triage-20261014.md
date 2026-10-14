# Preflight Proxy Timeout & Dumpsys Bus Congestion Triage (2026-10-14)

## Bối cảnh & Hiện tượng
Trong các phiên chạy TikTok Feed Session (nuôi acc) với quy mô 80–160 máy (25–30 workers đồng thời):
1. Hàng loạt máy (30–60 máy) bị đánh dấu `blocked-proxy-vpn` hoặc `device offline` ngay từ bước khởi động.
2. 10–20 máy khác bị lỗi `prepare-tiktok failed to focus TikTok after launch`, một số máy bị kẹt bước chuẩn bị kéo dài tới 30–60 phút.

## Nguyên nhân gốc rễ (Root Cause)

### 1. Hardcoded Timeout 3.0s cho ADB Settings Query (`vpn_preflight.py`)
- Lệnh: `adb.shell(["settings", "get", "global", "http_proxy"], timeout=3.0)`
- Khi farm chạy tải cao (nhiều worker đồng thời hoặc kết nối qua LAN tới cụm Admin remote `192.168.110.119:5037`), hàng đợi lệnh của ADB daemon bị trễ > 3.0 giây.
- Khối try/except bắt exception `timed out` và gom vào `ConsumerPreflightError("device is offline or ADB/USB disconnected")` mà KHÔNG có retry.
- **Hậu quả:** Máy và proxy hoàn toàn bình thường nhưng bị script hủy phiên oan uổng.

### 2. Dumpsys Thô 5MB Gây Nghẽn Bus ADB Daemon (`observe.py`)
- Hàm `get_focused_activity` liệt kê candidates:
  ```python
  candidates = [
      ["dumpsys", "window", "displays"],
      ["dumpsys", "window"],                # 3MB unbuffered text qua USB!
      ["dumpsys", "activity", "activities"],# 2MB unbuffered text qua USB!
  ]
  ```
- Mỗi lần kiểm tra focus, nếu `displays` không khớp, lệnh `dumpsys window` và `dumpsys activity activities` xuất hàng megabyte text thô qua USB.
- Với 25–30 worker chạy cùng lúc, hàng gigabyte text đổ dồn làm nghẽn bus USB và làm ADB server daemon tê liệt (latency tăng vọt, các lệnh khác bị timeout dây chuyền).

## Quy tắc & Bản vá chuẩn (Standard Fix Pattern)

1. **ADB Preflight Timeout & Retry:**
   - Mọi lệnh ADB kiểm tra trạng thái preflight (proxy, battery, wifi) trên farm đông máy BẮT BUỘC timeout tối thiểu **8.0s**.
   - BẮT BUỘC bọc vòng lặp retry tối thiểu **2 lần** với backoff `1.0s` khi gặp timeout hoặc connection lost trước khi quyết định fail-closed:
     ```python
     for _attempt in range(2):
         try:
             p_res = adb.shell(["settings", "get", "global", "http_proxy"], timeout=8.0, check=False)
             ...
             break
         except Exception as exc:
             p_err = str(exc)
             if _attempt == 0 and ("timed out" in p_err.lower() or is_connection_lost(p_err)):
                 time.sleep(1.0)
                 continue
             break
     ```

2. **CẤM Dumpsys Thô Không Lọc:**
   - CẤM TUYỆT ĐỐI gọi `dumpsys window` hoặc `dumpsys activity` không lọc qua USB.
   - BẮT BUỘC lọc trực tiếp trên shell của thiết bị Android:
     ```python
     ["sh", "-c", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|mFocusedWindow|mTopFullscreenOpaque'"]
     ```
   - Chỉ truyền đúng 1–2 dòng text đã lọc qua USB, giảm tải 99.9% lưu lượng cho ADB server daemon.
