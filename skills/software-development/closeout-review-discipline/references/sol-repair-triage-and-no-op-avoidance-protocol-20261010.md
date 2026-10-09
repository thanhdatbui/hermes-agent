# Sol Repair First-Responder Triage & Chống Bẫy No-Op Validation (10/10/2026)

Tài liệu đúc kết từ sự cố điều phối Strike 1 & Strike 2 trong quy trình Closeout Gate ngày 10/10/2026.

---

## 1. Bản chất điểm nghẽn kiến trúc

Theo `HERMES_SUBAGENT_RULES.md`, khi Closeout Gate trả về `REJECTED` (< 85 điểm):
- **Strike 1 & 2 Remediation:** BẮT BUỘC Sol High (`python D:/Taadaa/tools/sol_repair.py` qua `:20129`) ĐỘC QUYỀN tạo patch proposal O(1) đầu tiên (First-Responder Monopoly). Coordinator áp dụng và hậu kiểm `git diff --numstat <= 30 dòng`.
- **Điều kiện Fallback Worker:** CHỈ fallback dispatch Worker khi `sol_repair.py` exit != 0, crash, `valid=false`, `numstat > 30 dòng`, hoặc làm fail focused test.

### Mâu thuẫn cố hữu giữa Reviewer và Sol Repair:
1. **Auditor Bias của Reviewer:**
   - Model khi đóng vai Reviewer thường lý tưởng hóa và đưa ra các nhận xét định tính mang tầm vĩ mô: đòi hỏi framework metrics/alerting, đòi abstraction layer (`FarmConfig`), đòi hỏi kiểm thử trên thiết bị thật / ADB live...
2. **Chiếc áo giáp hẹp của Sol Repair:**
   - Khi làm thợ vá, Sol High bị gông cứng trong trần O(1): `numstat <= 30 dòng`, cấm can thiệp vật lý/ADB, cấm refactor lan man.
3. **Hai bẫy thất bại khi Coordinator copy nguyên văn findings thô:**
   - **Bẫy vỡ trần 30 dòng (Strike 1):** Sol Repair cố làm hài lòng mọi đòi hỏi vĩ mô ➔ sinh patch 153 dòng ➔ vi phạm ngân sách O(1).
   - **Bẫy No-Op Patch (Strike 2):** Sol Repair bị ép xử lý finding định tính không thể làm offline (đòi test farm thật) để đủ checklist `addressed_findings` ➔ sinh patch rỗng (`old_snippet == new_snippet`) ➔ bị chốt chặn AST của `sol_repair.py` chặn đứng:
     ```python
     elif old_snip == new_snip:
         syntax_ok = False
         syntax_err = "no-op patch rejected (old_snippet is identical to new_snippet)"
         overall_valid = False
     ```
     Dẫn đến proposal validation fail và thoát `exit code 1`.

---

## 2. Quy trình Triage bắt buộc cho Coordinator trước khi gọi Sol Repair

Tuyệt đối CẤM Coordinator copy thô 100% `key_findings` của Reviewer ném vào `scorecard.json` cho `sol_repair.py`. Coordinator BẮT BUỘC phải thực hiện **4 bước lọc (Triage)**:

### Bước 1: Loại bỏ Finding đòi hỏi thiết bị thật (Physical / Hardware Demands)
- Bất kỳ finding nào đòi hỏi: *"chạy thử trên máy thật"*, *"test ADB trực tiếp"*, *"xác minh trên phone farm live"* ➔ **LOẠI BỎ NGAY KHỎI SCORECARD SOL REPAIR**.
- *Lý do:* Closeout Gate và L2 Surgery bắt buộc chạy mocked/offline. Ép Sol sửa phần này chắc chắn gây ra no-op patch rỗng.

### Bước 2: Loại bỏ Finding kiến trúc vĩ mô (Macro Architecture)
- Các đề xuất như: *"cần tạo abstraction layer"*, *"cần cấu hình dynamic cluster injection"*, *"thiếu framework metrics chuyên biệt"* ➔ **LOẠI BỎ**.
- *Lý do:* Bản vá O(1) có ngân sách cứng `<= 30 dòng`, không thể và không được phép giải quyết tái cấu trúc hệ thống.

### Bước 3: Cô lập đúng 1-2 Actionable Code Defects (Khuyết tật logic cụ thể)
- Chỉ giữ lại các finding chỉ rõ lỗi sai logic kỹ thuật cụ thể có thể sửa trong 5-15 dòng, ví dụ:
  - `main()` luôn return 0 kể cả khi runner thất bại.
  - Sai sót cú pháp, thiếu biến, unhandled exception, timeout subprocess.
- Đặt finding này làm mục tiêu duy nhất cho Sol Repair. Khi chỉ nhận 1 finding kỹ thuật rõ ràng, Sol High sẽ sinh ra đúng 1 patch duy nhất chuẩn xác < 15 dòng.

### Bước 4: Kích hoạt Fallback Worker đúng lúc
- Nếu sau khi lọc, toàn bộ findings đều là định tính/kiến trúc: Không cố gọi Sol Repair để bị no-op.
- Nếu `sol_repair.py` exit code 1 (validation fail) hoặc patch sinh ra có `numstat > 30`:
  - Lập tức kích hoạt điều kiện **Fallback Worker** theo đúng `HERMES_SUBAGENT_RULES.md`.
  - Dispatch Worker (`delegate_task`) với Patch Contract thu hẹp để Worker sửa code trực tiếp và kiểm chứng qua focused unit test.
