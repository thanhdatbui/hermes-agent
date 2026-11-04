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
- Trên Dashboard / Sổ Bệnh Án (`follow_detail_component.py`): `Streak lỗi: ${data.fail_streak}` hiển thị trùng khớp 1:1 với số chấm đỏ trên ma trận ca chạy.

## 3. Quy Trình Đối Soát & Hiệu Chỉnh Chuẩn (SOP)
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
