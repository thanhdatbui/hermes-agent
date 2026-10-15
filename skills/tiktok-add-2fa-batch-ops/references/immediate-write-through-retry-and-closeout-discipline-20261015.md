# TikTok 2FA Write-Through Retry & Closeout Gate Discipline (15/10/2026)

## 1. User Invariant: Write-Through Ngay Lập Tức, CẤM Ngâm Secret Chờ Ca Sau
- **Chỉ thị dứt khoát từ User:** Khi tài khoản đã bật 2FA thành công trên TikTok, secret BẮT BUỘC phải được ghi ngay bằng mọi giá vào file Excel (`taikhoan_dat_v2_updated .xlsx`).
- **Hành vi cấm:** Tuyệt đối không được chấp nhận thất bại do nghẽn lock tạm thời rồi để secret nằm ngâm trong local journal chờ sang các phiên kế tiếp ("k mất dữ liệu sao chờ tới phiên tiếp theo lâu lắm").
- **Kiến trúc giải quyết 2 tầng:**
  1. *Tầng 1 (In-Place Retry trong `_write_cell`):* Bọc lệnh ghi `single_writer_workbook_update` bằng vòng lặp thử lại 5 lần kèm exponential backoff + jitter ngẫu nhiên (`sleep_func(min(random.uniform(1.5, 4.0) * (_i + 1), 12.0))`).
  2. *Tầng 2 (Post-Batch Journal Drain trong `run_batch_live_2fa.py`):* Ở cuối mỗi batch, tự động kích hoạt `recover_journal_2fa_to_excel.py --apply` để quét gom và xả toàn bộ journal `authenticator_confirmed` vào file Excel trong đúng 1 nhịp mở/ghi duy nhất.

---

## 2. Tiêu Chuẩn Thẩm Định Sol Reviewer (Closeout Gate Rubric) Cho Vòng Lặp Retry
Khi áp dụng vòng lặp retry cho các thao tác I/O hoặc khóa dữ liệu (file lock), Reviewer AI (`closeout_gate.py`) bắt buộc các điều kiện sau để đạt điểm cao (`>= 85/100`):
1. **Phân loại lỗi chính xác bằng frozenset hằng số:**
   - Khai báo hằng số `TRANSIENT_WORKBOOK_ERRORS = frozenset({...})` **TRƯỚC** hàm sử dụng nó (Sol Reviewer sẽ trừ điểm nặng nếu đặt sau hàm).
   - Chỉ retry đối với các lỗi transient thực sự: `"TIMEOUT"`, `"CROSS_HOST"`.
   - **CẤM** retry trên `"REPLACE"` nếu hàm bên dưới đã có cơ chế replace retry (tránh cấp số nhân số lần thử, ví dụ 5 x 8 = 40 lần gây vỡ unit test `test_replace_failure_is_reported_and_original_unchanged`).
   - Lỗi non-transient (mismatch identity, missing header, invalid format) bắt buộc phải `raise` ngay lập tức mà không retry.
2. **Quản lý biến ngoại lệ và Null-Guard:**
   - Phải gán `last_exc = _e` trong block `except WorkbookError as _e:`.
   - Cuối vòng lặp retry, **CẤM** hardcode `raise WorkbookError('BLOCKED_TIMEOUT_WORKBOOK_LOCK')` vì sẽ làm sai lệch loại lỗi nếu lỗi thực tế là `CROSS_HOST`.
   - Bắt buộc kiểm tra null-guard:
     ```python
     if last_exc is not None:
         logger.error(
             "workbook-lock-retry-exhausted attempts=5 err=%s workbook=%s",
             last_exc, path.name,
             extra={"event": "workbook-lock-retry-exhausted", "attempts": 5, "error": str(last_exc)},
         )
         raise last_exc
     raise WorkbookError("WORKBOOK_WRITE_RETRY_EXHAUSTED")
     ```
3. **Sleep Ceiling Bắt Buộc:**
   - Phải có trần sleep cứng: `sleep_func(min(random.uniform(1.5, 4.0) * (_i + 1), 12.0))` để tránh worst-case stall ~80s trên farm.
4. **Structured Observability (logging module thay vì print):**
   - Dùng `logger = logging.getLogger(__name__)` thay cho `print()` thô.
   - Cung cấp đủ 3 trạng thái quan sát trong vòng đời retry:
     * **Warning khi retry:** `logger.warning("workbook-lock-retry attempt=%d/%d ...", _i+1, 5, ...)`
     * **Info khi hồi phục thành công sau retry:** `if _i > 0: logger.info("workbook-lock-retry-succeeded ...")`
     * **Error khi kiệt sức retry (exhausted):** `logger.error("workbook-lock-retry-exhausted ...")`
5. **Bắt buộc Unit Test Coverage cho Logic Retry Mới:**
   - Phải có test case giả lập (mock) lỗi transient lock để chứng minh:
     * Retry thành công sau N lần transient failure (`test_transient_lock_timeout_retries_and_succeeds`).
     * Variant đa máy (`test_transient_lock_cross_host_variant_retries`).
     * Exhaust 5 lần thì raise đúng ngoại lệ `WorkbookError` (`attempts == 5`, `sleeps == 4`, kiểm tra bounds cho từng sleep).
     * Non-transient error raise ngay lần đầu không qua `sleep_func` (`attempts == 1`, `sleeps == 0`).
   - **Anti-pattern test bị trừ điểm:**
     * `patch.object(_write_cell.__globals__["_shared"], ...)` — test không được chọc vào `__globals__` của hàm nội bộ. Chuẩn hóa: `from core import workbook as wb_mod` rồi `patch.object(wb_mod._shared, "single_writer_workbook_update", ...)`.
     * `random.seed(...)` trong test: Nếu test kiểm tra khoảng ngẫu nhiên (bounds), cẩn thận tránh làm ô nhiễm global random state nếu chạy parallel.
     * Export `_write_cell` hoặc `TRANSIENT_WORKBOOK_ERRORS` vào `__all__` chỉ để phục vụ unit test là anti-pattern; giữ API surface sạch sẽ.

