# Multi-Shift Watchdog State Contracts & Sol Auditor Gating (>= 85/100)

Kinh nghiệm đúc rút từ phiên 20/09/2026 khi nới rộng watchdog ca tối sang hỗ trợ đa ca (Sáng - Trưa - Tối) và vượt qua Closeout Gate Sol Auditor từ 76 -> 82 -> 84 -> 87/100 (APPROVED).

## 1. Cạm bẫy Hardcoded Ca & Tiêu đề Báo cáo
- **Hiện tượng**: Cron/watchdog ban đầu chỉ viết cho ca tối (`post_evening_gpm_login_watchdog.py`), sau đó được nới schedule để chạy vào các khung rảnh ca sáng/trưa. Tuy nhiên tiêu đề báo cáo vẫn hardcode `[LOGIN GPM ĐÊM - TỔNG KẾT]` và `Hoàn tất ca tối`. Khi chạy xong vào đầu giờ chiều (13:41), watchdog bắn tin tổng kết "ca tối", gây nhầm lẫn nghiêm trọng cho vận hành.
- **Giải pháp chuẩn**:
  - Tạo helper hàm nhận diện ca động (`get_current_shift_info() -> (shift_code, shift_label, shift_desc)`):
    - `07:15 - 08:45` -> `("SANG", "SÁNG", "sáng")`
    - `12:00 - 13:45` -> `("TRUA", "TRƯA", "trưa")`
    - `20:15 - 23:45` -> `("TOI", "TỐI", "tối")`
    - Fallback: `< 12` SANG, `< 18` TRUA, còn lại TOI.
  - Động hóa tiêu đề báo cáo: `[LOGIN GPM {shift_label} - TỔNG KẾT]` và `Hoàn tất ca {shift_desc}`.

## 2. Quản lý State Transition Đa Ca (Multi-Shift State)
- **Cạm bẫy cờ `finished: true`**:
  - Nếu watchdog dùng cờ boolean toàn cục `"finished": true`, khi ca trưa chạy xong, state set `finished: true` cho cả ngày (`date == today`). Kết quả là ca tối thực sự (20:15+) sẽ bị skip hoàn toàn.
- **Quy chuẩn State**:
  - Tách danh sách ca đã hoàn tất: `"finished_shifts": ["TRUA"]` và `"reported_shifts": ["TRUA"]`.
  - Điều kiện bỏ qua trong `main()`: Chỉ bỏ qua nếu ca hiện tại (`shift_code`) đã nằm trong `finished_shifts` của cùng ngày.
  - Cờ `"finished": true` toàn ngày CHỈ được set khi ca tối đã chạy xong (`shift_code == "TOI"`) hoặc toàn bộ các ca trong ngày (`{"SANG", "TRUA", "TOI"}`) đều đã hoàn thành.
  - **Tương thích ngược**: Khi đọc state schema cũ chỉ có `{"finished": false, "reported": true}`, code phải tự động fallback `finished_shifts = []` thay vì crash.

## 3. Kỷ luật Fail-Closed Soak Gate (Chống rò rỉ tài khoản chưa ngâm)
- **Cạm bẫy parse ngày ngâm**:
  - Khi kiểm tra tài khoản đã đủ điều kiện ngâm `>= 7 ngày`: Nếu dữ liệu ngày tạo (`created_date`) bị thiếu (`None`), rỗng, hoặc chuỗi ngày không đúng chuẩn ISO (`invalid-date`), code không được phép cho tài khoản đi tiếp.
  - **Quy tắc**: Bắt buộc Fail-Closed — thiếu ngày hoặc lỗi parse `datetime.fromisoformat` phải lập tức `continue` (bỏ qua candidate) và ghi log telemetry, tuyệt đối không để lọt tài khoản chưa thẩm định đủ độ tuổi ngâm.

## 4. Bí Quyết Đạt Điểm Cao Sol Auditor (>= 85/100)
Qua các vòng review thực tế từ 76 lên 87 điểm:
1. **Không dùng assertion inline toán học để thế cho hàm thật**:
   - Viết `assert (today - created).days >= 7` trong test bị reviewer trừ điểm vì "chỉ kiểm tra biểu thức nội bộ test".
   - BẮT BUỘC: Test phải import module thật (`import post_evening_gpm_login_watchdog as w`) và gọi trực tiếp `w.get_candidates()`, `w._load_gmail_clean_creation_dates()`.
2. **Kiểm tra SQLite bằng Database Thật (In-memory / Temp file)**:
   - Thay vì mock toàn bộ sqlite cursor, hãy khởi tạo SQLite database thật với schema chuẩn (`CREATE TABLE profiles ...; CREATE TABLE cookies ...;`) và chèn dòng dữ liệu test để chứng minh hàm truy vấn SQL thật chạy đúng.
3. **Bao phủ các nhánh ngoại lệ mạng (Edge cases)**:
   - Luôn viết test cho trường hợp API ngoài bị Timeout (`urllib.request.urlopen` bắn `TimeoutError`) để chứng minh hàm bắt lỗi an toàn và fallback về `set()` rỗng.
4. **Structured Candidate Audit Telemetry**:
   - Thêm hàm log audit tường minh cho candidate lifecycle:
     ```python
     def log_candidate_audit(action: str, email: str, reason: str, mid: int | None = None, port: str | None = None):
         log(f"[AUDIT] action={action} email={email} mid={mid} port={port} reason={reason}")
     ```
     Ghi nhận mọi hành động `ACCEPT` và `REJECT` (kèm chi tiết lý do soak, proxy limit, duplicate mid, offline ADB).
