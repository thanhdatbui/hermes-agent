# Mechanical Remediation vs Discipline Promises & Dashboard Stale Carryover Invariant (2026-10-31)

## 1. Bối Cảnh Sự Cố & Lỗi Hành Vi Của Agent
* **Sự cố thực tế:** User phát hiện dashboard báo:
  `⚡ Tiến độ hôm nay: Bot +0 lượt (Web 📈 Tổng tăng: +8)`
  `@mautuoi08: ĐÃ FOLLOW: 9 +4 | 🔗 Nội bộ: +0`
* **Lỗi ứng xử của Agent (Discipline Theater):**
  Khi lệnh phân tích SQLite chạy nặng bị ngắt tín hiệu (`Operation interrupted`), agent im lặng turn đó. Khi user chất vấn ("Lí do treo k trả lời?"), agent đưa ra văn mẫu xin lỗi và hứa hẹn: *"Kỷ luật khắc phục: Mọi truy vấn kiểm tra SQLite về sau bắt buộc..."*.
* **User Correction Invariant:** *"Sửa cơ học chứ đéo phải kỉ luật hệ thống lồn gì cả"*.
  - **CẤM TUYỆT ĐỐI** đưa ra các lời hứa suông, văn mẫu "xin rút kinh nghiệm" hay "kỷ luật lần sau".
  - **BẮT BUỘC:** Mọi lỗi hệ thống/code phải được chuyển hóa thành **VÁ CƠ HỌC (Mechanical Fix)**: vá code, sửa SQL predicate, bổ sung unit test chống hồi quy, và hậu kiểm bằng dữ liệu thật.

---

## 2. Bản Chất Cơ Học Của Lỗi Dashboard Stale Carryover Delta
* **Vị trí lỗi:** `D:/Taadaa/tools/dashboard/queries.py` (hàm `get_farm_data`).
* **Cơ chế gây lỗi:**
  1. Khi sang ngày mới (ví dụ `max_dt = '2026-10-31'`), đợt quét đầu ngày lúc 06:01 mới chỉ quét được một phần farm. Các nick chưa quét trong ngày vẫn giữ snapshot gần nhất từ ngày hôm qua (`2026-10-30 20:46:41`).
  2. CTE `LatestCurr` lấy các nick có snapshot trong vòng 2 ngày lùi (`timestamp >= date(max_dt, '-2 days')`). Do đó các nick ngày hôm qua vẫn nằm trong `LatestCurr`.
  3. CTE `RankedPrev` join theo điều kiện:
     ```sql
     WHERE substr(s.timestamp, 1, 10) < substr(c.timestamp, 1, 10)
     ```
     Với nick chưa quét ngày mới, `c.timestamp` là ngày 30/10. Khi đó `RankedPrev` tìm snapshot ngày 29/10!
  4. Hệ quả:
     $$\Delta_{\text{following}} = \text{following}_{\text{30/10}} - \text{following}_{\text{29/10}}$$
     Dù tài khoản **chưa hề được quét trong ngày 31/10**, delta của ngày 30/10 vẫn bị tính trôi (carry-over) sang ngày mới.
  5. Khi đó:
     - `@mautuoi08`: +4
     - `@hoangchau2070`: +2
     - `@doanxuan01`: +1
     - `@nguyentrang86016`: +1
     $\rightarrow$ Tổng cộng đúng bằng **+8**. Web KPI cộng dồn thành `Web: +8`, trong khi bảng bot `daily_account_actions` của ngày 31/10 lúc 06:01 chưa chạy phiên nào (`Bot: +0`), tạo ra độ lệch ảo 8 lượt follow.

---

## 3. Giải Pháp Cơ Học Đã Triển Khai (O(1) Mechanical Patch)
* **Code fix:** Bổ sung điều kiện kiểm tra ngày của snapshot hiện tại so với `max_dt`. Nếu snapshot của nick thuộc ngày cũ (`ts[:10] < max_dt`), toàn bộ delta trong ngày mới bắt buộc gán bằng 0:
  ```python
  is_stale = bool(ts and max_dt and ts[:10] < max_dt)
  delta_f = 0 if is_stale else ((f_val - prev_f) if prev_f is not None else 0)
  delta_following = 0 if is_stale else ((following_val - prev_following) if prev_following is not None else 0)
  delta_h = 0 if is_stale else ((h_val - prev_h) if prev_h is not None else 0)
  delta_v = 0 if is_stale else ((v_val - prev_v) if prev_v is not None else 0)
  ```
* **Unit Test bắt buộc:** Bổ sung `test_stale_account_delta_zero_on_new_day` trong `tests/test_tiktok_dashboard.py` mô phỏng nick cũ chưa quét ngày mới để bảo vệ không tái diễn.
* **Quy tắc truy vấn SQLite bảng lớn (`snapshots` > 140k dòng):**
  CẤM chạy query có `ROW_NUMBER() OVER (PARTITION BY ...)` trên toàn bảng mà không có filter `timestamp >= date('now', '-2 days')`. Bỏ điều kiện thời gian sẽ gây nghẽn I/O và kích hoạt hard interrupt của agent gateway.
