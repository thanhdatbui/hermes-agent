# Avatar Watchdog Failure Accumulation & ADB Transport Stall Triage (2026-10-08)

## 1. Hiện tượng & Triệu chứng
Trong báo cáo tổng kết ca tối từ watchdog `post_evening_avatar_watchdog.py`:
- Báo cáo liệt kê danh sách lỗi tích lũy:
  ```text
  ❌ [ACCOUNT_SWITCHER_FAILED] (17 máy): 2, 16, 18, 20, 25, 26, 31, 34, 39, 41... (+7)
  ❌ [AVATAR_EDIT_OPEN_FAILED] (6 máy): 4, 28, 44, 51, 63, 69
  ❌ [DEVICE_OFFLINE] (1 máy): 30
  ❌ [OPEN_TIKTOK_FAILED] (1 máy): 221
  ❌ [PREFLIGHT_VPN_BLOCKED] (29 máy): 7, 9, 10, 77, 79...
  ```
- Tuy nhiên khi kiểm tra thực tế:
  - Máy 16, 34 thực tế đã hoàn thành `DONE` 6/8 Tik; 2 Tik còn lại chỉ đang `PENDING` do chờ bốc ảnh mới (`MISMATCH_GOC`), không hề kẹt switcher.
  - Máy 2 thực tế đã `DONE` 5/8 Tik.

---

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Bẫy tích lũy trạng thái trong Watchdog State (`session_failed_by_reason`):**
   - Trong `post_evening_avatar_state.json`, từ điển `session_failed_by_reason` ghi nhận máy ngay khi máy gặp lỗi ở lần chạy đầu tiên (Attempt 1).
   - Khi máy được tự động retry thành công ở Attempt 2 hoặc 3, hoặc đã hoàn tất qua batch trước đó, logic watchdog không tự động loại bỏ máy khỏi `session_failed_by_reason`.
   - Khi đồng hồ điểm hết khung giờ (sau 23:30), hàm `build_summary_report` lôi toàn bộ máy trong `session_failed_by_reason` ra in thành danh sách lỗi ca tối, gây ra **False Alarm tích lũy** khiến Operator tưởng rằng cả 17 máy đều đang chết switcher.

2. **Treo socket ADB đơn lẻ làm `inspect_machine.py` bị timeout 30s:**
   - Khi chạy `python D:/Taadaa/tools/inspect_machine.py 4`, lệnh `adb shell dumpsys` bị treo socket dù máy vẫn cắm sạc và hiển thị `device` trong `adb devices`.
   - Nguyên nhân do transport stream của daemon ADB trên Windows bị nghẽn buffer.

---

## 3. Quy trình Triage O(1) chuẩn hóa
1. **Đối soát Ground Truth qua SQLite `avatar_replace_queue`:**
   - CẤM phán đoán tình trạng fleet chỉ dựa vào text tổng kết của watchdog.
   - BẮT BUỘC query trực tiếp:
     ```python
     SELECT tik, may, username, status, last_error FROM avatar_replace_queue WHERE may = ?;
     ```
   - Nếu hầu hết các Tik của máy đã `DONE`, đây là False Alarm lịch sử từ Attempt 1.
2. **Cứu nhanh socket ADB bị treo bằng `reconnect` nguyên tử:**
   - Khi lệnh inspect máy bị timeout > 10s: CẤM kill-server toàn bộ fleet (`taskkill -F -IM adb.exe`).
   - Chạy ngay:
     ```bash
     adb -s <serial> reconnect
     ```
   - Socket hồi sinh ngay lập tức trong < 1s và ping `adb -s <serial> shell echo 1` trả về `1`.
3. **Phân biệt L3 BLOCKED vật lý qua Windows PnP Topology:**
   - Với máy báo `DEVICE_OFFLINE` hoặc `device not found`, bắt buộc kiểm tra PnP:
     ```powershell
     Get-PnpDevice | Where-Object { $_.InstanceId -like "*<serial>*" } | Select-Object FriendlyName, Status, Present, Problem
     ```
   - Nếu `Present: False` hoặc `Problem: CM_PROB_PHANTOM`: 100% lỗi cáp/sập nguồn phần cứng tại rack (ví dụ M30 trên Kibe, M221 trên Admin). Dừng mọi retry và chuyển L3 BLOCKED.
