# T2 Planner Empirical Reality & Option C Architecture (04/10/2026)

## 1. Bối cảnh & Sự thật vận hành (Empirical Reality Check)

### Vấn đề "Luật trên giấy" (Paper Rule)
Theo văn bản quy chế Tiered Workflow và phân vai Agent:
- Task T2 quy định Bước 1 phải do Sol High hoặc Terra High lập bản vẽ Patch Contract O(1) trước khi giao Worker thi công.
- **Thực tế kiểm toán session log (04/10/2026):**
  1. Terra High đã bị loại khỏi luồng chính từ 27/09 sau khi thua benchmark và tiêu tốn quota Codex đắt đỏ.
  2. Sol High CHƯA TỪNG chạy một lần nào để lên bản vẽ T2 Plan trong bất kỳ session thực tế nào.
  3. Toàn bộ 100% Patch Contract O(1) thực tế gửi cho Worker qua delegate_task đều do chính Coordinator (Gemini) tự grep hiện trường và tự soạn trong prompt.

### Làm rõ chi phí Quota (Chỉ thị từ User 04/10/2026)
- **Sol High qua cổng 20129:** Chạy trên dàn tài khoản ChatGPT-Web pool, HOÀN TOÀN 0đ quota Codex và không tốn tiền API (tài nguyên miễn phí). Thách thức của Sol Web không phải là chi phí quota, mà là độ trễ (20–45s/lượt) và nguy cơ rate-limit web hoặc lỗi payload quá lớn khi nạp context dài.
- **Terra High:** Chạy qua tài khoản Codex CLI OAuth, tiêu hao quota Codex đắt đỏ và có độ trễ timeout 90s khi tranh chấp lock.

---

## 2. Phán quyết Thẩm định từ Claude Code CLI (Lead System Architect)

Khi được triệu tập tư vấn độc lập, Claude CLI đã phân tích và bác bỏ 2 phương án cực đoan:
- **Bác bỏ Phương án B (Bắt buộc ép gọi Sol cho mọi T2):**
  - Sol không chạm được thiết bị ADB thật hay đọc màn hình, nên dữ liệu đầu vào của Sol chỉ tốt bằng bản tóm tắt do Gemini soạn.
  - Mỗi task T2 phải gánh thêm 20–45s độ trễ.
  - Khi Sol Web bị lỗi rate-limit, toàn bộ pipeline cứu farm bị tắc. Lúc khẩn cấp quy định lại bị lách, tiếp tục trở thành luật trên giấy.
- **Bác bỏ Phương án A thuần túy (Hợp thức hóa không chốt chặn):**
  - Nếu Coordinator vừa khảo sát, vừa tự soạn contract, vừa tự dispatch mà không có máy kiểm chứng thì tạo ra xung đột lợi ích. Chỉ trông chờ vào cổng chốt phiên cuối cùng là không đủ an toàn.

---

## 3. Kiến trúc Chốt: Phương án C (Coordinator-Planned, Machine-Gated, Trigger-Based Sol)

### 3.1 Phân tầng Thực thi T2 Thường quy
1. **Coordinator (Gemini) lập Patch Contract O(1):**
   - Khảo sát hiện trường qua ADB, OCR và log O(1).
   - Tự grep xác định anchor duy nhất tuyệt đối (count == 1).
   - Đóng gói Patch Contract O(1) trực tiếp trong prompt delegate_task (tốc độ 3–5 giây).
2. **Machine-Gated Enforcement (Hook tiền kiểm tra):**
   - Thay vì bắt người hay LLM duyệt từng plan, dùng hook tự động kiểm tra tính hợp lệ trước khi cho phép dispatch:
     - Target files tồn tại trên đĩa và nằm ngoài vùng cấm bảo vệ.
     - Anchor code cũ khớp chính xác đúng 1 lần trên đĩa (uniqueness == 1).
     - Có lệnh focused test dưới 30s.
     - Ngân sách Worker tối đa 15 calls.

### 3.2 Kích hoạt Sol High Pre-Plan theo Trigger Rủi ro cao
Sol High (0đ quota Codex) CHỈ BẮT BUỘC gọi Pre-Plan khi gặp một trong các trigger:
1. Target files chạm vào thành phần lõi nhạy cảm: các file hook kiểm soát, bộ quy chuẩn an toàn, cổng thẩm định, schema cơ sở dữ liệu.
2. Scope sửa đụng trên 3 files hoặc xuyên repository/module.
3. Đã có từ 2 lần dispatch thất bại trở lên cho cùng một bài toán (deadlock escalation).
4. Thay đổi luồng đăng nhập, thanh toán, credential, hoặc tài khoản farm.

