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

## 3. Bẫy Lệch State Cũ Sau Chuyển Đổi 1-Based (Stale State Desync)
- **Triệu chứng:** Ca chạy gần nhất gãy, ngày mãn hạn đúng nấc phạt của số ca 0 lượt liên tiếp (ví dụ 2 ca liên tiếp phạt 3 ngày đến 11-07), nhưng banner trạng thái lại ghi `Streak lỗi: 1`.
- **Nguyên nhân gốc rễ:** File JSON state (`follow_state_{machine}_row_{row}.json`) được ghi trước thời điểm commit chuẩn hóa 1-based (04/11). Thời điểm đó code lưu theo chuẩn 0-based: `czd = 2` nhưng gán `fail_streak: 1`. Khi Dashboard đọc trường tĩnh `fail_streak` từ JSON cũ thì hiển thị số cũ.
- **Xử lý triệt để:**
  1. **Reconcile state:** Quét các file state trong `D:/Taadaa/tiktok-follow/runs/state/`, nếu `consecutive_zero_drops > fail_streak` thì đồng bộ `fail_streak = min(10, czd)`.
  2. **Phòng vệ Helper:** Trong `follow_health_helper.py` hoặc parser đọc state, tính `fail_streak = max(raw_streak, min(10, czd))` để tự động tương thích ngược không bao giờ bị tụt streak trên UI.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
