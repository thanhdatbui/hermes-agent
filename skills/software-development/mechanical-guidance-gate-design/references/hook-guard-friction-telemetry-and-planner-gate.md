# Operational Guard Friction Telemetry & Planner Gate Observability (Báo Cáo Tỷ Lệ Ma Sát Hook Guard & Gate Planner Định Kỳ)

## 1. Bối cảnh & Vấn đề Thực Tế
Trong các hệ thống AI Coordinator - Worker tự hành, hệ thống phòng thủ thường được chia làm nhiều tầng:
- **Tầng Pre-Tool Hook Guards (`guard_scan_audit.jsonl`):** Chặn các hành vi rủi ro ngay trước khi tool thực thi (quét thư mục gốc diện rộng `GUARD_SEARCH_FILES_ROOT`, thiếu timeout `GUARD_FOREGROUND_TIMEOUT_MISSING`, timeout vượt trần 60s `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`, lệnh `find`/`os.walk`...).
- **Tầng Dispatch Gate (`dispatch_audit.jsonl`):** Chặn khi Agent gọi sai kênh điều phối (dùng `delegate_task` cho việc sửa code thay vì `dispatch_worker.py`, task khảo sát không có budget hoặc budget > 8 calls, thiếu nhãn `FILE:`).
- **Tầng Planner Gate (`dispatch_planner.py` / Gate B):** Lập kế hoạch kiến trúc đa tầng (Tier 1 Claude Sonnet $\to$ Tier 2 Sol Planner $\to$ Tier 3 Coordinator Fallback).
- **Tầng CI/CD Chốt Phiên (`gate_audit.jsonl`, `closeout_gate.py`, `safe_push.py`):** Thẩm định merge, canary máy thật, chấm điểm reviewer.

### Bẫy Thiết Kế Của Watchdog Đối Soát Cũ:
Nếu watchdog 6h (`gate_compliance_watchdog.py`) chỉ tập trung vào 8 Gate CI/CD chốt phiên, nó sẽ rơi vào tình trạng:
1. **7/8 Gate luôn báo `NO_EVIDENCE`:** Trong các khung giờ vận hành bình thường (nuôi farm, cào dữ liệu, xử lý sự cố không tạo commit), không có đợt chốt phiên nào diễn ra nên báo cáo hoàn toàn trống rỗng, vô nghĩa.
2. **"Mù" hoàn toàn với điểm ma sát lớn nhất:** Trong 24h qua, Agent thực tế đã bị Hook chặn **494 lần** và bị Dispatch chặn **563 lần** (hơn 1.000 lần va chạm). Agent tốn token, xoay xở nhiều turn thử-sai trong bóng tối mà Operator không hề hay biết để bổ sung guidance.
3. **Thiếu Gate Planner:** Vai trò tối quan trọng của Sonnet Planner / Sol Planner trong việc tạo kiến trúc trước khi worker thi công hoàn toàn không có chỉ số đo lường.

---

## 2. Số Liệu Đối Soát Thực Tế (Case Study 24h & 6h)

### Top Hook Guards Bị Vi Phạm Nhiều Nhất (`guard_scan_audit.jsonl`):
1. **`GUARD_DANGEROUS_ROOT` (34.2% - 169/494 lần):** Agent tự ý viết script Python quét đĩa diện rộng trên `D:/Taadaa` thay vì trỏ file cụ thể.
2. **`GUARD_SEARCH_FILES_ROOT` (21.3% - 105/494 lần):** Agent gọi tool `search_files` trên root thay vì giới hạn path.
3. **`GUARD_FOREGROUND_TIMEOUT_EXCEEDED` (14.0% - 69/494 lần):** Chạy terminal foreground với timeout > 60s khi chưa dùng canonical script được allowlist.
4. **`GUARD_FOREGROUND_TIMEOUT_MISSING` (11.1% - 55/494 lần):** Quên truyền tham số `timeout` vào terminal tool.
5. **`GUARD_FIND_SCAN` & `GUARD_PYTHON_WALKER` (7.9% - 39/494 lần):** Dùng shell `find` hoặc `os.walk`/`glob(recursive=True)`.

### Top Điểm Nghẽn Điều Phối (`dispatch_audit.jsonl`):
1. **`subagent_edit_blocked` (48.8% - 275/563 lần):** Agent cố dùng `delegate_task` để sửa code thay vì gọi `dispatch_worker.py`.
2. **`investigate` (46.9% - 264/563 lần):** Agent gọi `delegate_task` đọc log/khảo sát nhưng không giới hạn budget hoặc budget > 8 calls.
3. **`create` (4.3% - 24/563 lần):** Thiếu nhãn `FILE: <path>`.

---

## 3. Nguyên Tắc & Yêu Cầu Kiến Trúc Chuẩn Hóa

### 1. Dual-Spectrum Watchdog Architecture
Báo cáo tuân thủ định kỳ 6h BẮT BUỘC phải tích hợp 2 phân hệ song song:
- **Phân hệ 1: Workflow & Planner Gates:**
  - `G_PLAN`: Tỷ lệ thành công và phân bổ tier của Planner (Claude Sonnet vs Sol Planner vs Fallback).
  - `G_CANARY`: Tỷ lệ Canary máy thật pass/fail.
  - `G_REVIEW`: Tỷ lệ Reviewer chấm APPROVED / REJECTED (có tính remediation loop).
  - `G_CLOSEOUT`: Tỷ lệ điểm chốt phiên $\ge 85$.
- **Phân hệ 2: Hook Guard Friction & Violation Breakdown:**
  - Tổng số lần chặn trong cửa sổ rolling (6h/24h).
  - Bảng xếp hạng Top 5 Hook Guard bị vi phạm nhiều nhất kèm số lần và tỷ lệ `%`.
  - Phân tích nguyên nhân vi phạm chính và tool tương ứng (`terminal`, `search_files`, `delegate_task`).

### 2. Guidance-Targeting Feedback Loop (Vòng Lặp Nạp Hướng Dẫn Giảm Hao Token)
- Báo cáo tỷ lệ vi phạm sinh ra là để Operator (hoặc hệ thống tự động) nhìn thấy ngay **"Agent đang ngã ở đâu nhiều nhất"**.
- Khi phát hiện một Hook chiếm $> 20\%$ số lần chặn (như `GUARD_SEARCH_FILES_ROOT` hay `subagent_edit_blocked`):
  - Operator hoặc Coordinator dùng ngay `python D:/Taadaa/tools/guardgate/update_guidance.py` nạp hướng dẫn kiến trúc rõ ràng cho rule đó.
  - Cập nhật prompt/system rules để Agent nắm vững đường bay $O(1)$ (ví dụ: "Muốn sửa code: dùng `dispatch_worker.py`; Muốn tìm file: dùng `search_files(target='files')`, cấm quét content trên root").
  - Triệt tiêu các lượt thử-sai vô ích, giảm chi phí token và tăng tốc độ xử lý task.

### 3. UTC Time Parsing & Zero Naive-vs-Aware Collision
- Trong các script phân tích log (`gate_compliance_watchdog.py`), tuyệt đối cấm so sánh trực tiếp datetime naive với datetime timezone-aware.
- Chuẩn hóa:
  ```python
  # Tách chuỗi ISO và xử lý timezone đồng bộ
  clean_ts = ts.split('+')[0].replace('Z', '')
  dt = datetime.fromisoformat(clean_ts).replace(tzinfo=timezone.utc)
  ```
- Quét linh hoạt qua các key timestamp: `timestamp_utc`, `timestamp`, `ts`, `time`, `created_at`.