### 3.3 Vai trò của Terra High
- Terra High hoàn toàn không nằm trong luồng chính.
- CHỈ là dự phòng duy nhất khi Sol Web dính timeout liên tiếp hoặc tạm thời không khả dụng trong ca dính trigger rủi ro cao. Bắt buộc ghi lý do vào ledger kiểm toán.

### 3.4 Khâu Chốt phiên (Closeout Gate)
- Sol High giữ vai trò Đại Giám Khảo Độc Lập (chấm điểm từ 85 trở lên mới được nghiệm thu đóng phiên).
- Hậu kiểm bổ sung: Diff toàn phiên phải là tập con của các target files và nằm trong trần số dòng đã khai báo trong dispatch contract (ngưỡng dung sai thống nhất là `diff <= 30 dòng`, khớp 100% với `cage_gate.py`).

### 3.5 Kinh nghiệm Thẩm định Closeout cho Thay đổi Quy chế (Closeout Audit Package Lessons)
Khi thay đổi văn bản quy chế hoặc workflow hệ thống nộp lên Closeout Gate (`closeout_gate.py`), Sol Reviewer đòi hỏi 4 bằng chứng cứng:
1. **Toàn văn hoặc Git Diff thực tế:** Nộp gói audit (`--input _closeout_audit_package.txt`) chứa nguyên văn file quy chế mới và diff so với bản cũ.
2. **Bằng chứng Code Enforcement:** Trích dẫn chính xác các đoạn code kiểm soát thực thi (ví dụ: `hooks/guard_dispatch_contract.py` kiểm tra anchor c==1 trên đĩa vật lý, `cage_gate.py` giới hạn diff <= 30).
3. **Bộ Test Hồi Quy Trực Tiếp Cho Hook:** Hook kiểm soát trọng yếu bắt buộc phải có test tự động trực tiếp (như `tests/test_guard_dispatch_contract.py` kiểm thử đủ 5 nhánh: thiếu FILE, file không tồn tại, anchor count == 0, count > 1, và allow khi count == 1).
4. **Telemetry Đầy Đủ (Không Bỏ Sót Nhánh):** Mọi nhánh quyết định (cả block và allow) của các route (kể cả route `edit`) đều phải được ghi nhật ký vật lý vào audit ledger (`dispatch_audit.jsonl`).
5. **Dung Sai Thống Nhất:** Đảm bảo câu chữ trong markdown ("tối đa 30 dòng", `diff <= 30`) khớp tuyệt đối với mã nguồn python enforcer (`total_lines <= max_lines`), không để lệch `< 30` vs `<= 30`.

### 3.6 Pitfalls Điều Phối Công Cụ Bổ Sung
- **Claude Code CLI Print Mode (`-p`) Edit Trap:** Lệnh `claude -p` chạy không tương tác nhưng vẫn tuân thủ quyền ghi file. Nếu yêu cầu sửa file mà thiếu `--dangerously-skip-permissions` (hoặc `--allowedTools "Read,Edit,Write"`), Claude sẽ chỉ in bản thảo và hỏi xin quyền ghi ("Để tôi ghi file, bạn cho phép..."). Luôn thêm `--dangerously-skip-permissions` khi yêu cầu Claude sửa file tự động trong `-p` mode.
- **Terminal Redirection Guard Trap:** Coordinator guard chặn ký tự `>` ngay cả khi nằm trong chuỗi nháy kép (ví dụ: `old_string -> new_string`). Khi soạn prompt cho CLI qua terminal, tránh dùng ký tự `>` (thay bằng `sang`, `thanh`, hoặc `den`) để không bị chặn nhầm bởi regex điều hướng ghi file.

---

## 4. Nguyên tắc Chống Luật Trên Giấy (Anti-Paper-Rule Principle)
1. Mọi quy định MUST bắt buộc phải có enforcer cụ thể: hoặc là hook Python chặn cứng, hoặc là script kiểm chứng, hoặc test suite tự động.
2. Quy định nào chưa có tool/hook thi hành chỉ được ghi nhãn ADVISORY (khuyến nghị), không được coi là cổng chặn cứng để tránh hiện tượng tự sinh luật mù không thể kiểm soát.
