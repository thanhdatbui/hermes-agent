# Dynamic Healing Row Scoring & Anti-Consecutive Governance

## 1. Bối cảnh & Điểm mù của Cơ chế Hardcode Tĩnh (Static Heuristic)

Trước đây, trong `tiktok_runner.py`, các ca dưỡng sinh (`healing_row`) của Chu kỳ 4 ngày (Ca 3 Ngày 3 và cả 3 ca của Ngày 4 Rest Day) được gán cứng theo quy tắc tĩnh:
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

### Hai lỗ hổng thực tế nghiêm trọng:
1. **Lỗi Kẹp Ca (Back-to-back Run Anomaly):**
   - Tối Ngày 3 chạy Row 3 (Dưỡng sinh lúc 18h & 20h).
   - Sáng hôm sau Ngày 4 (06h & 08h) lại tiếp tục chạy Row 3! Khoảng cách giữa 2 ca chỉ là **10 tiếng**.
   - Cùng một dàn nick bị lôi lên máy 2 ca liên tiếp trong nửa ngày là bất thường và làm dồn toa lịch sang chu kỳ sau.
2. **Mù thông tin thực địa (Blind to Reality):**
   - Giả định cứng chỉ đưa Row 3, 4, 5, 6 vào dưỡng sinh.
   - Khi **Row 1 hoặc Row 2 bị nhả follow nhiều** (dính cờ `FOLLOW_FAILED` / `ip_circuit_breaker`), chúng hoàn toàn **bị tước quyền vào slot dưỡng sinh** để giải cứu và xả cờ phạt, buộc phải ôm án phạt nằm chờ đến vòng cày tiếp theo. Ngược lại, Row 3 dù đang khỏe lại bị đè ra chạy 2 ca liên tiếp.

---

## 2. Thiết kế Chuẩn: Cơ chế Chấm Điểm Ưu Tiên Động (Data-Driven Dynamic Healing)

Khi scheduler chạm tới slot dưỡng sinh (`target_row is None`), hệ thống không bốc tĩnh mà tính toán **Điểm Ưu Tiên Dưỡng Sinh (Healing Priority Score)** dựa trên dữ liệu thực tế:

### A. 3 Quy Tắc Bất Biến (Invariants)
1. **Ghép cặp 2 Phiên trong Ca (Session Pairing Invariant):**
   - Phiên 2 (08h, 14h, 20h) **BẮT BUỘC** chạy cùng Row với Phiên 1 (06h, 12h, 18h) của ca đó để hoàn tất trọn vẹn chu trình nuôi (Feed + Opportunistic Upload Hook).
2. **Chống Kẹp Ca Xuyên Biên Giới (Hard Anti-Consecutive Invariant):**
   - Tại Phiên 1, **BẮT BUỘC LOẠI TRỪ `last_row`** từ ca liền kề trước đó (đọc từ `runner_simple_state.json`).
   - Tuyệt đối cấm 1 Row xuất hiện ở 2 ca liên tiếp trong vòng 10–12 tiếng.
3. **Phân Tách Các Ca Ngày Nghỉ (Rest Day Diversity Invariant):**
   - Vào Ngày 4 (Rest Day gồm 3 ca Sáng - Trưa - Tối): Mỗi ca phải dưỡng sinh một Row khác nhau. Ca sau loại trừ các Row đã được nuôi ở các ca trước trong cùng ngày (`live/YYYY-MM-DD/row-*`).

### B. Công Thức Chấm Điểm Ưu Tiên
Với mỗi Row $R \in \{1..8\} \setminus \{\text{Excluded Rows}\}$:

$$\text{Score}(R) = 100 \times P_{\text{nhả}}(R) + 20 \times P_{\text{non}}(R) + 0.3 \times \text{HoursAgo}(R)$$

* **$P_{\text{nhả}}(R)$ (Trọng số 100 — P0 Khẩn cấp):**
  - Tỷ lệ tài khoản trong Row bị dính án nhả follow gần nhất (`follow_failed = True` hoặc `last_failed_date` trong vòng 3 ngày qua từ `runs/state/follow_state_*_row_R.json`).
  - Row nào đang bị TikTok phạt nhả nhiều nhất (như Row 2) sẽ có điểm vọt lên cao nhất để được giải cứu đi lướt feed xả cờ phạt.
* **$P_{\text{non}}(R)$ (Trọng số 20 — P1 Bồi dưỡng nền tảng):**
  - Tỷ lệ nick chưa đủ 10 video trong Row (truy vấn từ `farm_account_info` & `snapshots`).
* **$\text{HoursAgo}(R)$ (Trọng số 0.3 — P2 Chống bỏ đói):**
  - Thời gian tính bằng giờ kể từ lần cuối Row đó được lên máy nuôi.

Row có điểm cao nhất sẽ được chọn làm `healing_row` cho ca đó.

### C. Fail-Safe Fallback
Nếu DB hoặc thư mục state gặp lỗi truy cập/timeout:
- Hệ thống tự động fallback về danh sách thứ tự luân phiên an toàn `[2, 4, 1, 3, 5, 6, 7, 8]` và vẫn giữ nguyên luật loại trừ `last_row`. Đảm bảo cron an toàn tuyệt đối, không bao giờ bị crash hay đóng băng ca.
