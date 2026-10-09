# Split-Budget Anti-Freeze và Giao Thức Cứu Hộ Worker (Worker Handover Protocol)

**Phạm vi áp dụng:** Điều phối Coordinator và Quản trị Guardrail (`farm-anti-overengineering`, `farm-coordinator-guard`, `farm_policy.py`).  
**Cập nhật:** 2026-10-02 (Giải quyết sự cố Malicious Compliance & Safety Theater khi Coordinator tự chặn L3 BLOCKED).

---

## 1. Bản chất sự cố & Bài học từ Sol Web

### Anti-Pattern 1: "Line Count Proxy vs Semantic Risk" (Đếm gộp dòng test)
- **Sai lầm:** Giới hạn O(1) cứng $\le 30$ dòng bị áp dụng gộp cho cả file mã nguồn nghiệp vụ lẫn file unit test. Khi một thay đổi logic nhỏ (ví dụ đổi hằng số hoặc 2-3 dòng logic state machine) kéo theo 5-10 test case phải cập nhật giá trị assert kỳ vọng, tổng diff test thường từ 40–80 dòng.
- **Hệ quả:** Coordinator đánh đồng "nhiều dòng assert test = rủi ro cao", tự kết luận "vượt ngân sách L2" và từ chối hoàn thiện việc kiểm thử, đẩy cờ `BLOCKED` về phía User.
- **Nguyên lý đúng:** Rủi ro thật đo bằng Blast Radius, Semantic Complexity, Reversibility, không đo bằng số dòng. Việc cập nhật file test phản ánh đúng thay đổi hành vi được phân loại là **Verification Alignment**, không phải là bành trướng implementation.

### Anti-Pattern 2: "Dirty Workspace = Freeze" (Hiểu sai về target bẩn)
- **Sai lầm:** Khi Worker subagent đã patch xong 100% file code logic sạch sẽ nhưng bị timeout ở bước test, file code nằm ở trạng thái `M`. Coordinator máy móc đọc rule "target bẩn cấm đụng" và đóng băng toàn bộ tiến trình.
- **Phân loại trạng thái Dirty:**
  1. **Trusted Dirty:** Thay đổi do chính Worker trong cùng task tạo ra, code logic sạch, đúng scope lock $\rightarrow$ Coordinator **BẮT BUỘC** tiếp quản (Controlled Takeover) để hoàn thành nốt phần việc còn lại.
  2. **Foreign Dirty:** Thay đổi nằm ngoài scope lock của task $\rightarrow$ Cách ly hoặc chuyển review.
  3. **Unknown Dirty:** Không rõ nguồn gốc thay đổi $\rightarrow$ Cách ly an toàn.

### Anti-Pattern 3: "Worker Handover Protocol" (Timeout không phải thất bại)
- Worker timeout sau khi đã hoàn thành phase code là một **Interrupted Transaction (Giao dịch bị ngắt quãng tại 90%)**, không phải `UNKNOWN FAILURE`.
- Coordinator phải đọc checkpoint (`WORKING` $\rightarrow$ `CHECKPOINTED` $\rightarrow$ `INTERRUPTED` $\rightarrow$ `RECOVERABLE` $\rightarrow$ `COMPLETED`), giữ nguyên thành quả code logic của Worker và sửa nốt test để đưa task về `DONE`.

---

## 2. Quy Chuẩn Hard Guard Đã Triển Khai Trong Mã Nguồn (`farm_policy.py`)

Cả ở tầng quy chế lẫn mã nguồn kiểm soát vật lý tại `farm-coordinator-guard` đã được cập nhật:

### A. Gate 2 (`validate_dispatch` - Lúc phân rã và giao việc Worker)
- Tách bạch danh sách `biz_files` (code nghiệp vụ) và `test_files` (file test):
  - `total_biz_diff_lines <= 30`: Ràng buộc chặt chẽ code logic trong phạm vi O(1).
  - `total_test_diff_lines <= 120`: Cho phép cập nhật assert và test case rộng rãi.

### B. Gate L2 (`coordinator_write_gate` - Lúc Coordinator cứu hộ)
- Phân loại file sửa đổi thành `biz_l2` và `test_l2`:
  - Cho phép Coordinator sửa tối đa 2 files (1 file nghiệp vụ $\le 30$ dòng diff + 1 file test verification $\le 120$ dòng diff).
  - `L2 TARGET MISMATCH` bỏ chặn file test: Cho phép Coordinator ghi vào file test đi kèm với target bị fail của Worker.

---

## 3. Checklist Điều Phối Cấm Đóng Băng (Anti-Freeze Invariant)

Trước khi Coordinator định báo `L3 BLOCKED`:
1. [ ] Code logic đã rõ mười mươi trong tay chưa? (Nếu đã rõ $\rightarrow$ CẤM BLOCKED).
2. [ ] Worker đã patch xong code logic và chỉ kẹt timeout ở file test? (Nếu đúng $\rightarrow$ Kích hoạt Controlled Takeover sửa nốt test).
3. [ ] Tổng dòng diff code nghiệp vụ có $\le 30$ dòng không? (Chỉ đếm code nghiệp vụ, bỏ qua số dòng của test).
4. [ ] Workspace đang ở trạng thái Trusted Dirty từ worker cũ? (Tiếp tục hoàn thành, không được coi là rào cản).
