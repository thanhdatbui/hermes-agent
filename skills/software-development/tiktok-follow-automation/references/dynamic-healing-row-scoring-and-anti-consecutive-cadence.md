# Dynamic Healing Row Scoring & Anti-Consecutive Cadence

## 1. Lỗ Hổng Của Cơ Chế Dưỡng Sinh Gán Tĩnh (Static Heuristic Trap)

Trong lịch trình chu kỳ 4 ngày (96h):
- Ngày 1: Rows lẻ (1, 3, 5).
- Ngày 2: Rows chẵn (2, 4, 6).
- Ngày 3: Ca 1 (Row 7), Ca 2 (Row 8), Ca 3 (Dưỡng sinh pure feed).
- Ngày 4: Dưỡng sinh xả tải toàn farm (3 ca pure feed).

### Vấn đề thực tế khi hardcode tĩnh `healing_row` (Bài học 2026-10-13):
1. **Bẫy kẹp ca dồn dập (Consecutive Ca Trapping):**
   - Khi gán tĩnh Ca tối Ngày 3 chọn Row 3, và Ca sáng Ngày 4 cũng chọn Row 3:
     Cùng 1 dàn nick bị lôi lên máy 2 ca liên tiếp trong vòng **10 tiếng** (20h tối đến 06h sáng hôm sau), sau đó ngày kia lại vào lịch cày chính $\rightarrow$ mật độ chạy quá dày làm mất ý nghĩa xả tải.
2. **Mù thông tin thực địa (Blind to Fleet Reality):**
   - Heuristic tĩnh chỉ luân phiên Row 3/4/5 mà bỏ qua Row 1, 2, 7, 8.
   - Khi Row 2 vừa cày xong hôm trước và bị TikTok gắn cờ nhả follow hàng loạt (>70% nick dính Active Cooldown), Row 2 hoàn toàn không có cơ hội được cấp slot dưỡng sinh để gỡ án, dẫn đến tích tụ rủi ro.

---

## 2. Thiết Kế Chọn Row Dưỡng Sinh Động (Data-Driven Dynamic Healing)

Module triển khai: `D:/Taadaa/tools/healing_selector.py` được gọi bởi `tiktok_runner.py` khi `target_row is None`.

### 4 Ràng Buộc & Quy Tắc Cốt Tử:

1. **Ràng buộc Ghép Cặp Phiên (Session Pairing Invariant):**
   - Mỗi ca gồm 2 phiên: Phiên 1 (06h, 12h, 18h) và Phiên 2 (08h, 14h, 20h).
   - Phiên 2 **BẮT BUỘC** chạy cùng Row với Phiên 1 của ca đó để hoàn tất đủ 2 phiên nuôi (Session 1 lướt feed + Session 2 lướt feed & kẹp kiểm tra upload).
   - Kiểm tra qua `runner_simple_state.json`: nếu `last_window` khớp nhịp Phiên 1 cùng ngày $\rightarrow$ giữ nguyên `last_row`.

2. **Ràng buộc Chống Kẹp Ca (Anti-Consecutive Boundary Invariant):**
   - Khi bắt đầu ca mới: **BẮT BUỘC LOẠI TRỪ `last_row`** của ca liền trước (đọc từ `runner_simple_state.json`).
   - Triệt tiêu 100% rủi ro chạy cùng một Row ở 2 ca sát nhau.

3. **Ràng buộc Đa Dạng Hóa Ngày Nghỉ (Rest Day Diversity Invariant):**
   - Trong Ngày 4 (Rest Day toàn farm gồm 3 ca): loại trừ các Row đã được chạy ở các ca trước trong ngày (đối soát folder `runtime/kibe/live/YYYY-MM-DD/row-*`).
   - Đảm bảo 3 ca trong ngày nghỉ giải cứu 3 Row khác nhau.

4. **Công Thức Chấm Điểm Ưu Tiên (Healing Priority Score):**
   Với mỗi Row $R \in \text{Candidates}$:

   $$\text{Score}(R) = 100 \times P_{\text{ActiveFail}} + 20 \times P_{\text{Young}}$$

   - **$P_{\text{ActiveFail}}$ (Trọng số 100 — P0 Khẩn cấp):** Tỷ lệ máy trong Row đang có **Active Cooldown** thực sự:
     * `follow_failed == True` và chưa quá `streak_days` (3/5/7 ngày).
     * `cooldown_until_date >= today`.
     * `now < cooldown_until_at`.
     * ⚠️ **BẪY KỸ THUẬT CẦN TRÁNH:** Tuyệt đối không chỉ đọc `fail_streak > 0`. Trong Taadaa Farm, `fail_streak` được bảo lưu để theo dõi lịch sử và không bị reset khi hết hạn. Nếu chỉ đọc `fail_streak > 0` sẽ bị 100% false positive cho các nick đã hết hạn cooldown từ nhiều ngày trước!
   - **$P_{\text{Young}}$ (Trọng số 20 — P1 Bồi dưỡng nền tảng):** Tỷ lệ tài khoản $< 10$ video từ bảng `snapshots` & `farm_account_info`.
   - Row có $\text{Score}(R)$ cao nhất được bốc để chạy dưỡng sinh.

5. **Cơ Chế Dự Phòng (Fail-Safe Fallback):**
   - Khi DB `tiktok_tracker.db` bị khóa hoặc thư mục live lỗi: fallback an toàn theo thứ tự ưu tiên `[2, 4, 1, 3, 5, 6, 7, 8]` sau khi đã loại trừ `last_row`, đảm bảo cron không bao giờ crash.
