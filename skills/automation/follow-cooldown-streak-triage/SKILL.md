---
name: follow-cooldown-streak-triage
description: Quy trình đối soát và đồng bộ fail_streak và consecutive_zero_drops cho Follow Runner & Sổ Bệnh Án Dashboard.
---

# Follow Cooldown Streak & Zero-Drop Triage

Sử dụng khi kiểm tra "Sổ Bệnh Án" trên Dashboard hoặc log Follow Runner phát hiện lệch số lần nhả follow liên tiếp (0 lượt) so với `fail_streak` hiển thị trên UI.

## 1. Triệu Chứng Nhận Diện
- Ma trận ca chạy hiển thị nhiều cữ nhả follow (0 lượt) đỏ liên tiếp (ví dụ: 3 ca 0 lượt: `25-10`, `27-10`, `01-11`).
- Banner trạng thái hiển thị `Streak lỗi: 1` hoặc số streak thấp hơn số ca nhả thực tế.

## 2. Chuẩn Hóa Toàn Hệ Thống 1-Based (Đếm Sao Phạt Vậy - Quyết Định Ngày 04/11)
Hệ thống đã chuẩn hóa toàn bộ sang chuẩn **1-based**:
- Số ca 0 lượt liên tiếp (`consecutive_zero_drops = N`) chính là `fail_streak = N`:
  - 1 ca 0 lượt: `fail_streak = 1` (cooldown 24h).
  - 2 ca 0 lượt liên tiếp: `fail_streak = 2` (cooldown 3 ngày).
  - 3 ca 0 lượt liên tiếp: `fail_streak = 3` (cooldown 5 ngày).
  - ≥ 4 ca 0 lượt liên tiếp: `fail_streak = min(10, czd)` (cooldown 15 ngày).
  - Follow thành công / chạm trần an toàn (`used > 0`): `fail_streak = 0`, `consecutive_zero_drops = 0`.
- Trên Dashboard / Sổ Bệnh Án (`D:/Taadaa/tools/dashboard/follow_detail_component.py` thuộc repo `D:/Taadaa/tools`):
  * Dòng trạng thái (`statusHtml` trong hàm `renderFollowDetailModal`):
    `Trạng thái: 🔴 Đang bị nhả (Cooldown) • Streak lỗi: ${data.fail_streak} • Mãn hạn: ${data.cooldown_until_date}`
  * Mapping nấc phạt theo streak 1-based:
    - Streak 1: 1 ngày (24h)
    - Streak 2: 3 ngày
    - Streak 3: 5 ngày
    - Streak ≥ 4: 15 ngày
  * Hiển thị trùng khớp 1:1 với số chấm đỏ trên ma trận ca chạy.
  * Format hiển thị chuẩn (Phương án 1 - viết gọn theo yêu cầu User):
    `Streak lỗi: ${streak} (${days} ngày)`
    - Ví dụ cụ thể: `Streak lỗi: 1 (1 ngày)`, `Streak lỗi: 2 (3 ngày)`, `Streak lỗi: 3 (5 ngày)`, `Streak lỗi: 4 (15 ngày)`.

## 3. Bẫy Lệch State Cũ Chưa Reconcile Sau Di Cư 1-Based (Commit 6277b38 ngày 04/11)
- **Hiện tượng:** Ma trận hiển thị $N$ ca 0 lượt đỏ liên tiếp ($N \ge 2$), hạn cooldown tính đúng nấc thang $N$ ca, nhưng banner vẫn hiện `Streak lỗi: N - 1` (ví dụ: nick `@lu.huyn926` m31_r1 có 2 ca đỏ 31-10 và 04-11, mãn hạn 07-11 phạt 3 ngày, nhưng banner ghi `Streak lỗi: 1`).
- **Nguyên nhân gốc rễ:** State file `runs/state/follow_state_*.json` được ghi từ trước thời điểm nâng cấp 1-based (commit `6277b38` lúc 16:11:29 ngày 04/11). Thời điểm đó, logic cũ gán `fail_streak = czd - 1` tĩnh vào file JSON. Khi code runner đổi sang 1-based, 246 file state cũ trên đĩa chưa được backfill nên Dashboard đọc giá trị cũ.
- **Giải pháp xử lý kép (Defense-in-depth):**
  1. **Tầng Dashboard Parser (`follow_health_helper.py` & `queries.py`):** Bắt buộc bọc cơ chế phòng vệ tự động khi đọc state:
     ```python
     czd = _to_int(d.get("consecutive_zero_drops")) or 0
     raw_streak = _to_int(d.get("fail_streak")) or 0
     fail_streak = max(raw_streak, min(10, czd)) if czd > 0 else raw_streak
     ```
     Điều này đảm bảo Dashboard luôn hiển thị đúng chuẩn 1-based ngay lập tức mà không phụ thuộc vào tiến độ migrate đĩa.
  2. **Tầng State File Disk (SSOT Migration):** Chạy script đối soát quét đĩa cập nhật `fail_streak = min(10, czd)` cho toàn bộ các file JSON có `czd > 0` và `fail_streak < czd`.

