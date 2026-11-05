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

## 4. Triage Nghịch Lý: "🔴 Đang bị nhả (Cooldown) • Streak lỗi: 0" (Ca Ăn Nhả Đuôi)
- **Hiện tượng:** Trên UI Sổ Bệnh Án, nick hiển thị cờ đỏ `🔴 Đang bị nhả (Cooldown) • Streak lỗi: 0 • Mãn hạn: YYYY-MM-DD`. Operator thắc mắc: *"Đang bị nhả sao lại Streak lỗi 0?"*.
- **Nguyên nhân cốt lõi:**
  * Nick chạy ca gần nhất đã follow thành công $\ge 1$ người (`used > 0`, ví dụ `used = 1` follow được 1 người), sau đó mới bị nhả ở lượt tiếp theo (`last_failed_ceiling = used + 1`).
  * Theo logic bảo vệ (`follow_state.py` line 538): Khi `used > 0`, hệ thống coi đây là **chạm trần an toàn / ăn nhả đuôi**, reset sạch `consecutive_zero_drops = 0` và gán `fail_streak = 0` để tránh phạt oan lũy tiến.
  * Tuy nhiên, vì kết thúc ca bị nhả, bot vẫn kích hoạt `set_follow_failed()` để khóa cooldown dưỡng sinh 24h (`cooldown_until_date = ngày mai`).
  * Dashboard đọc `follow_failed = True` và `fail_streak = 0` nên render nguyên văn: `🔴 Đang bị nhả (Cooldown) • Streak lỗi: 0`.
- **Kỷ luật giải trình khi User đối soát:**
  1. Trích xuất ngay số lượt follow thành công trong ca (`budget_used` hoặc dòng đầu tiên trong bảng UID con).
  2. Nêu rõ: Ca này là **Ăn nhả đuôi (`used > 0`)**, không phải **Nhả trắng 0 lượt (`used == 0`)**.
  3. Cooldown 24h là thời gian làm nguội thiết bị / xả cache, không phải án phạt streak. Streak lỗi chỉ tính khi bị nhả trắng 0 lượt liên tiếp.

## 5. Kỷ Luật Đánh Giá A/B Test Max Volume & Bản Chất Trần Thời Gian Follow Hook
- **Tránh nhầm lẫn báo cáo:** `Tik 4`, `Tik 8` trong báo cáo Telegram là **slot workbook** (tài khoản con), KHÔNG PHẢI số thứ tự máy (`M4`, `M8`). Máy lẻ/chẵn phân biệt bằng tiền tố `M{N}`.
- **Tiêu chuẩn vàng đánh giá A/B Test (Máy Chẵn Bỏ Hồi Phục vs Máy Lẻ Có Hồi Phục):**
  * CẤM đánh giá hiệu quả qua số ca 0 lượt nhả phát đầu (`used == 0`), vì cả 2 nhóm khi vừa bấm anchor đầu tiên bị nhả đều bắt buộc phải kích hoạt phanh dừng session (`FOLLOW_FAILED: anchor bị nhả sau vuốt`) để cứu nick.
  * **Tiêu chuẩn vàng thực tế:** Theo dõi dọc tỷ lệ tích lũy phạt nặng (`fail_streak >= 3` - cooldown 7-15 ngày) và tỷ lệ giữ trần ở các chu kỳ 72h sau khi nick ăn kịch trần (15-20 lượt).
  * **Thực nghiệm chứng minh:** Sau 72h nghỉ, TikTok không phạt thù vặt với nick đủ trust. Nhóm B (Chẵn - Thả trần) có tỷ lệ `streak >= 3` thấp hơn Nhóm A (16.3% vs 18.9%), các nick nòng cốt (như M2 Row 1) ăn 17 -> 17 -> 18 lượt sạch qua 3 cữ liên tiếp mà `fail_streak = 0`.
- **Vì sao Quota 18-20 lượt nhưng Phiên 1 thường dừng ở 12-14 lượt?**
  * **Trần thời gian cứng 20 phút (`DEFAULT_FOLLOW_HOOK_TIMEOUT_SECONDS = 1200.0`):** Do quy trình mô phỏng người thật (xem clip anchor 12-16s, xem clip ứng viên 12-15s, Path B reload + đệm settle 3.5s, jitter delay 3-8s) ngốn 60-80s/lượt. Trong 1200s, bot chỉ kịp ăn tối đa 12-16 lượt trước khi chạm timeout thu quân nhường máy chạy upload video.
  * **Nhả đuôi ở Phiên 2:** TikTok tính rate limit trượt trong 24h. Phiên 1 đã nuốt 12-16 lượt thì sang Phiên 2 (cách 1.5-2h) tổng ngày chạm trần sinh lý (15-18 lượt), TikTok kích hoạt nhả follow $\rightarrow$ Bot dừng an toàn ở lượt thứ 1-2.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
