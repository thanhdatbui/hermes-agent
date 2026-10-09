# Case Study 29: 78 -> 84 -> 86/100 (APPROVED) trong repo `Hermes` (`post_noon_chain_watchdog.py`) — Bẫy Commit Split Mù Source Diff, Breaking Parser Type Change, Xóa Test Lõm Coverage & Kỹ Thuật `SummaryResult` Dual-Interface

## 1. Bẫy Commit Split Mù Source Diff (78/100 REJECTED)
- **Hiện tượng:** Coordinator thực hiện sửa code nghiệp vụ ở commit 1 (`fix(watchdog)`), sau đó nhận ra test cần sửa nên sửa tiếp ở commit 2 (`test(watchdog)`). Khi chạy closeout gate:
  `python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/Hermes" --base HEAD~1`
  Reviewer chỉ nhìn thấy diff của commit 2 (chỉ có thay đổi file test, không có code nghiệp vụ).
- **Reviewer kết luận:** *"Diff chủ yếu thay đổi và loại bỏ test case; chưa có source code diff để xác minh logic runtime thực sự, nên không thể kết luận các thay đổi chức năng mới đã đúng ngoài phạm vi test hiện có."* (Chấm 78/100).
- **Khắc phục:**
  - Bắt buộc hợp nhất commit (`git reset --soft <base>` rồi commit lại 1 commit duy nhất) hoặc truyền `--base HEAD~N` bao trùm toàn bộ source diff.
  - Reviewer Sol Auditor bắt buộc phải nhìn thấy đồng thời cả source code implementation lẫn test code trong cùng một diff payload thì mới đánh giá được tính đúng đắn logic (`logic_correctness`) và chứng cứ kiểm thử (`test_evidence`).

---

## 2. Bẫy Breaking Change Khi Đổi Kiểu Trả Về Của Parser (84/100 REJECTED)
- **Hiện tượng:** Hàm `parse_summary_counts(...)` vốn trả về `tuple[int, int, int]` (`total, success, failed`). Để phục vụ yêu cầu tách bạch lỗi nền tảng vs lỗi script, hàm được sửa thành trả về `dict` chứa `failure_breakdown` và `skip_safe`.
- **Reviewer kết luận:** *"parse_summary_counts đổi kiểu trả về từ tuple sang dict nhưng diff chỉ chứng minh được consumer trong file hiện tại đã sửa; chưa có bằng chứng toàn bộ repository không còn caller phụ thuộc tuple cũ."* (Kẹt 84/100, thiếu đúng 1 điểm để đạt threshold 85).
- **Khắc phục triệt để bằng `SummaryResult` Dual-Interface Pattern:**
  Kế thừa `dict` và override `__iter__` trả về iterator của tuple `(total, success, failed)`:
  ```python
  class SummaryResult(dict):
      def __iter__(self):
          return iter((self.get("total", 0), self.get("success", 0), self.get("failed", 0)))
  ```
  - **Caller mới:** Đọc dạng dict: `res["failure_breakdown"]`, `res.get("skip_safe")`.
  - **Caller cũ:** Unpack dạng tuple bình thường: `tot, suc, fail = parse_summary_counts(...)`.
  - **Không làm vỡ bất kỳ consumer nào** trong toàn bộ ecosystem farm/cronjob.

---

## 3. Bẫy Decommission Helper Gây Nổ AttributeError & Xóa Test Gây Lõm Coverage
- **Hiện tượng:** Khi dừng tính năng reg ChatGPT trên S7 theo chỉ đạo của Sếp, nếu xóa hẳn hàm helper `parse_chatgpt_warmup_counts` và xóa 3 test case liên quan:
  1. Các test suite hoặc module khác còn mock hoặc import `watchdog.parse_chatgpt_warmup_counts` sẽ bị nổ `AttributeError`.
  2. Reviewer trừ điểm regression: *"Một số test cũ liên quan ChatGPT warmup đã bị xóa thay vì được thay thế bằng kiểm chứng tương đương, làm giảm khả năng phát hiện regression ở luồng này."*
- **Khắc phục:**
  1. **Giữ lại Stub Deprecated:**
     ```python
     def parse_chatgpt_warmup_counts(log_dir_hint: Path | None = None, min_mtime: float | None = None) -> tuple[int, int]:
         """Deprecated: ChatGPT registration on S7 has been disabled."""
         return 0, 0
     ```
  2. **Thay thế Test Thay Vì Xóa:** Thay vì xóa sạch test cũ, hãy chuyển đổi các test case đó thành kiểm chứng cho logic phân loại lỗi mới:
     - `test_gmail_report_formats_script_failure_when_success_is_zero`
     - `test_gmail_report_formats_safe_skip_and_mixed_breakdown`
     - `test_summary_result_backward_compatibility_and_stub`
  3. Duy trì hoặc tăng tổng số lượng unit tests (từ 8 lên 9 tests pass 100%).

---

## 4. Kỷ Luật Pre-Push Hook Với Multi-Repo Closeout
- Khi phiên làm việc chạm vào nhiều repo (ví dụ: `register gmail`, `GPM auto`, `Hermes`):
  - Hook `pre-push` ở các repo chuẩn farm kiểm tra log audit tại `D:/Taadaa/logs/gate_audit.jsonl` qua SHA256 chain.
  - Nếu commit ở repo nào chưa được chạy `closeout_gate.py` tương ứng của repo đó và nhận verdict `APPROVED` (Score >= 85), hook sẽ reject lệnh `git push` ngay lập tức:
    `❌ [BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — verdict=REJECTED score=...`
  - **Quy trình chuẩn:** 
    1. Chạy `closeout_gate.py` cho từng repo bị chỉnh sửa.
    2. Chỉ khi nhận được `Verdict: APPROVED (>= 85)` thì mới thực hiện `git push` lên remote của repo đó.