## 4. Quy Trình Đối Soát & Hiệu Chỉnh Chuẩn (SOP)
1. **Trích xuất state file của nick:**
   - Đường dẫn: `D:/Taadaa/tiktok-follow/runs/state/follow_state_{machine}_row_{row}.json`.
   - Đọc các trường: `consecutive_zero_drops`, `fail_streak`, `cooldown_until_date`, `last_failed_date`.

2. **Đối soát số ca 0 lượt thực tế từ SQLite SSOT:**
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('D:/Taadaa/data/tiktok_tracker.db'); c = conn.cursor(); c.execute('SELECT target_date, internal_follows FROM daily_account_actions WHERE username = \"<username>\" ORDER BY target_date DESC'); [print(r) for r in c.fetchall()]; conn.close()"
   ```
   - Đếm số ca 0 lượt liên tiếp gần nhất tính từ ngày gần nhất ngược về trước cho tới ca có `internal_follows > 0`.

3. **Cập nhật đồng bộ state nếu bị lệch:**
   - Nếu số ca 0 lượt liên tiếp = $N$ ($N \ge 1$):
     - `consecutive_zero_drops = N`
     - `fail_streak = N` (chuẩn 1-based đồng bộ: đếm sao phạt vậy)
     - Tính lại ngày mãn hạn cooldown chuẩn theo nấc thang:
       - $N = 1$: +24h (hoặc hết ngày).
       - $N = 2$: +3 ngày.
       - $N = 3$: +5 ngày.
       - $N \ge 4$: +15 ngày.

## 5. Bẫy Lệch Báo Cáo Đối Soát TikTok Web (Triage Lệch Âm / Lệch Dương)
Khi đối soát báo cáo ca chạy (`Đối soát TikTok Web (+X Following thật | Lệch Y so với script báo Z)`):
1. **Lệch dương (`script 0 lượt - web N lượt - lệch (+N)`):**
   - **Triệu chứng:** Web tăng $N$ lượt thật, nhưng dòng đối soát báo script 0 lượt, trong khi khối *Nhả follow* phía dưới ghi nhận đúng `Nhả ở Hồi phục (M: N lượt)`.
   - **Nguyên nhân:** Bug Watchdog `feed_session_watchdog.py` đặt `reset = failed` vô điều kiện. Khi máy đã follow thành công $N$ lượt ($cnt > 0$), đến lượt $N+1$ mới bị TikTok chặn và set cờ `follow_failed = True`, Watchdog đã xóa sạch $N$ lượt thành công về 0 (`m_to_reported = natural_cnt if reset else cnt + natural_cnt`).
   - **Quy chuẩn đối soát:** Chỉ reset về 0 khi nhả liền ở lượt đầu (`cnt == 0`). Với máy `cnt > 0`, các lượt trước đó đã được server TikTok chấp nhận, số thực tế là $N$.

2. **Lệch âm (`script 1 lượt - web 0 lượt - lệch (-1)`):**
   - **Nguyên nhân:** Lượt follow tự nhiên trên Feed overlay video (`swipe_N_after/follow`) không có cơ chế pull-to-refresh reload profile. Nếu tài khoản đã bị server TikTok bóp action (ngay sau đó chạy follow chéo bị nhả liền), server đã âm thầm nuốt (silent drop) lượt tap follow trên feed mà app không có callback lỗi. Không coi đây là lỗi script runner.

3. **Lệch dương do trễ cache Web (`script 0 lượt - web 1 lượt - lệch (+1)`):**
   - **Nguyên nhân:** Độ trễ cập nhật cache CDN / server TikTok từ các phiên follow trước đó (hoặc lượt đăng video mới kích hoạt giải phóng counter trên web profile). Kiểm tra dump UI `artifacts/.../ui.xml` trên máy thật tại thời điểm chạy: nếu UI máy hiển thị trùng khớp với script trước phiên thì khẳng định do Web delay.
