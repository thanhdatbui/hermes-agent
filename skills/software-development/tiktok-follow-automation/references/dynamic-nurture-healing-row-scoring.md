# Dynamic Nurture & Healing Row Scoring (Cơ chế Chọn Row Dưỡng Sinh Động)

## 1. Bối cảnh & Lỗ hổng của Cơ chế Chọn Tĩnh (Static Hardcoding)
Trước đây, các slot Dưỡng sinh (Ca 3 Ngày 3 và cả 3 ca Ngày 4 Rest Day) được gán cứng theo quy tắc modulo:
```python
if cycle_day == 2:
    healing_row = 3 if (cycle_idx % 2 == 0) else 4
elif slot_key in ((6, 0), (8, 0)):
    healing_row = 3
elif slot_key in ((12, 0), (14, 0)):
    healing_row = 4
else:
    healing_row = 5 if (cycle_idx % 2 == 0) else 6
```

### Hai lỗ hổng chết người của logic tĩnh:
1. **Hiện tượng Kẹp Ca / Liên tiếp (Consecutive Run Flaw):**
   - Tối Ngày 3 (20:00) chạy Row 3 dưỡng sinh $\rightarrow$ Sáng Ngày 4 (06:00) lại lôi Row 3 ra dưỡng sinh tiếp (chỉ cách nhau 10 tiếng).
   - Đến trưa Ngày 5 (12:00) Row 3 lại vào lịch cày chính $\rightarrow$ Row 3 bị đè chạy 3 ca trong vòng 48h.
2. **Mù Dữ Liệu Thực Địa (Blind to Fleet State):**
   - Row 1, 2, 7, 8 bị **loại trừ hoàn toàn** khỏi các slot dưỡng sinh.
   - Khi Row 2 cày ở Ngày 2 bị dính cờ nhả follow nhiều (`FOLLOW_FAILED` / circuit breaker), Row 2 hoàn toàn không có cơ hội được cứu trong ca dưỡng sinh, phải ôm án phạt chờ đến vòng cày sau.

---

## 2. Nguyên tắc Thiết kế: Cơ chế Tính Điểm Động (Dynamic Health Scoring)

User Correction (2026-10-13): *"Đáng lẽ cơ chế chọn nick đi dưỡng phải động theo chỉ số nick r tính trung bình toàn row để chọn row cần dưỡng chứ... Đổi qua cơ chế tính điểm đi"*.

### 2.1. Luật Bất Biến Chống Kẹp Ca (Hard Anti-Consecutive Invariant)
- **BẮT BUỘC LOẠI TRỪ Row vừa chạy ở ca liền kề trước đó:**
  $$R \in \{1..8\} \setminus \{\text{last\_row}\}$$
  - Đọc `last_row` từ `runner_simple_state.json`.
  - Nếu ca trước chạy Row 3 $\rightarrow$ Ca tiếp theo tuyệt đối cấm chọn Row 3, bắt buộc chuyển sang Row có điểm cao thứ nhì.

### 2.2. Công thức Điểm Ưu Tiên Dưỡng Sinh (Healing Priority Score)
Với mỗi Row $R \in \{1..8\} \setminus \{\text{last\_row}\}$:

$$\text{Score}(R) = 50 \times P_{\text{nhả}}(R) + 1.0 \times \text{HoursAgo}(R) + 10 \times P_{\text{non}}(R)$$

1. **$P_{\text{nhả}}(R)$ (Trọng số 50 — P0 Khẩn cấp nhất):**
   - Tỷ lệ tài khoản trong Row đang dính cờ nhả follow (`FOLLOW_FAILED`, `ip_circuit_breaker`, hoặc `fail_streak > 0`) trong 48h gần nhất.
   - **Lý do thuật toán:** Nick bị nhả follow là do backend TikTok kích hoạt Action Block ngầm. Đây là nhóm có rủi ro cao nhất (High Risk Anomaly), bắt buộc phải được ưu tiên số 1 đi dưỡng sinh (`0 follow`, pure feed) để gỡ cờ phạt và hồi Trust Score.
2. **$\text{HoursAgo}(R)$ (Trọng số 1.0 — P1 Chống bỏ đói):**
   - Số giờ kể từ lần cuối Row đó xuất hiện trên máy (`_get_cluster_row_last_nurtured`).
   - Đảm bảo không Row nào bị bỏ đói quá ngưỡng $STARVATION\_THRESHOLD\_H$ (108h).
3. **$P_{\text{non}}(R)$ (Trọng số 10 — P2 Nhóm trẻ):**
   - Tỷ lệ tài khoản có $< 10$ video trong Row. Nhóm này cần lướt FYP tích lũy độ ngâm và video.

### 2.3. Cơ chế Dự phòng An toàn (Fail-Safe Deterministic Fallback)
Nếu database `tiktok_tracker.db` hoặc folder runtime không truy cập được:
- Fallback về danh sách ưu tiên an toàn `[3, 4, 5, 2, 6, 1, 7, 8]` sau khi đã lọc bỏ `last_row`.
- Đảm bảo runner luôn xác định được Row hợp lệ trong $O(1)$ mà không bị crash hay gián đoạn cron.
