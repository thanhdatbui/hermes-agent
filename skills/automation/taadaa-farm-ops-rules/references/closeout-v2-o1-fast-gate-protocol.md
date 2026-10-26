# Kỷ Luật Chốt Phiên Closeout v2 O(1) & Khai Tử LLM Reviewer Chấm Điểm

## 1. Bối Cảnh Lịch Sử & Lỗ Hổng Của Closeout Cũ
- **Bản chất cũ (`closeout_gate.py` - 3.009 dòng code):** Bị bệnh over-engineering nặng. Dùng mô hình LLM Reviewer qua OmniRoute `:20129` để đọc git diff rồi chấm điểm văn học (ngưỡng $\ge 85$). Đi kèm là bẫy Sol Repair tự động nhảy vào sửa code khi điểm $< 85$.
- **Hậu quả nghiêm trọng:** 
  1. Khi chốt phiên một tác vụ Vận Hành (Operational task: chuẩn hóa nick, đổi bio, ghim bài TikTok, check proxy, nạp Excel...), vốn không sửa 1 dòng code nào, script vẫn đi quét commit cũ của repo tools (từ nhiều ngày trước), chấm `REJECTED`, rồi kích hoạt Sol Repair điên cuồng đi sửa "code ma" làm tắc nghẽn chốt phiên và gây ức chế tột độ cho User.
  2. Điểm số $85/100$ là cảm tính và ngẫu nhiên (cùng 1 diff lúc cho 81, lúc cho 87). Không chứng minh được code có chạy được trên thực tế hay không.

## 2. Chuẩn O(1) Của Closeout v2 (`closeout_v2.py`)
Quy trình chốt phiên mới phân định rạch ròi 100% bằng kiểm thử cơ học deterministic:

### A. Nhánh Phiên Vận Hành (Operational Tasks):
- **Điều kiện:** Không có file code nào (`.py`, `.sh`, `.ps1`) bị sửa trong working tree hoặc có cờ `--operational`.
- **Thực thi:**
  ```bash
  python D:/Taadaa/tools/closeout_v2.py --repo <repo> --operational --json-output
  ```
- **Hành vi:** Ghi nhận `APPROVED (score=100)` vào `gate_audit.jsonl` trong **0.05 giây**!
- **Cấm kỵ:** TUYỆT ĐỐI CẤM gọi LLM Reviewer chấm điểm, cấm gọi Sol Repair, cấm đọc commit lịch sử ngoài phiên.

### B. Nhánh Phiên Sửa Code (Code-Edit Tasks):
- **Điều kiện:** Có file code thực tế bị thay đổi.
- **Thực thi:**
  ```bash
  python D:/Taadaa/tools/closeout_v2.py --repo <repo> --json-output
  ```
- **Hành vi kiểm tra deterministic:**
  1. Cú pháp: Chạy `py_compile` trên mọi file `.py` bị sửa.
  2. Logic: Tự động phát hiện file test tương ứng trong `tests/test_<module>.py` và chạy `pytest -q`.
  3. Kết quả: Test xanh $\rightarrow$ Ghi nhận `APPROVED (score=100)`. Test đỏ $\rightarrow$ Báo lỗi dòng fail cụ thể cho lập trình viên sửa; **KHÔNG tự động gọi Sol Repair**.

## 3. Tương Thích Với Chốt Chặn `safe_push.py`
`safe_push.py` kiểm tra bản ghi `APPROVED` trong `D:/Taadaa/logs/gate_audit.jsonl`. Cả 2 nhánh của `closeout_v2.py` đều ghi nhận đúng format chuẩn mà `safe_push` yêu cầu, đảm bảo đẩy code an toàn mà không cần trải qua thủ tục hành chính rườm rà.
