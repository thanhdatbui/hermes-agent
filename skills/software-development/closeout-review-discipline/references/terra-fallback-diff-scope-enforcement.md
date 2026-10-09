# Khắc phục lỗ hổng Fallback sang Terra Codex cho phép gửi diff không giới hạn (Diff Scope Enforcement)

## 1. Bối cảnh & Nguyên nhân cốt lõi sự cố
Trong thiết kế cũ của hệ thống Closeout Gate:
- Model primary `review` trỏ vào **Sol Web (ChatGPT-Web pool)** có trần payload ~24KB - 37KB để tránh lỗi HTTP 413.
- Khi Sol Web quá tải hoặc diff vượt ngưỡng, hệ thống kích hoạt fallback sang **Terra Codex (`cx/gpt-5.6-terra-high`)**.
- Luật cũ định nghĩa sai lầm: *"Terra full-context contract (Gửi nặng thoải mái, trần an toàn 4 MiB)"*.
- **Hậu quả thực tế (Sự cố chiều 05/10/2026):**
  - Khi Gemini cạn quota, hệ thống chuyển sang Luna. Luna bôi lan man +612 dòng code, mock test và phòng thủ đồ sộ.
  - Diff phình to từ 20KB lên 71KB -> 92KB.
  - Vượt trần Sol Web, gate tự động fallback sang Terra Codex và mang theo **toàn bộ 92KB diff rác của cả working tree**.
  - Terra Codex nhận diff khổng lồ, xử lý chậm hàng phút và review rất khắt khe, liên tục REJECT (57–77đ).
  - Kết hợp với quy chế cũ *"No-cap remediation loop"*, hệ thống quay vòng 11 lần, làm tê liệt chốt phiên suốt hơn nửa ngày.

## 2. Chỉ thị dứt điểm từ User (Invariant `INV-4`)
User ra lệnh sửa triệt để:
> *"Sửa cái vụ fallback reviewer sang terra codex đc phép gửi k giới hạn diff đi. Thì dù có k qua sol cx bị ép gửi mỗi diff scope!"*

### Quy tắc bất biến mới:
1. **Dù có fallback sang Terra Codex hay bất kỳ model nào, BẮT BUỘC ép gửi duy nhất diff scope mục tiêu (`target_files` / candidate scope O(1) <= 30 dòng).**
2. **CẤM TUYỆT ĐỐI gửi unconstrained diff hoặc quét rác working tree của cả repo sang Terra.**
3. Kể cả khi model có context window 128k–200k tokens và safety ceiling 4 MiB, **Closeout Gate ở tầng local vẫn cưỡng chế trần diff tối đa 30.000 Bytes** (`MAX_DIFF_BYTES_GATE = 30_000`, hoàn toàn nằm trọn trong ngưỡng an toàn 37KB của `sol_payload_guard`). Nếu thợ bôi diff vượt quá 30KB, gate văng ngay **Exit code 3 (`DIFF_TOO_LARGE`)** trong 0.1s để báo Coordinator phân rã task, cấm cửa gửi lên reviewer.

## 3. Triển khai kỹ thuật trong hệ thống

### A. Cập nhật `TIERED_WORKFLOW.md`
- **Invariant `INV-4`:**
  ```markdown
  - `INV-4`: Dù fallback sang Terra exact model `cx/gpt-5.6-terra-high` (với safety ceiling 4 MiB), reviewer request BẮT BUỘC bị ép chỉ gửi duy nhất diff scope mục tiêu (`target_files` / candidate diff O(1) <= 30 dòng), CẤM TUYỆT ĐỐI gửi unconstrained diff hoặc dirty repo rác; a request to reverse INV-3/INV-4 is `REVIEW_CONTRACT_CONFLICT`.
  ```
- **Bảng vai trò (Roles):**
  ```markdown
  | Terra exact model `cx/gpt-5.6-terra-high` | Exact fallback only when Sol Web is unavailable, never primary; bắt buộc ép gửi duy nhất diff scope mục tiêu (--files O(1)), cấm gửi unconstrained diff; safety ceiling 4 MiB |
  ```

### B. Cưỡng chế trong `closeout_gate.py`
- `MAX_DIFF_BYTES_GATE = 30_000` được đặt làm hằng số cứng toàn cục cho `extract_diff`. Bất kể `--model` được truyền là `review`, `cx/gpt-5.6-terra-high`, hay model nào khác, trần 30KB luôn được áp dụng ngay tại bước trích xuất diff.
- Khi diff vượt 30KB:
  ```python
  if len(raw_diff_bytes) > effective_max:
      return DiffResult(
          success=False,
          diff_text="",
          staged_files=staged_files,
          error=f"[Gate Fail-Fast: DIFF_TOO_LARGE] Diff quá lớn ({len(raw_diff_bytes)} > {effective_max} bytes). "
                f"Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.",
      )
  ```
  Và tại `main()`: văng ngay `sys.exit(3)` để phân biệt với lỗi git thông thường (exit 1), ngăn chặn vòng lặp remediation mù quáng.
- Thêm cờ `--files` / `--target-file` cô lập scope: chỉ trích xuất diff của các file được phân công (`targeted_candidate`), bỏ qua hoàn toàn các file dirty khác của repo.

### C. Kiểm chứng & Kết quả Thực tế
- **Test suite:** 33 tests trong `test_closeout_binding_tamper.py`, `test_tiered_workflow_policy.py`, `test_cage_gate.py` đều pass 100%.
- **Chạy Closeout Gate thực tế:** Đạt **Verdict: APPROVED, Score: 86/100, Exit Code 0**, commit `cb8613f` và push thành công lên GitHub remote `main`.
