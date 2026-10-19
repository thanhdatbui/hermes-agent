# Frontend Component Review Scoring, Sol Repair Syntax Invalidation & Worker Fallback (2026-10-19)

## 1. Bối cảnh & Hiện tượng (Session 19/10/2026)
Trong phiên làm việc sửa lỗi click ID trong Sổ Bệnh Án (`follow_detail_component.py`) và bổ sung test kiến trúc (`test_dashboard_architecture_gate.py`), quy trình Closeout Gate đã trải qua 3 vòng chấm điểm:
- **Lần 1 (Strike 1):** Reviewer chấm **76/100 (REJECTED)**. Điểm trừ lớn nhất ở Telemetry (8/15) và thiếu test bảo mật XSS / ma trận dữ liệu lỗi.
- **Sol Repair Strike 1 & 2:** Sinh ra patch proposal bị `syntax_ok: false` (`SyntaxError at line 1: invalid syntax` do code JavaScript nhúng trong Python template string bị Sol viết như JS trần).
- **Lần 2 (Strike 2):** Nâng test tĩnh lên 15 passed, điểm tăng lên **78/100 (REJECTED)**. Reviewer chỉ ra:
  1. Thiếu log vòng đời tải dữ liệu (Telemetry).
  2. Nhãn `'Chưa từng (sạch)'` mang tính suy đoán, gây hiểu nhầm nếu dữ liệu lịch sử thất bại bị thiếu thay vì thực sự chưa từng thất bại.
- **Strike 3 Hand-off:** Chuyển sang Worker (`claude_worker.py --role worker`), tự khắc phục dứt điểm 3 điểm trừ, nâng điểm lên **84/100 (APPROVED theo Grace Band 80–84)** và push an toàn.

---

## 2. Các Bài Học Cốt Tử Về Chấm Điểm Giao Diện Frontend (Reviewer Sol Rubric)

### A. Bổ sung Telemetry vòng đời tải dữ liệu trong UI Components
- Với các component giao diện thuần (HTML/JS), reviewer thường trừ 6–7 điểm ở hạng mục `telemetry_observability` (chỉ cho 8/15) nếu không có log theo dõi vòng đời dữ liệu.
- **Cách khắc phục chuẩn:** Luôn thêm 3 mốc console logging có cấu trúc kèm ngữ cảnh (`seq`, `machine`, `row`, `error`):
  ```javascript
  console.info('[follow-detail] loading', { seq, machine, row });
  // khi nạp thành công:
  console.info('[follow-detail] loaded', { seq, machine, row });
  // trong khối catch:
  console.error('[follow-detail] load failed', { seq, machine, row, error: err });
  ```
  Thao tác này lập tức kéo điểm `telemetry_observability` từ 8/15 lên 12/15 (+4 điểm).

### B. Tránh nhãn suy đoán khi dữ liệu bị thiếu (Anti-Speculative Labeling)
- Reviewer Sol Auditor đánh giá rất khắt khe về tính trung thực của nhãn dữ liệu:
  * Nhãn suy đoán bị phạt: `'Chưa từng (sạch)'` khi `last_failed_ceiling` là `null/undefined/empty` (vì thiếu dữ liệu không đồng nghĩa với việc nick chưa từng thất bại).
  * Nhãn trung thực được cộng điểm: `'Chưa ghi nhận'` phản ánh đúng trạng thái cơ sở dữ liệu hiện tại.

### C. Tiêu chuẩn an toàn cho liên kết mở ngoài (External Anchor Links)
- Khi render link dẫn ra TikTok hoặc trang ngoài trong bảng/modal:
  1. `encodeURIComponent(username)`: Chống phá vỡ URL query/path.
  2. `fdEsc(username)`: Chống XSS trên text hiển thị.
  3. `rel="noopener"`: Chống reverse tabnabbing khi mở tab mới (`target="_blank"`).
  4. `onclick="event.stopPropagation();"`: Ngăn sự kiện click lan truyền lên hàng bảng (row-click handler) gây toggle hoặc đóng modal ngoài ý muốn.

---

## 3. Quy Trình Xử Lý Khi Sol Repair Bị Invalidation Syntax (`syntax_ok: false`)

### Vấn đề
Khi file đích là Python nhưng nội dung chỉnh sửa lại nằm trong chuỗi multiline JavaScript (`FOLLOW_DETAIL_MODAL_JS = """..."""`), Sol Repair thường sinh patch chứa cú pháp JavaScript thuần, khiến trình kiểm tra cú pháp Python (`py_compile` / AST) báo lỗi `syntax_ok: false` và `SyntaxError`.

### Điều kiện Fallback Worker Hợp Lệ
Theo quy tắc First-Responder Monopoly:
> *CHỈ fallback dispatch Worker khi: sol_repair.py exit != 0 / crash / timeout, hoặc valid=false, hoặc numstat > 30 dòng, hoặc patch của Sol làm fail focused test.*

Trường hợp `syntax_ok: false` trên toàn bộ patch proposal là căn cứ pháp lý rõ ràng để **dừng áp dụng proposal của Sol Repair** và chuyển giao ngay cho **Worker (`claude_worker.py --role worker`)** xử lý.

---

## 4. Bẫy CLI Argument Quoting Trên Windows Cho `claude_worker.py`

Khi gọi `claude_worker.py` từ bash trên Windows:
- **CẤM:** Truyền file prompt qua subshell `$(< prompt.txt)` nếu file chứa dấu nháy kép (`"`), backticks (`` ` ``) hoặc nhiều dòng. Git Bash sẽ mở rộng chuỗi và làm gãy tokenization, gây lỗi:
  `'\", \"' is not recognized as an internal or external command`.
- **ĐÚNG:** Truyền prompt trực tiếp dạng chuỗi đơn dòng ngắn gọn, cô đọng:
  ```bash
  python D:/Taadaa/tools/claude_worker.py "In dashboard/follow_detail_component.py change label 'Chưa từng (sạch)' to 'Chưa ghi nhận'. In tests update assertion and add XSS test." --role worker --file "dashboard/follow_detail_component.py" --workdir "D:/Taadaa/tools"
  ```
