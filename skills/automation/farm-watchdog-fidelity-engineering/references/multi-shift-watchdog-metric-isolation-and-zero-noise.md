# Multi-Shift Watchdog Metric Isolation & Zero-Noise Invariant

## 1. Bẫy Lũy Kế Ngày vs Kết Quả Ca (Shift Reporting Drift)
Trong các watchdog chạy nhiều ca trong ngày (sáng, trưa, chiều, tối như `post_evening_gpm_login_watchdog.py`), state file thường lưu các biến tổng ngày:
- `total_success`
- `total_fail`
- `failed_details`

### Điểm mù nguy hiểm (False-Alarm Storm):
- Ca sáng chạy bị lỗi 3 tài khoản (`total_fail = 3`, `failed_details = [acc1, acc2, acc3]`).
- Ca tối bước vào khung giờ nhưng toàn bộ máy bận hoặc tài khoản đang hạ nhiệt cooldown (`candidates = 0` hoặc không đủ điều kiện chạy). Ca tối thực tế chạy **0 lượt** (`shift_success = 0, shift_fail = 0`).
- Khi hết giờ ca (timeout/is_late), watchdog kiểm tra:
  ```python
  if total_success > 0 or total_fail > 0: # BẪY: total_fail = 3 từ ca sáng!
      print(_format_summary_report(total_success, total_fail, shift_label="TỐI"))
  ```
- Kết quả: Watchdog in ra:
  `[LOGIN GPM TỐI - TỔNG KẾT]`
  `• Kết quả ca: ✓ 0 | ✗ 3 | max_proxy 0/cổng | Hoàn tất ca tối`
  `⚠️ Chi tiết 3 acc thất bại: acc1, acc2, acc3...`
- Hậu quả: Người vận hành tưởng rằng hệ thống vừa lôi 3 acc ra chạy tiếp và lại làm tạch tiếp, gây hoang mang và tranh cãi không đáng có.

---

## 2. Quy Tắc Thiết Kế Chuẩn (Contract Invariants)

1. **Phân định rõ 2 phạm vi biến đếm:**
   - **Phạm vi Ca (`shift_success`, `shift_fail`, `shift_failed_details`):** Luôn khởi tạo bằng 0 / rỗng ở đầu hàm `main()` của mỗi lần chạy hoặc mỗi tick của ca. Chỉ tăng khi worker trong ca đó thực sự hoàn tất.
   - **Phạm vi Ngày (`total_success`, `total_fail`, `all_day_failed_details`):** Đọc từ state file để tích lũy dồn cho toàn bộ 24h.

2. **Template Báo Cáo Tách Bạch:**
   - Dòng tiêu đề và kết quả ca BẮT BUỘC dùng biến của ca:
     `• Kết quả ca: ✓ {shift_success} | ✗ {shift_fail} | max_proxy {max_p}/cổng`
   - Chỉ in dòng lũy kế ngày ở dòng phụ phía dưới nếu cần:
     `• Lũy kế cả ngày: ✓ {total_success} | ✗ {total_fail}`
   - Danh sách `failed_details` hiển thị trong báo cáo ca **CHỈ ĐƯỢC CHỨA** các tài khoản vừa thất bại trong chính ca đó (`shift_failed_details`), tuyệt đối cấm bê danh sách lỗi từ ca trước sang.

3. **Nguyên Tắc Watchdog Im Lặng (Zero-Noise on Empty Shifts):**
   - Nếu trong suốt ca không có candidate nào chạy (`shift_success == 0 and shift_fail == 0`) và không có candidate nào bị kẹt chờ máy rảnh (`skipped_busy == 0`):
     $\rightarrow$ Watchdog cập nhật `finished_shifts`, ghi state và **KẾT THÚC TRONG IM LẶNG**.
     $\rightarrow$ Tuyệt đối không gửi tin nhắn Telegram hay stdout rác khi không có biến động mới trong ca.