---

## 3. Phân Biệt Các Tầng Worker: Hermes Subagent vs External CLI (Claude Code)
Trong quá trình điều phối vá lỗi:
- **Hermes Subagent (`delegate_task`):**
  * Mô hình worker con chạy trong môi trường Hermes, dùng model OmniRoute (`ag-gemini-pool-3`, Luna High).
  * Chịu sự kiểm soát chặt chẽ của Guard: Scope Lock (chỉ được sửa file trong danh sách cho phép), Terminal Allowlist (chặn các lệnh shell tự do, chặn `py_compile`), Budget <= 15 calls.
  * Thích hợp cho các task sửa O(1) đã có Patch Contract rõ ràng.
- **External CLI (Claude Code CLI `claude -p`):**
  * Chạy qua terminal độc lập ngoài luồng kiểm soát của guard Hermes.
  * Tự do đọc/ghi file, tự chạy test và compile, không bị chặn bởi Scope Lock hay whitelist terminal.
  * **Chỉ kích hoạt khi:** Kích hoạt giao thức **Strike 3 Reviewer Hand-off** khi Closeout Gate bị reject liên tiếp 3 lần trên cùng scope_hash để tự remediate dứt điểm.

---

## 4. Cạm Bẫy CRLF vs LF trên Windows Làm Bùng Nổ Kích Thước Diff
- **Hiện tượng:** Chạy `closeout_gate.py` bị Fail-Fast ngay từ bước trích xuất diff:
  ```text
  GATE-FAIL(diff-too-large): targeted diff quá lớn (54950 > 30000 bytes).
  Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.
  ```
- **Nguyên nhân:** Khi worker hoặc script chỉnh sửa file trên Windows git-bash, file bị chuyển đổi ký tự xuống dòng từ LF (`\n`) sang CRLF (`\r\n`). Khi so sánh với commit gốc (dùng LF), git diff coi toàn bộ file (580 dòng) bị xóa và viết lại toàn bộ.
- **Cách xử lý chuẩn:**
  * Giữ nguyên byte xuống dòng `\n` của file nguồn khi dùng tool patch/write.
  * Trước khi gọi closeout gate, luôn kiểm tra `git diff --numstat`. Nếu thấy số dòng nhảy vọt tương đương tổng số dòng trong file (`589 583`), kiểm tra ngay tỷ lệ CRLF/LF bằng Python để chuẩn hóa về LF trước khi review.
  * Trong closeout gate, chỉ định rõ `--files` cụ thể để bỏ qua các file bị trôi CRLF chưa kịp chuẩn hóa.

---

## 5. Xử Lý Khi Reviewer (:20129) Bị Timeout Trong Closeout Gate
- **Hiện tượng:** Lệnh `python D:/Taadaa/tools/closeout_gate.py` treo 300s và exit code 1 với lỗi:
  `[OmniRouteClient] Request timed out on read: HTTPConnectionPool(host='localhost', port=20129): Read timed out.`
- **Nguyên nhân:** Model mặc định `--model review` trỏ về alias upstream bị nghẽn luồng suy luận hoặc kết nối proxy bị đơ.
- **Giải pháp xử lý:**
  1. Thăm dò các model dự phòng hoạt động nhanh trên `:20129`: `antigravity/claude-sonnet-4-6`, `ag-gemini-pool-3`, `antigravity/gemini-3-flash`.
  2. Bổ sung tham số model tường minh khi chạy gate:
     ```bash
     python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/tiktok-add-bao-mat-f2a" --base HEAD --files <files...> --model antigravity/claude-sonnet-4-6 --json-output
     ```
  3. Nếu `sol_repair.py` bị exit code 1 do model trong allowlist bị timeout, kích hoạt ngay **Fallback Worker** theo quy tắc Closeout Remediation để sửa theo findings của Reviewer.

---

## 6. Strike 3 → Claude CLI Handoff Protocol
Khi `closeout_gate.py` reject 3 lần liên tiếp trên cùng scope_hash:
- Gate phát tín hiệu: `[REVIEWER_HANDOFF_TRIGGERED: 3 consecutive rejections reached...]`
- CẢ Coordinator, Worker VÀ Sol Repair ĐỀU PHẢI DỪNG đoán/sửa.
- Chuyển giao ngay cho **Claude Code CLI** chạy print-mode (`claude -p`):
  ```bash
  claude -p "You are Claude acting as Reviewer-with-write-access after 3 consecutive Closeout Gate rejections: [exact findings]" \
    --allowedTools "Read,Edit,Write,Bash" \
    --dangerously-skip-permissions \
    --max-turns 20 \
    --output-format json \
    --workdir "D:/Taadaa/tiktok-add-bao-mat-f2a"
  ```
- Claude CLI có quyền ghi file và chạy test độc lập ngoài guard, sửa dứt điểm các điểm cấu trúc/anti-pattern mà Worker subagent hay lặp lại.
