# Avatar Queue Stale Drift & Preflight VPN Error Classification (2026-10-08)

## 1. Bản chất sự cố "13 acc / máy" trong `avatar_replace_queue`
### Triệu chứng & Hiện tượng:
- Khi kiểm tra máy 213 (và 256 slot khác trên Admin), bảng `avatar_replace_queue` trả về 13 dòng tài khoản gán cho cùng 1 máy.
- Watchdog và runner liên tục báo lỗi `ACCOUNT_SWITCHER_FAILED` hoặc `FAILED` trên máy 213.

### Nguyên nhân cốt lõi:
- **Lệch Primary Key & Migration không dọn rác:**
  - Bảng `avatar_replace_queue` có Primary Key là `(username, tik, host_id)`.
  - Khi farm Admin được migrate/re-map tài khoản ngày 07/10/2026 theo workbook Excel mới, các tài khoản mới được chèn (`INSERT`) vào queue.
  - Do PK không ràng buộc `may + tik`, các bản ghi cũ của ngày 02/10/2026 không bị ghi đè, dẫn đến tồn tại song song cả acc cũ lẫn acc mới trên cùng một số máy.
  - Khi runner cố gắng chuyển tài khoản (switcher), nó bốc trúng các username cũ (đã bị gỡ khỏi máy) $\to$ văng lỗi `ACCOUNT_SWITCHER_FAILED`.

### Quy trình khắc phục & Phòng ngừa:
1. **Dọn dẹp rác định kỳ đối soát với `farm_account_info`:**
   ```sql
   -- Xóa các bản ghi trong avatar_replace_queue không còn khớp với farm_account_info chuẩn
   DELETE FROM avatar_replace_queue
   WHERE rowid IN (
       SELECT q.rowid
       FROM avatar_replace_queue q
       LEFT JOIN farm_account_info f ON q.may = f.may AND q.tik = f.tik AND q.username = f.username
       WHERE f.username IS NULL
   );
   ```
2. **Đối soát Ground Truth trước khi kết luận lỗi Switcher:**
   - So sánh username trong queue với `farm_account_info` và file Excel `Tik<N>.xlsx`. Nếu username trong queue không có trong Excel, lập tức loại bỏ khỏi hàng đợi.

---

## 2. Bản chất sự cố `PREFLIGHT_VPN_BLOCKED` do mất kết nối ADB / USB
### Hiện tượng:
- Báo cáo watchdog tổng kết ca tối liệt kê 29 máy bị `PREFLIGHT_VPN_BLOCKED` (ví dụ M9, M10, M25, M38, M74, M77, M79...).

### Nguyên nhân cốt lõi:
- Trong `automation_core/preflight.py` (dòng 708):
  - Khi lệnh kiểm tra VPN gửi qua ADB bị lỗi do máy bị offline, mất kết nối USB hoặc rớt socket ADB (`device offline or ADB/USB disconnected`), hàm ném ra `ConsumerPreflightError`.
  - Tại `tiktok_workflow/run_post.py` (dòng 1312–1325), toàn bộ `ConsumerPreflightError` bị gom chung và gán nhãn error_type là `[PREFLIGHT_VPN_BLOCKED]`.
  - **Hậu quả:** Máy bị mất cáp/rớt ADB bị báo nhầm là lỗi mạng VPN.

### Quy tắc Triage O(1):
1. **Kiểm tra `inspect_machine.py <N>` hoặc `adb devices`:**
   - Nếu máy báo `device not found` hoặc `device offline`: Phân loại chính xác là **Lỗi kết nối ADB/USB / Phần cứng**, không phải lỗi cấu hình proxy/VPN.
2. **Phân biệt 2 nhánh lỗi trong log:**
   - `error=device is offline or ADB/USB disconnected` $\to$ Rớt ADB/USB (Cần `adb reconnect` hoặc kiểm tra cáp).
   - `error=required Android VPN is not connected` $\to$ Lỗi VPN thật sự (App chưa kết nối hoặc chưa bật tunnel).
