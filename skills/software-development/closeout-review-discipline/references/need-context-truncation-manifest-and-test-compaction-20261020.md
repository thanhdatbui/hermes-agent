# NEED_CONTEXT Truncation Manifest Trap & Test Suite Compaction in Closeout Gate

## Bối cảnh Hiện Trường (2026-10-20)
Khi triển khai tính năng hoặc remediate theo Closeout Gate qua nhiều vòng (Vòng 1 -> Vòng 2 -> Vòng 3), số lượng test case tăng nhanh từ 15 lên 37 rồi 45 tests. Tổng dung lượng diff giữa file triển khai và file test tăng lên 31.643 chars (~550 dòng diff).

Mặc dù toàn bộ 45/45 tests pass 100% trong 11.2 giây, `closeout_gate.py` liên tục thất bại với phán quyết:
```text
============================================================
  CLOSEOUT GATE — REVIEW SUMMARY
============================================================
  Verdict : NEED_CONTEXT
  Status  : ❌  FAIL
============================================================

── Model Response ──────────────────────────────────────────
NEED_CONTEXT:tests/test_xiaowei_idle_auto_close_watchdog.py
────────────────────────────────────────────────────────────
```
Sau 3 lần liên tiếp, Gate kích hoạt cờ `[REVIEWER_HANDOFF_TRIGGERED]`.

---

## Nguyên Nhân Gốc Rễ (Root Cause)
1. Trong `D:/Taadaa/tools/sol_payload_guard.py`, trần payload gửi sang Sol High (:20129) được khống chế bởi `SOL_TARGET_BYTES` (~36.000 bytes) và phân bổ ngân sách diff:
   ```python
   def format_manifest(diff_digest=None, log_digest=None, sent_bytes=0, extra=""):
       ...
       return (
           f"[TRUNCATION_MANIFEST]\n"
           f"level={level_str} total_raw_bytes={raw_b} sent_bytes={sent_bytes}\n"
           f"diff_sha={diff_sha} log_sha={log_sha}\n"
           f"omitted_details={omitted_str}\n"
           f"{extra_str}"
           f"NOTE: Phần bị lược KHÔNG được coi là đã review. Nếu cần xem để kết luận, trả về NEED_CONTEXT:<path>.\n\n"
       )
   ```
2. Khi candidate diff vượt quá ngân sách chia sẻ (~20KB-24KB), `focus_diff()` sẽ cắt bỏ một số hunks của file test (`omitted_details=hunks elided`).
3. Dòng nhắc hệ thống trong `[TRUNCATION_MANIFEST]` yêu cầu: *"Nếu cần xem để kết luận, trả về NEED_CONTEXT:<path>"*.
4. Model Sol High trên OmniRoute thấy diff bị cắt cụt, tuân thủ đúng chỉ thị và trả về `NEED_CONTEXT:tests/test_...`.
5. `closeout_gate.py` bắt được chuỗi `NEED_CONTEXT:` và lập tức fail-closed với Verdict `NEED_CONTEXT`.

---

## Quy Trình Khắc Phục (Actionable Remediation Protocol)
1. **Tuyệt đối không viết thêm test lẻ tẻ:**
   Việc viết thêm hàm test mới chỉ làm diff phình to hơn và khiến truncation trầm trọng hơn.
2. **Gom cụm và cô đọng test suite (Test Suite Compaction):**
   - Chuyển các hàm test có cấu trúc giống nhau thành `@pytest.mark.parametrize`.
   - Viết các test helper ngắn gọn (1-2 dòng) để mock environment và clock.
   - Giữ nguyên toàn bộ các assertion logic quan trọng, nhưng loại bỏ code dàn trải lặp lại.
3. **Mục tiêu Diff Budget:**
   - Đưa tổng dung lượng diff của cả file logic lẫn file test về **<= 18.000 characters** (~300 dòng diff).
   - Khi diff nằm gọn trong ngân sách, `sol_payload_guard` gửi trọn vẹn 100% diff mà không chèn `[TRUNCATION_MANIFEST]`.
   - Sol High đọc được đầy đủ mã nguồn và bộ test, cho điểm thực chất mà không bị kẹt `NEED_CONTEXT`.
