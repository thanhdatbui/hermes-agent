# Dynamic Healing Row Selection & Anti-Consecutive Cadence

## 1. Bối cảnh & Lỗ hổng của cơ chế chọn tĩnh (Static Healing Slots)
Trước tháng 10/2026, lịch chạy runner gán tĩnh các ca dưỡng sinh (Ca 3 Ngày 3 và cả 3 Ca Ngày 4):
- Ngày 3 Ca 3 (Tối): Gán cứng luân phiên Row 3 hoặc Row 4.
- Ngày 4 (Rest Day): Ca sáng gán Row 3, Ca trưa gán Row 4, Ca tối gán Row 5/6.

### 2 Lỗ hổng nghiêm trọng đã bộc lộ trong vận hành thực tế:
1. **Lỗi Kẹp Ca (Back-to-Back Shifts in < 10h):**
   - Tối Ngày 3 (20:00) chạy Row 3 dưỡng sinh, sáng Ngày 4 (06:00) lại lôi Row 3 ra dưỡng tiếp.
   - Khoảng cách chỉ 10 tiếng khiến tài khoản bị dồn toa, mất nhịp sinh học tự nhiên.
2. **Mù thông tin thực địa (Blind to Real-world Follow Failures):**
   - Row 2 cày ngày hôm trước bị dính cờ nhả follow cao (57.7% nick dính active cooldown) nhưng bị loại hoàn toàn khỏi lịch dưỡng sinh tĩnh.
   - Row 4 dính 77.9% active cooldown cũng không được giải cứu kịp thời.
   - Trong khi đó, Row 3 đang khỏe (chỉ 17.6% cooldown) lại bị đè ra chạy 2 ca liên tiếp.

---

## 2. Thiết kế Kiến trúc: Cơ chế Chấm Điểm Động (`healing_selector.py`)

Khi runner chạm vào một slot dưỡng sinh (`target_row is None`), hàm `determine_healing_row()` được kích hoạt với 4 quy tắc bắt buộc:

### Quy tắc 1: Ghép cặp 2 phiên cùng ca (Session Pairing Invariant)
- Mỗi ca có 2 phiên: Phiên 1 (06h, 12h, 18h) và Phiên 2 (08h, 14h, 20h).
- Phiên 2 **bắt buộc bốc đúng Row mà Phiên 1 đã chạy** (kiểm tra `last_window` từ `runner_simple_state.json`) để đảm bảo hoàn thành trọn vẹn 2 phiên cho cùng 1 Row.

### Quy tắc 2: Chống kẹp ca qua ranh giới ca (Anti-Consecutive Boundary Rule)
- Phiên 1 của ca mới **bắt buộc loại trừ `last_row` của ca liền trước** (đọc từ `runner_simple_state.json`).
- Triệt tiêu 100% rủi ro chạy cùng 1 Row ở ca tối rồi sáng hôm sau lại chạy tiếp.

### Quy tắc 3: Phân chia 3 ca ngày nghỉ (Rest Day Multi-Ca Partitioning)
- Vào Ngày 4 (Rest Day, `cycle_day == 3`), kiểm tra thư mục live hôm nay (`runtime/kibe/live/YYYY-MM-DD/`).
- **Loại trừ toàn bộ các Row đã chạy ở các ca trước trong ngày** $\rightarrow$ Đảm bảo 3 ca trong ngày nghỉ sẽ giải cứu 3 Row kiệt sức khác nhau, không bao giờ trùng lặp.

### Quy tắc 4: Công thức Chấm điểm Ưu tiên (Priority Scoring Formula)
Với các candidate rows hợp lệ còn lại:

$$\text{Score}(R) = 100 \times P_{\text{fail\_active}} + 20 \times P_{\text{young}}$$

* $P_{\text{fail\_active}}$: Tỷ lệ máy của Row đó đang dính **Active Cooldown** (tính theo thời điểm hiện tại `now < until_dt` hoặc `today <= cooldown_until_date` hoặc `today <= failed_date + streak_days`).
* $P_{\text{young}}$: Tỷ lệ nick chưa đủ 10 video trong Row (đọc từ `farm_account_info` & `snapshots`).
* Row có $\text{Score}$ cao nhất sẽ được chọn làm `healing_row`.

---

## 3. Cạm bẫy kỹ thuật & Lưu ý sống còn (Closeout Gate Lessons 2026-10-13)

