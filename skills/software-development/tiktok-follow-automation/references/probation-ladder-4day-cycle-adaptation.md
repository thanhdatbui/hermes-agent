# Thích Ứng Bậc Thang Thử Thách (Graduated Probation) Với Chu Kỳ Xoay Tua 4 Ngày

## 1. Mâu thuẫn giữa Probation cũ (4 ca sạch) vs Chu kỳ 4 ngày (Burst & Hibernation)

### A. Độ trễ "ngâm chân" khi giữ nguyên 4 ca sạch
- Ở workflow cũ (chạy dồn dập hàng ngày hoặc cách nhật): 4 ca sạch mất khoảng 4–8 ngày ngoài đời thực để một nick hoàn thành Hồi phục 1 & 2 rồi tốt nghiệp lên Khỏe.
- Trong **Chu kỳ 4 ngày (Burst & Hibernation Cadence)**:
  - Mỗi tài khoản `(máy, row)` chỉ lên giàn follow **đúng 1 lần trong cả chu kỳ 4 ngày** (các ngày còn lại là ca của row khác, ngày dưỡng sinh hoặc ngày nghỉ toàn farm).
  - Nếu vẫn yêu cầu `clean_days >= 2` (Hồi phục 1) và `clean_days >= 4` (Hồi phục 2):
    * Chu kỳ 1 (Ngày 1): Hồi phục 1 (1–2 fl) -> clean=1.
    * Chu kỳ 2 (Ngày 5): Hồi phục 1 (1–2 fl) -> clean=2 (lên Hồi phục 2).
    * Chu kỳ 3 (Ngày 9): Hồi phục 2 (5–8 fl) -> clean=3.
    * Chu kỳ 4 (Ngày 13): Hồi phục 2 (5–8 fl) -> clean=4 (tốt nghiệp).
    * Chu kỳ 5 (Ngày 17): Mới chính thức chạy mức Khỏe (10–15 fl).
  - **Hậu quả:** Mất **17 ngày (gần 3 tuần)** chỉ để tốt nghiệp, trong cả 17 ngày gom vỏn vẹn ~15 follow (~1 follow/ngày), làm chậm nghiêm trọng tốc độ phát triển dàn nick.

### B. Rủi ro khi bỏ hẳn Hồi phục để nhảy thẳng Full Quota
- **Bẫy đột biến hành vi (Action Spike):** Nick vừa ra tù vẫn nằm trong danh sách giám sát ngầm của TikTok server. Nếu cấp ngay full quota (10–15 fl/phiên) sau khi mãn hạn, backend TikTok phát hiện đột biến sẽ kích hoạt án phạt tiếp theo với streak cao hơn (Streak 2: 5 ngày, Streak 3: 7 ngày, Streak 4+: 15 ngày).
- **Nguy cơ giật Cầu Dao IP MikroTik (Tier-Aware Breaker):** Trên farm Taadaa, chỉ khi nick Khỏe (`was_graduated == True`) bị nhả mới ngắt proxy MikroTik 48h. Nếu cho nick chưa qua thử thách lên Khỏe bừa bãi, tỷ lệ nhả sẽ làm giật cầu dao IP liên tục, kéo theo máy cùng dải IP bị tê liệt.

---

## 2. Quy Chuẩn Rút Gọn: 1 Phiên Sạch / 1 Nấc Thang (Fast-Track Adaptation)

Nhờ chu kỳ 4 ngày đã tạo ra **khoảng nghỉ đệm tự nhiên 72–96h** giữa 2 lần follow của cùng một nick (hành vi ngủ đông tự nhiên làm suy giảm cờ nghi vấn spam ở server TikTok), ta áp dụng quy tắc rút gọn:

