# TikTok Feed Watchdog: Bẫy Gom Fail Trống Slot Phôi Mới & Thiếu Báo Cáo Tỷ Lệ Thả Tim (Case 156)

## 1. Hiện tượng & Phản hồi từ User
- **Triệu chứng:** Kết thúc Ca nuôi (Ca 4 - Row 7), báo cáo tổng kết Telegram báo:
  `• Lướt Feed: Success (19) ... Fail (61): M1, M2, M5, ... M80`
  khiến User thắc mắc: "Sao fail lắm thế? Với lại không báo cáo tỉ lệ thả tim/like?".
- **Thực tế:** Toàn farm chỉ có 35 tài khoản ở Row 7 (các máy còn lại chưa có nick do là phôi mới). Có 19 máy lướt Feed thành công rực rỡ, nhưng báo cáo gom cả 45 máy trống slot vào mục `Fail (61)`. Đồng thời bản tin Telegram thiếu hẳn số liệu thả tim dù runner có like thật.

## 2. Nguyên nhân gốc rễ (Root Cause)

### A. Bẫy Gom Máy Chưa Có Nick Vào Mục Fail (Watchdog False-Alarm)
- Trong `python_runner/core/feed_session_workbook.py`, khi máy chưa có nick trong `taikhoan_run_safe.xlsx`:
  ```python
  reason = f"account row {row_index} is empty (no username) for machine {machine}, skipping"
  ```
- Runner xử lý đúng bằng cách phân loại `config-error` (safe-skip) và ghi nhận vào `summary.txt`.
- Tuy nhiên, trong `feed_session_watchdog.py`:
  ```python
  # Fallback parse batched summary.txt at run root
  failed_m = re.findall(r"machine_(\d+)", c)
  for m_num in set(failed_m):
      if m_num not in res_m:
          res_m[m_num] = {"status": "fail", "reason": "batch-config-error"}
  ...
  succ = sorted([m for m, d in all_machines.items() if d["status"] == "success"], key=num_key)
  fail = sorted([f"M{m}" for m, d in all_machines.items() if d["status"] != "success"], key=num_key)
  ```
  Watchdog đã nhét tất cả các máy có `status != "success"` (bao gồm cả `batch-config-error` do không có nick) vào nhóm `Fail`. Điều này gây hiểu lầm nghiêm trọng rằng 61 máy bị lỗi mạng/kẹt app.

### B. Thiếu Trích Xuất Tỷ Lệ Thả Tim (Like / Heart)
- Code runner `feed-session-smoke` có chạy tính năng thả tim tự nhiên (`swipe_X_after/like: like_video`) và ghi đầy đủ số liệu vào `summary.txt` của từng máy:
  ```json
  "like_counts": {"for-you": 4, "following": 0, "friends": 0},
  "total_swipes_completed": 21
  ```
- Nhưng `feed_session_watchdog.py` chỉ parse `final_status`, `follow_result.json` và `upload_result.json`, hoàn toàn bỏ qua trường `like_counts`. Do đó, bản tin Telegram không có dòng nào về tỷ lệ thả tim.

## 3. Quy tắc Thiết Kế & Khắc Phục Bắt Buộc

1. **Phân loại 3 tầng trạng thái Lướt Feed trong Watchdog:**
   - **Success**: Các máy lướt Feed hoàn tất đạt tiêu chuẩn video.
   - **Bỏ qua (Trống slot / Chưa có nick)**: Các máy có lý do `account row X is empty (no username)`, `workbook does not have valid row` hoặc không nằm trong danh sách accounts được phân bổ cho Row đó. Tuyệt đối **CẤM** gom vào `Fail`.
   - **Fail (Lỗi thực sự)**: Chỉ các máy có nick nhưng gặp lỗi: `manual-needed`, `blocked-proxy-vpn`, kẹt lock timeout, crash script, mất kết nối ADB.
2. **Bắt buộc hiển thị Tỷ lệ Thả Tim (Like):**
   - Định dạng chuẩn trên báo cáo Telegram:
     ```text
     • Lướt Feed:
       + Success (19): 3, 4, 6, 7, ...
       + Fail (16): M1, M2, M5, ...
       + Bỏ qua trống slot (45): M13, M20, ...
       + Thả tim (Like): 86 tim / 687 videos (12.5%)
     ```
   - Trích xuất `like_counts` từ `summary.txt` của từng máy và tính tổng toàn ca.
