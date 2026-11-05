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

## 4. Cơ Chế A/B Testing Nhóm Máy Chẵn (Max Volume) vs Máy Lẻ (Hồi Phục)
Hệ thống chia cụm máy theo chẵn / lẻ để tối ưu cân bằng tải cổng proxy 4G chung và thử nghiệm sản lượng:
- **Nhóm B (Máy Chẵn: `machine % 2 == 0` - Max Volume):**
  * Bỏ hoàn toàn cơ chế Hồi phục 1 & 2 (`_probation_budget`).
  * Cấp thẳng Full Trần `cap = 20`, dao động `[cap - 2, cap] = [18, 20]`, `mode = "full"`.
  * **Chạm trần an toàn (`used > 0`):** Ngắt phiên ngay lập tức, bảo toàn $N - 1$ lượt sạch. Kỳ sau tới cữ vẫn được cấp Full Quota Max Volume, không bị giáng cấp về Hồi phục.
  * **Chết Anchor phát đầu (`used == 0`):** Fail-closed lập tức (`FOLLOW_FAILED`), tăng streak và đưa vào Cooldown để chống ăn gậy Action Block nặng.
- **Nhóm A (Máy Lẻ: `machine % 2 == 1` - Bảo Thủ):**
  * Bắt buộc đi qua thang Hồi phục (Hồi phục 1: 3–4 lượt, Hồi phục 2: 5–6 lượt).
  * Cần tích lũy đủ 2 ngày sạch (`probation_clean_days = 2`) mới được tốt nghiệp về Full Quota.
- **Cách đối soát thực tế:**
  * Soi `last_budget_decision` trong `follow_state_{machine}_row_{row}.json`: Máy chẵn luôn nhận `budget: 18..20, mode: "full"` (dù `probation_clean_days = 0`), máy lẻ nhận `mode: "probation_tier1"` hoặc `"probation_tier2"`.

## 5. Phương Pháp Luận Đánh Giá Hiệu Quả A/B Test (Tránh Bẫy Đánh Giá Nhả Phát Đầu)
- **Bẫy tư duy sai lầm:** Đánh giá hiệu quả bằng việc so sánh tỷ lệ phiên dừng khi nhả phát đầu (`used == 0`). 
  * *Bản chất:* Khi TikTok siết anchor hoặc cổng proxy dính cờ đen tạm thời, **bất kể máy chẵn hay máy lẻ đều bắt buộc phải kích hoạt phanh dừng phiên ngay (`used == 0`)** để cứu nick khỏi Action Block. Không thể lấy số ca 0 lượt để bảo nhóm Max Volume hỏng.
- **Tiêu chuẩn vàng đánh giá hiệu quả (Multi-cycle Fate):**
  1. **Tỷ lệ dính Cooldown sâu (`fail_streak >= 3` nghỉ 7–15 ngày):** Thả trần có làm nick bị dồn streak liên tục không? (Thực tế kiểm chứng farm: Nhóm Chẵn chỉ 16.3% dính streak ≥ 3, thấp hơn Nhóm Lẻ 18.9%).
  2. **Khả năng lặp lại sản lượng sau 72h (3 ngày):** Khi nick ăn 15–20 follow ở vòng trước, cữ 3 ngày sau có tiếp tục nuốt 15–20 follow hay bị TikTok "ghi sổ thù vặt"? Thực tế các nick nòng cốt (`M2`, `M12`, `M48`) sau khi ăn trọn 17–19 follow vẫn giữ nguyên `fail_streak = 0` và tiếp tục ăn đều đặn 17–18 follow qua 3 cữ liên tiếp mà không bị phạt.

## 6. Bản Chất Trần Phiên 20 vs Sản Lượng Ca 17–19 Lượt (Rolling 24h Window)
- **Hiện tượng:** Mỗi phiên cấp trần 20 lượt (lý thuyết 2 phiên/ca = 40 lượt), nhưng tổng thực tế 2 phiên chỉ thu về 17–19 lượt.
- **Bản chất kỹ thuật:**
  * Thuật toán TikTok kiểm soát trần follow theo cửa sổ trượt 24h (Rolling 24h Window), ngưỡng chịu tải an toàn của nick farm hiện tại là 15–20 follow/ngày.
  * **Phiên 1:** Nick sung sức, nuốt trọn 14–16 lượt sạch.
  * **Phiên 2 (cách 1.5–2h):** TikTok cộng dồn sản lượng Phiên 1. Khi bot bấm thêm 1–2 lượt (chạm mốc 17–19 cả ngày), TikTok kích hoạt rào chắn tự vệ khiến follow bị nhả ngược sau vuốt 3.5s.
  * **Script ngắt an toàn:** Nhận diện nhả ngược, script lập tức dừng phiên bảo toàn số follow đã ăn.
  * Con số 17–19 là giới hạn sinh lý an toàn của TikTok trong ngày, không phải do script bóp trần.

## 7. Kỷ Luật Đọc Báo Cáo: Phân Biệt `M<num>` vs `Tik <num>`
- **Cú pháp:** `- M<machine> Tik <slot> (@username) : script N lượt`
  * Dòng `- M5 Tik 8 (@davidsoarek17) : script 2 lượt` $\rightarrow$ Đây là **Máy 5 (Máy Lẻ)** chạy slot **Tik 8**, tuyệt đối không đọc nhầm thành Máy 8.
  * Nhìn tiền tố `M<num>` để xác định số máy chẵn/lẻ, không nhìn số sau chữ `Tik`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
