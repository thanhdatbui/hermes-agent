# Watchdog Cohort Accounting Invariants across Session Hooks

## 1. Bản chất kiến trúc đa tầng (Multi-Stage Lifecycle)
Trong một phiên nuôi TikTok (`multi-machine-feed-session`), vòng đời của mỗi máy trải qua các giai đoạn:
1. **Reservation & Preflight:** Kiểm tra `device_lock`, router proxy/VPN, pin, kết nối. Nếu máy dính lock của tiến trình khác (`skipped-device-locked`) hoặc mất kết nối (`blocked-proxy-vpn`), máy sẽ dừng ngay tại vòng ngoài mà không bao giờ spawn worker tiến trình con.
2. **Feed Session (Lướt Feed):** Chạy `prepare_tiktok` -> `feed_session_smoke`.
3. **Follow Hook:** Chạy sau bước lướt Feed. Tạo ra file artifact `follow_result.json`.
4. **Upload Hook (Phiên 3):** Chạy ở phiên cuối ngày. Tạo ra file artifact `upload_result.json`.

## 2. Nguyên nhân lệch số liệu Follow / Upload trong Watchdog
Khi `feed_session_watchdog.py` tổng kết phiên:
- `all_machines` gom tất cả các máy có `summary.txt` (cả success lẫn fail từ mọi bước, ví dụ 79 máy: 58 success, 21 fail).
- Tuy nhiên, chỉ những máy vào tới worker con mới chạy hook Follow và ghi `follow_result.json` (ở đây 58 máy feed success + M14 = 59 máy).
- 20 máy còn lại (17 máy kẹt lock, 3 máy lỗi proxy/VPN) bị dừng từ vòng reservation nên hoàn toàn không có `follow_result.json`.
- **Lỗ hổng parser cũ:**
  ```python
  if m in all_follows:
      ...
  else:
      # Chỉ tính lỗi follow nếu máy lướt Feed thành công nhưng follow hook không chạy được
      if all_machines[m].get("status") == "success":
          fl_error.append(m)
      # NẾU status != "success" -> BỎ QUA HOÀN TOÀN -> MÁY BIẾN MẤT KHỎI BÁO CÁO!
  ```
  Dẫn đến tổng Follow chỉ hiển thị 59 máy, trong khi tổng máy xử lý là 79 máy.

## 3. Quy tắc bắt buộc khi thiết kế / sửa script Watchdog (Cohort Accounting Invariant)
1. **Bảo toàn tổng số máy (Conservation of Cohort Count):**
   Mỗi section (Feed, Follow, Upload) BẮT BUỘC phải có tổng số máy bằng chính xác `total_machines`:
   `len(success) + len(released) + len(error) + len(skipped) == total_machines`
2. **Xử lý fail-closed cho máy không chạy hook:**
   Nếu máy không có `follow_result.json`:
   - Nếu Feed thành công: tính vào `fl_error` (lỗi script hook không chạy).
   - Nếu Feed thất bại / skip từ đầu (do kẹt lock, lỗi mạng, crash preflight): tính vào `fl_skipped` (bỏ qua follow vì feed chưa hoàn tất), đảm bảo tổng số máy bỏ qua phản ánh đúng toàn bộ các máy không đi follow trong phiên.
