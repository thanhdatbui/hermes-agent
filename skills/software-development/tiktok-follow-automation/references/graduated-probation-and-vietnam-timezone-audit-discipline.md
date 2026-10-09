# Graduated Probation Ladder & Vietnam Timezone Audit Discipline

Tài liệu chuẩn hóa kiến trúc Bậc thang thử thách (Graduated Probation) và kỷ luật đối soát múi giờ / Parity Lane cho hệ thống TikTok Follow Phone Farm.

---

## 1. Kỷ Luật Đối Soát Múi Giờ (UTC vs GMT+7) & Parity Lane

### A. Pitfall Múi Giờ Dẫn Đến Báo Cáo Sai Lệch (Hallucination)
- **Đặc tính lưu trữ:** Dữ liệu timestamp trong state JSON (`follow_state_*.json`) được lưu dưới dạng ISO 8601 UTC chuẩn (`+00:00` hoặc `Z`), ví dụ: `2026-10-06T23:30:00+00:00`.
- **Lịch trình Farm:** Toàn bộ scheduler, cronjob và parity lane của Farm vận hành theo **Giờ Việt Nam (`Asia/Ho_Chi_Minh`, GMT+7)**.
- **Hậu quả nếu parse chuỗi thô (Naive string slicing `ts[:10]`):**
  - Giờ UTC `2026-10-06T23:30:00` thực tế là **`2026-10-07 06:30:00` sáng giờ Việt Nam**.
  - Nếu cắt chuỗi thô sẽ báo cáo nhầm là "Row 1 chạy vào ngày chẵn 06/10" (vi phạm quy tắc Parity Lane), hoặc nhầm lẫn "1 nick chạy 2 ngày liên tiếp" trong khi thực tế nick chỉ chạy 2 phiên (ca 06:30 và ca 08:30) trong cùng một buổi sáng ngày lẻ (07/10).

### B. Quy Tắc Bắt Buộc Khi Thống Kê & Audit Follow
1. **100% Timestamp phải chuyển đổi sang `Asia/Ho_Chi_Minh` trước khi group by ngày:**
   ```python
   from datetime import datetime
   from zoneinfo import ZoneInfo
   HCMC = ZoneInfo("Asia/Ho_Chi_Minh")
   vn_dt = datetime.fromisoformat(ts).astimezone(HCMC)
   vn_day = vn_dt.strftime("%Y-%m-%d")
   ```
2. **Quy tắc Parity Lane kiểm chứng:**
   - Ngày lẻ VN (01, 03, 05, 07...): Chỉ Row lẻ (Row 1, 3, 5, 7) được phép có timestamp follow.
   - Ngày chẵn VN (02, 04, 06...): Chỉ Row chẵn (Row 2, 4, 6, 8) được phép có timestamp follow.
   - Bất kỳ thống kê nào vi phạm quy tắc này đều bắt nguồn từ lỗi parse múi giờ UTC hoặc rò rỉ scheduling.

---

## 2. Kiến Trúc Bậc Thang Thử Thách (Graduated Probation Ladder)

### A. Bài Học Thực Tế Từ Dữ Liệu Tháng 10/2026
- **Nick khỏe (Không tiền án, >215 ngày, >25 video):** Inbound Trust rất cao, có thể chịu tải **17 - 30+ follows/ngày** an toàn tuyệt đối (0% fail). Tuyệt đối không hạ trần vô lý của nhóm này làm giảm hiệu suất toàn farm.
- **Nick mới ra tù sau Cooldown:**
  - Nhảy vọt quota từ cữ warm-up (3-5 lượt) lên Full Budget (10-20/phiên, 20-30+/ngày) ở ngày thứ 2 là nguyên nhân khiến **25% nick bị TikTok cắn nhả lại ngay lập tức** (chạm ngưỡng quét 12+ follow/ngày của TikTok).
  - Vùng an toàn cao nhất cho nick đang hồi phục là **dưới 10 follows/ngày (cụ thể 7 - 9 lượt)**: tỷ lệ an toàn đạt **88.9%**.

### B. Quy Chuẩn 3 Nấc Thang Thử Thách (`probation_clean_days`)
Thay vì xóa án tích ngay sau 1 ngày warm-up, tài khoản có tiền án (`fail_streak > 0`) phải vượt qua 3 nấc:

1. **Nấc 1: Mới ra tù (`probation_clean_days < 3`):**
   - Quota: **3 – 5 follows / ngày** (`mode_str = "probation_tier1"`).
   - Yêu cầu: Hoàn thành sạch 3 ngày chạy thực tế không bị nhả.
2. **Nấc 2: Tăng tải an toàn (`3 <= probation_clean_days < 6`):**
   - Quota: **7 – 9 follows / ngày** (`mode_str = "probation_tier2"`).
   - Yêu cầu: Tiếp tục hoàn thành sạch thêm 3 ngày chạy thực tế ở mức này.
3. **Nấc 3: Tốt nghiệp & Xóa án tích (`probation_clean_days >= 6`):**
   - Reset `fail_streak = 0`, xóa `probation_clean_days`.
   - Trở lại **Full Budget (`10 – 20/phiên`, `mode_str = "full"`)** như nick khỏe.

### C. Quy Đổi Thời Gian Thực Ngoài Đời
- Với lịch Parity Lane (cách nhật 2 ngày/lần) cộng tỷ lệ dưỡng sinh farm (~1/3), trung bình một nick mất $2.3\text{ ngày lịch}$ để có 1 ngày chạy.
- $3\text{ clean days} \times 2.3 \approx 7\text{ ngày lịch}$ (1 tuần) cho mỗi nấc.
- Tổng thời gian thử thách: $\approx 14 - 15\text{ ngày}$ (khoảng nửa tháng ngoài đời thực). Chu kỳ 2 tuần này tương ứng hoàn hảo với thời gian phân rã điểm phạt (Cooldown Decay) trên Server TikTok.
- **Fail-closed:** Nếu bị TikTok nhả lại ở bất kỳ nấc nào -> Lập tức vào tù nghỉ Cooldown theo streak và khi ra tù reset `probation_clean_days = 0` về lại Nấc 1.

---

## 3. Đối Soát Tính Xác Thực Dữ Liệu (Cross-verification)
- Khi nghi ngờ hàm verify bị false-positive hoặc báo cáo khống:
  - BẮT BUỘC đối soát chéo giữa `follow_state_*.json` và bảng `snapshots` trong `D:/Taadaa/data/tiktok_tracker.db`.
  - Bảng `snapshots` chứa dữ liệu cào trực tiếp từ màn hình Profile của app TikTok trên máy thật (`following_count`, `follower_count`, `video_count`).
  - Nếu số `following_count` trên TikTok tăng khớp với số follow tích lũy trong state, nick đó thực sự ăn follow thành công và không bị nhả.