1. **Bẫy `fail_streak` lịch sử:**
   - Trong `follow_state_*.json`, khi nick từng dính nhả từ 2 tuần trước, trường `fail_streak = 1` vẫn được lưu vĩnh viễn (do luật không được tự ý xóa án).
   - **CẤM TUYỆT ĐỐI** chỉ kiểm tra `fail_streak > 0` hoặc `follow_failed_date` mà không đối chiếu với ngày hết hạn cooldown! Kiểm tra ẩu sẽ biến 100% nick cũ thành "đang bị nhả", làm sai lệch toàn bộ điểm số.
2. **Bẫy nghẽn CPU / I/O quét đĩa (Performance Invariant):**
   - Quét 413 file JSON trạng thái tốn ~1.7 giây mỗi lần.
   - Khi chạy test suite lặp 48 ngày (96 lần gọi), thời gian tăng vọt lên > 160 giây và gây timeout test suite.
   - **Giải pháp bắt buộc:** Cài đặt bộ đệm in-memory 60 giây (`_CACHE_FAIL_RATES`, TTL = 60.0s). Giúp các lệnh gọi liên tiếp trong vòng 1 phút phản hồi tức thì (< 10ms) mà vẫn đảm bảo tính tươi mới tuyệt đối giữa các tick cron 15 phút.
3. **Cơ chế Fallback Fail-Safe & Tương thích ngược:**
   - Nếu `healing_selector` gặp lỗi (thiếu module, DB bận hoặc sai path), tuyệt đối **CẤM fallback im lặng gán cứng row = 2**. Gán cứng sẽ tạo điểm mù vận hành và làm chệch lịch cũ.
   - Fallback **bắt buộc bảo toàn 100% logic tương thích ngược** của lịch cũ (`Row 3/4/5/6` theo `cycle_day`, `cycle_idx` và `slot_key`).
4. **Structured JSON Telemetry Invariant (Reviewer Requirement):**
   - CẤM log chuỗi tự do (như `[HEALING_SELECTOR_FALLBACK] ...`) gây khó khăn cho log parser và phân tích dài hạn.
   - **Bắt buộc emit JSON event có cấu trúc**:
     - Khi chọn thành công (stdout):
       ```python
       sys.stdout.write(json.dumps({
           "event": "healing_row_selected",
           "row": row,
           "window": window_label,
           "cycle_day": cycle_day,
           "cycle_idx": cycle_idx,
           "tools_dir": str(tools_dir),
       }, sort_keys=True) + "\n")
       ```
     - Khi rơi vào fallback (stderr):
       ```python
       sys.stderr.write(json.dumps({
           "event": "healing_row_fallback",
           "row": row,
           "window": window_label,
           "cycle_day": cycle_day,
           "cycle_idx": cycle_idx,
           "error_type": type(exc).__name__,
           "error": str(exc),
       }, sort_keys=True) + "\n")
       ```
5. **Đường dẫn Portable (Anti-Hardcoded Path Invariant):**
   - CẤM hardcode trực tiếp `D:/Taadaa/tools` trong runtime script. Khi deploy sang máy khác hoặc chạy test isolated sẽ gãy ngay.
   - **Pattern chuẩn:** Ưu tiên đọc biến môi trường `HERMES_CRON_TOOLS_DIR`, sau đó dò ngược qua các thư mục cha `[p / "tools" for p in Path(__file__).resolve().parents]` để tìm chính xác nơi chứa `healing_selector.py`.
6. **Audit JSONL Bền Vững & Log Rotation (Closeout Gate Standards 2026-10-13):**
   - Mọi quyết định chọn Row bắt buộc xuất bản ghi JSONL bất biến vào `D:/Taadaa/runtime/audit_logs/healing_decision_audit.jsonl`.
   - Payload bắt buộc chuẩn hóa `schema_version: "1.0"` kèm `trace_id` ngẫu nhiên, `timestamp` ISO UTC, `row`, `score` và danh sách `candidates`.
   - **Cơ chế xoay vòng file (Log Rotation):** Khi file vượt ngưỡng 5MB, tự động đổi tên sang `.jsonl.1` trước khi ghi mới để chống phình đĩa.
   - **Cấm nuốt exception rộng (No Broad Silent Pass):** Toàn bộ các khối try-except quét state file, truy vấn SQLite và scan thư mục live bắt buộc ghi nhận `logger.warning` / `logger.exception`, tuyệt đối không để `pass` im lặng che giấu lỗi dữ liệu.
