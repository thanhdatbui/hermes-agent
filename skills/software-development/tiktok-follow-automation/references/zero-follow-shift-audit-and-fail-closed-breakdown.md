# Đối soát & Phân rã Ca Nuôi Acc Có 0 Lượt Follow (Zero-Follow Shift Audit)

## 1. Bản chất hiện tượng
Khi người dùng thắc mắc *"Ca trưa/ca nào đó không chạy follow à?"* hoặc báo cáo ghi nhận `Follow: 0 lượt`:
**Tuyệt đối không kết luận vội là script bị crash, kẹt hay bỏ quên ca.** 
Tiến trình nuôi acc (`multi_machine_feed_session.py`) thường vẫn chạy 100% đầy đủ cả 2 phiên (hàng ngàn lượt lướt feed, hàng trăm tim), nhưng hệ thống bảo vệ đa tầng (Fail-Closed) đã kích hoạt đồng loạt khiến số lượt follow thực tế = 0.

## 2. Bảng 6 nguyên nhân Fail-Closed khiến Follow = 0
1. **🌿 Dưỡng sinh ngẫu nhiên (`organic-rest-day-pure-feed` ~33-40%):**
   - Thuật toán băm `MD5(date : machine : row) % 3 == 0` cố định trong ngày cho từng nick.
   - Nick rơi vào ngày dưỡng sinh chỉ lướt feed (Pure Feed), tự động bỏ qua 0 follow và 0 upload.
2. **⚡ Cầu dao IP 48h ngắt bảo vệ (`IP_CIRCUIT_BREAKER_TRIPPED` / `CIRCUIT_BREAKER_SKIPPED`):**
   - Nếu ở ca trước (ví dụ Ca 1 sáng) có nick trên cùng proxy dính `FOLLOW_FAILED`, IP đó bị cách ly 48 giờ.
   - Các ca sau (Ca 2 trưa, Ca 3 chiều) cùng dải proxy sẽ tự động skip follow trước cửa app để cứu nick, tránh chết dắt dây.
3. **⏳ Nick đang trong thời gian Cooldown (`follow-released-daily-cooldown`):**
   - Nick từng dính nhả follow ở các đợt chạy trước đang chịu án phạt cách ly 3–7 ngày (`cooldown_until_date`).
4. **🔴 Nick non chưa đủ điều kiện (`under-6-videos-follow-disabled`):**
   - Nick đăng dưới 6 video (rất phổ biến ở cụm Admin hoặc dàn nick mới tạo) bị khóa cứng tính năng follow theo policy an toàn farm.
5. **🎯 Anchor trống / Hết target (`zero-following-skip-v2` / `status: OK, followed_count: 0`):**
   - Máy kiểm tra danh sách target của anchor thấy 0 follower / 0 following hoặc bề mặt list rỗng -> tự động skip an toàn không spam.
6. **🛑 Bị TikTok siết nhả tại trận (`FOLLOW_FAILED: anchor @... bị nhả sau vuốt`):**
   - Vừa tap follow lượt đầu tiên thì TikTok nhả ngay lập tức -> script dừng phiên khẩn cấp ngay tại chỗ (chốt 0 lượt) để bảo vệ tài khoản.

## 3. Quy trình điều tra hiện trường chuẩn O(1) (Chống quét đĩa diện rộng)
- **CẤM TUYỆT ĐỐI:** Dùng `os.walk`, `glob(recursive=True)`, `find`, `grep -rn` quét trên `D:/Taadaa/runtime` hoặc `D:/Taadaa/tiktok-follow` (vi phạm Invariant và kích hoạt `GUARD_DANGEROUS_ROOT`).
- **Bước 1: Tra cứu CSDL tập trung O(1):**
  ```python
  import sqlite3
  conn = sqlite3.connect(r'D:/Taadaa/data/tiktok_tracker.db')
  cur = conn.cursor()
  cur.execute("SELECT * FROM session_action_stats WHERE target_date=? AND session_key LIKE ?", (today, f"%{ca_name}%"))
  print(cur.fetchall())
  ```
- **Bước 2: Phân tích kết quả phiên qua parser chính thống:**
  Dùng trực tiếp hàm `parse_run_all(run_path)` từ `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`:
  ```python
  import sys
  sys.path.insert(0, r'C:/Users/Kibe/AppData/Local/hermes/scripts')
  import feed_session_watchdog as fsw
  # Trả về bộ 3 dict: (feed_dict, follow_dict, upload_dict)
  d1, d2, d3 = fsw.parse_run_all(r'D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-<R>-<HHMMSS>/<RUN_ID>')
  ```
- **Bước 3: Tổng hợp phân rã định lượng:**
  Phân loại từng máy trong `d2` theo 6 nhóm nguyên nhân ở Mục 2 để báo cáo minh bạch cho User.