| Nấc thang | Quota đề xuất | Thời gian thử thách | Điều kiện thăng hạng |
| :--- | :--- | :--- | :--- |
| **Hồi phục 1** *(Tân binh / Mới ra tù)* | **2 – 4 follows** / phiên | **Đúng 1 phiên duy nhất** (1 chu kỳ) | Chạy sạch, không bị rollback -> Thăng lên Hồi phục 2 ở chu kỳ kế tiếp. |
| **Hồi phục 2** *(Tăng tải an toàn)* | **6 – 8 follows** / phiên | **Đúng 1 phiên duy nhất** (1 chu kỳ) | Chạy sạch -> Tốt nghiệp lên **Khỏe** (Full Quota). |
| **Khỏe / Nòng cốt** | **10 – 15 follows** / phiên | Duy trì theo chu kỳ 4 ngày | Nếu bị nhả -> Phạt Cooldown theo streak và quay lại Hồi phục 1. |

- **Thời gian tốt nghiệp:** Rút ngắn từ **17 ngày xuống còn 8 ngày** (chỉ sau 2 chu kỳ chạy sạch).
- **Bảo toàn Canary Gate:** Phiên đầu (2–4 fl) đóng vai trò là probe dò đường an toàn: nếu nick chưa sạch án thì phanh ngay, chỉ phạt cá nhân account, không làm giật Cầu dao IP farm.

---

## 3. Pitfall Lệch Pha Đồng Bộ: Core Runner vs Dashboard Helper (:1905)

### Nguyên nhân gây lệch pha
Khi rút ngắn bậc thang thử thách trong core runner (`follow_runner/core/follow_state.py`) từ 2 ca/nấc xuống 1 ca/nấc, nếu bỏ quên Dashboard helper (`follow_health_helper.py` và `tiktok_dashboard.py`), giao diện sẽ tiếp tục hiển thị `(0/2 ca)` và `🎯 Cần 2 ca sạch`, gây hoang mang cho Operator tưởng rằng nick vẫn bị giam 2 ca.

### Checklist đồng bộ bắt buộc trên Dashboard Helper & Frontend:
1. **Phân tầng sức khỏe (`follow_health_helper.py`):**
   - Ngưỡng lên Hồi phục 2: Đổi từ `clean_days >= 2` thành `clean_days >= 1`.
   - Nhãn hiển thị (`tier_label`):
     * Tier 1: `🟠 Hồi phục 1 ({clean_days}/1 ca)`
     * Tier 2: `🟡 Hồi phục 2 ({clean_days - 1}/1 ca)`
   - Tiến độ thăng cấp (`sessions_needed`):
     * Tier 1: `sessions_needed = max(1, 1 - clean_days)` (cần 1 ca sạch để lên Hồi phục 2).
     * Tier 2: `sessions_needed = max(1, 2 - clean_days)` (cần thêm 1 ca sạch để tốt nghiệp).
     * Fallback DB record (`farm_account_info`): BẮT BUỘC gán `sessions_needed = 1`.
   - Sweet spot text: `"Hồi phục chuẩn, 1 ca sạch"`.
2. **Giao diện HTML/JS (`tiktok_dashboard.py`):**
   - Badge tooltip & fallback: Sửa `sessions_needed || 2` thành `sessions_needed || 1`.
3. **Kỷ luật viết Unit Test (`test_tiktok_dashboard_history.py`):**
   - Tài khoản mẫu cho nhóm `healthy_full`: BẮT BUỘC truyền `"graduated": true` vào state JSON mock. Nếu chỉ set `fail_streak: 0, probation_clean_days: 0` mà thiếu lịch sử follow, helper sẽ coi là tân binh chưa tốt nghiệp và đẩy về Tier 1.
   - Mock test transition: Mock clean_days=0 cho Tier 1 (0/1 ca), clean_days=1 cho Tier 2 (0/1 ca).
4. **Độ trễ Cache (:1905):**
   - Web Dashboard có bộ đệm cache 15s (`_CACHE_TTL = 15.0`). Khi verify API qua script, gọi trực tiếp `get_follow_health_data()` để lấy kết quả tức thì O(1) thay vì curl qua HTTP cache cũ.
