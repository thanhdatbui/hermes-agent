# Claude Reviewer Approved: gate_common Fail-Closed Validation & ASCII Token Security (2026-10-18)

## 1. Bối Cảnh Lịch Sử & Kiểm Duyệt Độc Lập
- Sau khi đạt đồng thuận kiến trúc 3 bên giữa Coordinator, Sol Advisor (:20129) và Claude Planner, hệ thống bước vào giai đoạn kiểm duyệt độc lập (Independent Review) bởi Claude Sonnet 5.5 CLI (`claude_worker.py --role reviewer`).
- Claude Reviewer đã kiên quyết từ chối phê duyệt "chay" dựa trên văn bản tóm tắt (Reviewer Verdict: REJECTED evidence-insufficient) và phát hiện ra **2 lỗ hổng logic bảo mật thực tế** trong bản cài đặt ban đầu của `gate_common.py`.

## 2. Hai Lỗ Hổng Blockers & Cách Khắc Phục Triệt Để

### Blocker 1: Fail-Open Khi `grace_evidence=None`
- **Lỗi:** Trong logic ban đầu, nếu điểm nằm trong dải Grace (80–84) nhưng caller không truyền `grace_evidence` (`grace_evidence=None`), hàm `evaluate()` tự động bỏ qua việc kiểm tra diff và test, dẫn đến cấp `CONDITIONAL_PASS` trái phép!
- **Khắc phục Fail-Closed:**
  ```python
  if score >= policy["grace_threshold"]:
      if _grace_ok(grace_evidence, policy["budget"]):
          return _result(COND, "grace", "grace_approved")
      return _result(FAIL, None, "grace_conditions_unmet")
  ```
  Hàm `_grace_ok()` bắt buộc `grace_evidence` phải là `dict` hợp lệ, có `tests_passed is True`, `diff_files <= max_files` và `diff_lines <= max_lines`. Mọi trường hợp `grace_evidence=None` đều bị ném về `FAIL`.
- **Test bảo vệ:** `test_evaluate_grace_without_evidence_is_rejected PASSED`.

### Blocker 2: Lỗ Hổng Non-ASCII Token Gây Unhandled Exception
- **Lỗi:** Nếu token chứa ký tự lạ ngoài ASCII (ví dụ `é.abc`), hàm `_sign()` khi gọi `body.encode("ascii")` sẽ ném `UnicodeEncodeError`, hoặc `hmac.compare_digest()` ném `TypeError`. Trong CLI `main()`, ngoại lệ này không được bắt, khiến process crash với exit code 1 thay vì trả mã lỗi toàn vẹn 20 theo chuẩn.
- **Khắc phục:**
  ```python
  if not sep or not body or not body.isascii() or not sig.isascii():
      return False, "malformed_token"
  try:
      signature_ok = hmac.compare_digest(sig, _sign(_key(gate_dir), body))
  except (TypeError, UnicodeError):
      return False, "malformed_token"
  ```
- **Test bảo vệ:** 
  - `test_verify_rejects_non_ascii_token[\xe9.abc] PASSED`
  - `test_verify_rejects_non_ascii_token[abc.\xe9] PASSED`

## 3. Bộ Test Chuẩn Hóa 33/33 Kịch Bản Đối Kháng (Adversarial Coverage)
1. **Kiểm tra biên điểm số:** 79 (FAIL), 80-84 có evidence (COND/grace), 80-84 không evidence (FAIL), 85+ (PASS/strict).
2. **Loại trừ giá trị bất thường:** Điểm âm (-1), điểm > 100 (101), số thực (85.0), boolean (True), chuỗi ('90'), None $\rightarrow$ 100% trả về `FAIL ('invalid_score')`.
3. **Biên ngân sách Grace inclusive:** 2 files & 80 lines (PASS); 3 files hoặc 81 lines (FAIL).
4. **Bảo vệ toàn vẹn Token HMAC:**
   - Đổi `approval_tier` từ `grace` lên `strict` $\rightarrow$ Trả về `verdict_invalid`.
   - Token giả mạo chữ ký $\rightarrow$ Trả về `bad_signature`.
   - Token hết hạn đúng khoảnh khắc `now == exp` $\rightarrow$ Trả về `expired`.
   - Khác commit/change_id $\rightarrow$ Trả về `change_mismatch`.
5. **Giao diện CLI Exit Codes:**
   - Exit `0`: Token hợp lệ và khớp commit HEAD.
   - Exit `10`: Bị từ chối (head mismatch, expired, thiếu evidence).
   - Exit `20`: Lỗi toàn vẹn (tampered token, malformed signature).

## 4. Phán Quyết Nghiệm Thu
Claude Sonnet 5.5 Reviewer chính thức cấp: **Reviewer Verdict: APPROVED** sau khi toàn bộ 33 unit tests pass 100% và cơ chế Fail-Closed được chứng minh bằng thực nghiệm.
