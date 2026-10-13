# Dynamic Healing Row Scoring & Anti-Consecutive Cadence

## 1. Bối cảnh & Vấn đề Của Cơ Chế Tĩnh Cũ
- **Lỗ hổng kẹp ca (Consecutive Trap):** Khi hardcode tĩnh theo slot, xảy ra hiện tượng Ca 3 tối hôm trước chạy Row 3 dưỡng sinh, sáng hôm sau (Ca 1 lúc 06:00) lại gọi tiếp Row 3 dưỡng sinh (cách nhau chỉ 10 tiếng). Điều này làm dồn tải bất thường lên cùng một dàn nick trong khi các row khác bị bỏ đói.
- **Điểm mù thực địa (Blind to Reality):** Cơ chế tĩnh chỉ luân phiên Row 3/4/5/6, loại trừ hoàn toàn Row 1, 2, 7, 8 khỏi diện dưỡng sinh. Khi Row 2 hoặc Row 4 vừa cày xong bị dính cờ nhả follow nặng (>50-70% nick dính active cooldown), chúng không bao giờ được cấp slot đi dưỡng sinh xả phạt, dẫn đến nguy cơ tích lũy rủi ro và chết nick.

---

## 2. Quy Tắc Bất Biến Lập Lịch Dưỡng Sinh Động (Invariants)

### A. Luật Ghép Cặp 2 Phiên Cùng Ca (Session Pairing Invariant)
- Trong 1 ca (gồm Phiên 1 lúc 06h/12h/18h và Phiên 2 lúc 08h/14h/20h), **Phiên 2 BẮT BUỘC ghép đúng Row của Phiên 1**.
- Tuyệt đối không đổi row giữa 2 phiên trong cùng 1 ca để bảo toàn tính trọn vẹn của ca nuôi (Feed + Upload).

### B. Luật Chống Kẹp Ca Cứng (Hard Anti-Consecutive Across Ca Boundaries)
- Khi bắt đầu Ca mới (Phiên 1): **BẮT BUỘC LOẠI TRỪ Row vừa chạy ở ca liền kề trước đó** (`runner_simple_state.json` $\rightarrow$ `last_row`).
- Cấm tuyệt đối bốc cùng 1 Row cho 2 ca liên tiếp trong vòng 10-12 tiếng.

### C. Luật Phân Tách 3 Ca Ngày Nghỉ (Rest Day Diversity)
- Vào Ngày 4 (Recovery Day / Rest Day gồm 3 ca: Sáng, Trưa, Tối):
- Mỗi ca **BẮT BUỘC dưỡng sinh một Row khác nhau** (loại trừ các row đã chạy ở ca trước trong ngày tại thư mục `live/YYYY-MM-DD`).
- Đảm bảo 3 ca trong ngày nghỉ giải cứu được 3 Row đang cần phục hồi nhất toàn farm.

---

## 3. Công Thức Chấm Điểm Ưu Tiên (Healing Priority Score)

Với mỗi candidate row $R \in \{1..8\} \setminus \{\text{excluded\_rows}\}$:

$$\text{Score}(R) = 100 \times P_{\text{nhả\_active}} + 20 \times P_{\text{non}} + \text{Chống kẹp ca}$$

1. **$P_{\text{nhả\_active}}$ (Trọng số 100 — P0 Khẩn cấp nhất):**
   - Tỷ lệ máy/nick của Row đó đang dính án **Active Cooldown / Nhả follow thật** (đọc từ `runs/state/follow_state_*.json`):
     * `is_cooldown = True` khi `today <= cooldown_until_date` hoặc `now < cooldown_until_at` hoặc `today <= failed_date + streak_days`.
   - Tránh bẫy: Cấm dùng `fail_streak > 0` thuần túy vì án cũ đã hết hạn vẫn giữ nguyên số streak, gây dương tính giả cho các row đã sạch phạt.
2. **$P_{\text{non}}$ (Trọng số 20 — P1 Nhóm nick trẻ):**
   - Tỷ lệ nick $< 10$ video trong Row (truy vấn nhanh từ `farm_account_info` & `snapshots` trong `tiktok_tracker.db`).
3. **Cơ chế Cache 60s (In-Memory Throttle):**
   - Kết quả quét tỷ lệ $P_{\text{nhả}}$ và $P_{\text{non}}$ được đệm trong RAM 60s để khi chạy loop hoặc kiểm thử suite không bao giờ bị nghẽn I/O hay timeout.

---

## 4. Fallback An Toàn Tương Thích Ngược (Fail-Safe Hierarchy)
- Khi gặp lỗi dependency, path môi trường hoặc CSDL bận:
- **BẮT BUỘC fallback về đúng Row tương thích ngược theo slot và chu kỳ cũ** (`Row 3/4/5/6`). Cấm gán cứng `row = 2` để tránh gây sai lệch chu kỳ khi selector gặp sự cố.
- **BẮT BUỘC phát Structured Telemetry Warning** (`{"event": "healing_row_fallback", "error": "...", "row": row}`) để watchdog và dashboard phát hiện ngay điểm mù.
