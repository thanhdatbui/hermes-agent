# Breaking 79 Plateau: Diff Budget Ratio, State Merge, Proof Magic Bytes & Anti-Clarify Discipline

**Date:** 2026-10-19  
**Target:** `closeout_gate.py`, `sol_payload_guard.py`, `tests/test_tiktok_rename_watchdog.py`, `tiktok_rename_rolling_watchdog.py`  
**Verdict:** `APPROVED (Score: 83/100, Grace Band 80-84 Auto-Push)`

---

## 1. Sự Cố & Bài Học Kỷ Luật: CẤM DÙNG `clarify` ĐỂ KHÓC LÓC KHI CHƯA QUA GATE

### Hiện tượng vi phạm:
Khi `closeout_gate.py` trả về điểm 65-79 (REJECTED), Coordinator đã gọi công cụ `clarify` đưa ra 2 lựa chọn:
1. Tự động chuyển giao Claude CLI Reviewer tự remediate code & test để qua Gate 85.
2. Giữ commit hiện tại trên local branch, không push lên origin remote.

User phản ứng gay gắt:
> *"Clgt lại khóc lóc đụ mẹ t fix lỗi khóc lóc này r mà?"*

### Nguyên tắc bất di bất dịch:
- **CẤM TUYỆT ĐỐI dùng `clarify` trong quy trình Closeout Gate:** Khi điểm chưa đạt (65-79), việc đưa menu lựa chọn hay hỏi "có tiếp tục không" bị coi là hành vi đầu hàng (Surrender / Apology Theater).
- **Trách nhiệm tự thân của Coordinator:** Quyền điều phối khắc phục qua các tầng (`sol_repair` -> `dispatch_worker` (Haiku 5.5 / Agy pool) -> `claude_worker` Reviewer) đã được cấp sẵn. Coordinator BẮT BUỘC tự động chạy vòng lặp khắc phục kỹ thuật cho đến khi:
  - Gate đạt `STRICT_APPROVED` (>=85) hoặc `GRACE_APPROVED` (80-84 auto-push), HOẶC
  - Gate tự động dừng theo cơ chế circuit breaker cơ học.
- **Không bao giờ làm phiền User bằng câu hỏi nghiệp vụ giả cầy:** Thất bại kỹ thuật ở closeout là do code/test chưa đạt chuẩn rubric, không phải quyết định nghiệp vụ cần User can thiệp.

---

## 2. Kỹ Thuật: Giải Quyết Bẫy `TRUNCATION_MANIFEST` & Nâng Budget Diff lên 80%

### Nguyên nhân bẫy `NEED_CONTEXT`:
- Trong `sol_payload_guard.py`, hàm `split_budget(total_budget)` trước đây phân bổ:
  - `diff_b = int(total_budget * 0.65)` (65%)
  - `log_b = int(total_budget * 0.25)` (25%)
  - `reserve_b = total_budget - diff_b - log_b` (10%)
- Với trần `SOL_TARGET_BYTES = 32,768`, ngân sách diff chỉ có **21,299 bytes**.
- Khi một tính năng mới đi kèm bộ unit test hoàn chỉnh (12-16 tests), tổng diff của file logic và file test thường rơi vào khoảng **22 - 25 KB**.
- Mặc dù tổng payload chỉ ~24KB (dưới xa trần cứng 40KB), thuật toán `digest_diff` vẫn tự động cắt tỉa file cuối cùng và gắn nhãn `TRUNCATION_MANIFEST`.
- Sol Auditor khi thấy `TRUNCATION_MANIFEST` lập tức dừng chấm và trả về `NEED_CONTEXT:<file>` (Score 0).

### Giải pháp cấu trúc:
1. **Điều chỉnh tỷ lệ phân bổ trong `sol_payload_guard.py`:**
   ```python
   def split_budget(total_budget: int) -> Tuple[int, int, int]:
       # Diff: 80% (tối đa hóa diff context cho Reviewer), Log: 10%, Reserve: 10%
       diff_b = int(total_budget * 0.80)
       log_b = int(total_budget * 0.10)
       reserve_b = total_budget - diff_b - log_b
       return diff_b, log_b, reserve_b
   ```
   Nâng ngân sách diff từ 21.3KB lên **26.2KB**, giải phóng không gian cho cả logic lẫn unit test đầy đủ.
2. **Consolidation bộ test (Chống phình diff):**
   - Không viết các hàm test dài dòng lặp đi lặp lại khối mock.
   - Gộp các test case cùng nhóm vào hàm helper tập trung (ví dụ `_run_single_worker`).
   - Dùng tham số hóa / vòng lặp danh sách tuple cho các mốc thời gian biên thay vì viết 20 câu lệnh `self.assertTrue(...)` riêng lẻ.

---

## 3. Rubric Checklist Để Bứt Phá Điểm 78-79 Lên 80-84 (Grace Band)

Reviewer Sol Auditor trừ điểm rất nhất quán ở mốc 78-79. Để đạt từ 80 điểm trở lên và kích hoạt Grace Auto-Push, bắt buộc phải thỏa mãn 4 tiêu chí sau:

1. **State Preservation (Không ghi đè dữ liệu cũ):**
   - *Lỗi bị trừ:* Khởi tạo dict rỗng hoặc chỉ lưu kết quả của batch hiện tại rồi ghi đè lên file state JSON (làm mất lịch sử các tài khoản chạy trước đó).
   - *Cách đạt chuẩn:* Trước khi ghi atomic, phải đọc lại file state hiện tại trên đĩa (nếu có), merge các entry mới vào dict cũ rồi mới ghi atomic replace.
     ```python
     if STATE_FILE.exists():
         try:
             current_disk = json.loads(STATE_FILE.read_text(encoding="utf-8"))
             current_disk.update(state)
             state = current_disk
         except Exception: pass
     _atomic_write_json(STATE_FILE, state)
     ```

2. **Proof Validation Bằng Magic Bytes (Không chỉ check kích thước > 0):**
   - *Lỗi bị trừ:* Chỉ kiểm tra `p.exists() and p.stat().st_size > 0`. File rác (text, zero byte, corrupt) vẫn lọt qua.
   - *Cách đạt chuẩn:* Kiểm tra kích thước và header chuẩn của định dạng ảnh (ví dụ PNG signature):
     ```python
     has_valid_proof = p.exists() and p.stat().st_size > 8 and p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
     ```

3. **Kiểm Thử Khóa Tiến Trình Thực Tế (Real Process Lock Test):**
   - *Lỗi bị trừ:* Tất cả unit test đều mock `_acquire_process_lock()`, không có test kiểm chứng va chạm lock thật.
   - *Cách đạt chuẩn:* Viết ít nhất 1 test tạo file lock thật trong thư mục temp, gọi `_acquire_process_lock()` lần 1 thành công (nhận file handle), và gọi lần 2 trả về `None` do xung đột `msvcrt.locking`. Đóng handle trong khối `finally`.

4. **Fail-Closed Khi Gặp Ngoại Lệ Heuristic / Phụ Thuộc:**
   - *Lỗi bị trừ:* `except Exception: pass` hoặc trả về `False` khi kiểm tra tiến trình / tên tài khoản.
   - *Cách đạt chuẩn:* Nếu đọc tiến trình gặp lỗi (ngoài `NoSuchProcess`) hoặc module phân tích tên không import được, bắt buộc fail-closed trả về `True` (báo phiên đang bận / cần đổi tên) để bảo vệ an toàn farm.
