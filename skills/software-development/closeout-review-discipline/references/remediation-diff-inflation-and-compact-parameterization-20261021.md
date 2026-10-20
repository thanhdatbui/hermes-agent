# Remediation Diff-Budget Contract & Anti-Inflation Lockdown (2026-10-21)

## 1. Hiện Tượng & Cơ Chế Sinh Lỗi (Diff Inflation Cascade)
Trong các vòng lặp khắc phục lỗi Closeout Gate (Strike 1 -> Strike 2 -> Strike 3):
1. Reviewer Sol High chấm trượt (70-77đ) và liệt kê 5-8 điểm rủi ro (schema validation, lock race condition, edge case Alt-Tab, process identity, rapid focus, psutil fallback...).
2. Worker nhận danh sách findings và tiến hành sửa code + viết test kiểm chứng.
3. **Bẫy nảy sinh:** Worker có xu hướng viết mỗi finding một hoặc nhiều test function độc lập (ví dụ `test_evaluate_idle_rejects_nan`, `test_evaluate_idle_rejects_inf`, `test_evaluate_idle_rejects_negative`, `test_lock_race_stale`, `test_lock_race_fresh`...).
4. Sau 2-3 lượt remediation, bộ test tăng vọt từ 25 tests lên 68 tests, rồi 106 tests; file test phình từ 250 dòng lên 750 dòng.
5. Tổng unified diff phình từ 15KB lên 31KB, rồi 44KB, rồi 56KB (>56,000 ký tự)!
6. `sol_payload_guard.py` có trần ngân sách `SOL_TARGET_BYTES = 36,000` (ngân sách diff 80% ~ 28.8KB). Khi diff vượt trần, hàm `digest_diff()` buộc phải lược bỏ hunks (ví dụ lược bỏ 28 hunks) và chèn:
   `[TRUNCATION_MANIFEST] ... NOTE: Phần bị lược KHÔNG được coi là đã review. Nếu cần xem để kết luận, trả về NEED_CONTEXT:<path>.`
7. Reviewer Sol High đọc thấy chỉ thị này lập tức tuân thủ nguyên tắc fail-closed, trả về `NEED_CONTEXT:<path>`, từ chối chấm điểm và Gate tiếp tục fail!
8. Càng sửa theo findings cũ thì diff càng to -> Truncation càng nặng -> Gate fail vĩnh viễn trong bế tắc.

---

## 2. Quy Tắc Bắt Buộc Khi Soạn Contract Cho Worker / Reviewer CLI

Khi Coordinator dispatch Worker (`dispatch_worker.py`) hoặc Reviewer CLI (`claude_worker.py --role reviewer`) để khắc phục lỗi Closeout Gate:

### A. Khống Chế Trần Diff Cứng (Hard Diff Ceiling <= 20,000 Chars)
- BẮT BUỘC quy định trong prompt worker:
  `TỔNG DIFF CẢ HAI FILE (CODE + TEST) BẮT BUỘC <= 20,000 KÝ TỰ (git diff | wc -c <= 20000).`
- Worker sau khi sửa code và test phải chạy `git diff <files> | wc -c` kiểm tra. Nếu > 20,000 ký tự thì BẮT BUỘC tự thu gọn (refactor compact) trước khi kết thúc lượt.

### B. Cấm Append Test Độc Lập — Ép Buộc Parametric Consolidation
- **CẤM TUYỆT ĐỐI** viết chuỗi test function con dài dòng lặp đi lặp lại boilerplate (mocking, setup, assert).
- **BẮT BUỘC** gom toàn bộ các biến thể dữ liệu và edge cases vào `@pytest.mark.parametrize`:
  ```python
  @pytest.mark.parametrize("payload,expected_err", [
      ({}, "SAMPLER_STATE_INVALID"),
      ({"heartbeat": "bad"}, "SAMPLER_STATE_INVALID"),
      ({"heartbeat": float("nan"), "last_active": 100}, "SAMPLER_STATE_INVALID"),
      ({"heartbeat": float("inf"), "last_active": 100}, "SAMPLER_STATE_INVALID"),
      ({"heartbeat": -1, "last_active": 100}, "SAMPLER_STATE_INVALID"),
      ({"heartbeat": 100, "last_active": -5}, "SAMPLER_STATE_INVALID"),
  ])
  def test_evaluate_idle_invalid_schema_compact(payload, expected_err):
      assert evaluate_idle(payload) == (None, expected_err)
  ```
- 1 test function ngắn 10 dòng có thể kiểm thử 6-10 findings của Reviewer, chỉ tốn ~500 ký tự diff thay vì 4,000 ký tự nếu viết 6 test riêng.

### C. Triệt Tiêu Dead Code và Trùng Lặp
- Khi tái cấu trúc logic, xóa bỏ các hàm helper cũ không còn dùng thay vì giữ lại cả code cũ lẫn code mới.
- Gom cụm các assert liên quan vào cùng một luồng test vòng đời (lifecycle test) thay vì chẻ nhỏ thành nhiều bài test chỉ assert 1 thuộc tính tĩnh.

---

## 3. Checklist Kiểm Tra Của Coordinator Trước Khi Chạy Lại Gate

1. `pytest <test_file> -q` pass 100% không có lỗi hay warning.
2. `git diff <target_files> | wc -c` < 25,000 ký tự (lý tưởng < 18,000 ký tự).
3. Đã chạy thử `python -c "import sol_payload_guard as spg; ..."` hoặc quan sát output gate: không xuất hiện `[TRUNCATION_MANIFEST] level=L4/L5` hay `elided hunks`.
4. Nếu phát hiện diff bắt đầu chớm > 30KB: DỪNG NGAY việc append thêm test, dispatch compact worker gọt tỉa test suite về dạng parameterized trước khi trigger Gate.
