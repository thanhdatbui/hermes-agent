# TikTok 2FA Write-Through Retry & Closeout Gate Discipline (15/10/2026)

## 1. User Invariant: Write-Through Ngay Lập Tức, CẤM Ngâm Secret Chờ Ca Sau
- **Chỉ thị dứt khoát từ User:** Khi tài khoản đã bật 2FA thành công trên TikTok, secret BẮT BUỘC phải được ghi ngay bằng mọi giá vào file Excel (`taikhoan_dat_v2_updated .xlsx`).
- **Hành vi cấm:** Tuyệt đối không được chấp nhận thất bại do nghẽn lock tạm thời rồi để secret nằm ngâm trong local journal chờ sang các phiên kế tiếp.
- **Kiến trúc giải quyết 2 tầng:**
  1. *Tầng 1 (In-Place Retry trong `_write_cell`):* Bọc lệnh ghi `single_writer_workbook_update` bằng vòng lặp thử lại 5 lần kèm exponential backoff + jitter ngẫu nhiên (`random.uniform(1.5, 4.0) * (attempt + 1)`).
  2. *Tầng 2 (Post-Batch Journal Drain trong `run_batch_live_2fa.py`):* Ở cuối mỗi batch, tự động kích hoạt `recover_journal_2fa_to_excel.py --apply` để quét gom và xả toàn bộ journal `authenticator_confirmed` vào file Excel trong đúng 1 nhịp mở/ghi duy nhất.

---

## 2. Tiêu Chuẩn Thẩm Định Sol Reviewer (Closeout Gate Rubric) Cho Vòng Lặp Retry
Khi áp dụng vòng lặp retry cho các thao tác I/O hoặc khóa dữ liệu (file lock), Reviewer AI (`closeout_gate.py`) bắt buộc các điều kiện sau để đạt điểm `>= 85/100`:
1. **Phân loại lỗi chính xác (Explicit Error Classification):**
   - Chỉ retry đối với các lỗi transient thực sự: `"TIMEOUT"`, `"CROSS_HOST"`.
   - **CẤM** retry trên `"REPLACE"` nếu hàm bên dưới đã có cơ chế replace retry (tránh cấp số nhân số lần thử, ví dụ 5 x 8 = 40 lần gây vỡ unit test `test_replace_failure_is_reported_and_original_unchanged`).
   - Lỗi non-transient (mismatch identity, missing header, invalid format) bắt buộc phải `raise` ngay lập tức mà không retry.
2. **Bắt buộc Structured Telemetry Logging:**
   - Mỗi lần retry phải có log telemetry rõ ràng:
     ```python
     print(f"[telemetry:workbook-lock-retry] attempt={_i+1} err={_e}", flush=True)
     ```
   - Không được dùng one-liner im lặng (`except WorkbookError: continue`) vì vi phạm nguyên tắc quan sát (observability) trong production farm.
3. **Bắt buộc Unit Test Coverage cho Logic Retry Mới:**
   - Phải có test case giả lập (mock) lỗi transient lock để chứng minh:
     * Retry thành công sau N lần transient failure (`test_transient_lock_timeout_retries_and_succeeds`).
     * Exhaust 5 lần thì raise đúng ngoại lệ `WorkbookError`.
     * Non-transient error raise ngay lần đầu không qua `sleep_func`.
4. **Nhất quán API Surface:**
   - Nếu hàm nội bộ (như `_write_cell`) được import sang test file để mock dependencies, cần khai báo vào `__all__` của module để tránh warning API surface không nhất quán.

---

## 3. Cạm Bẫy CRLF vs LF trên Windows Làm Bùng Nổ Kích Thước Diff
- **Hiện tượng:** Chạy `closeout_gate.py` bị Fail-Fast ngay từ bước trích xuất diff:
  ```text
  GATE-FAIL(diff-too-large): targeted diff quá lớn (54950 > 30000 bytes).
  Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.
  ```
- **Nguyên nhân:** Khi worker hoặc script chỉnh sửa file trên Windows git-bash, file bị chuyển đổi ký tự xuống dòng từ LF (`\n`) sang CRLF (`\r\n`). Khi so sánh với commit gốc (dùng LF), git diff coi toàn bộ file (580 dòng) bị xóa và viết lại toàn bộ.
- **Cách xử lý chuẩn:**
  * Giữ nguyên byte xuống dòng `\n` của file nguồn khi dùng tool patch/write.
  * Trước khi gọi closeout gate, luôn kiểm tra `git diff --numstat`. Nếu thấy số dòng nhảy vọt tương đương tổng số dòng trong file (`589 583`), kiểm tra ngay tỷ lệ CRLF/LF bằng Python để chuẩn hóa về LF trước khi review.

---

## 4. Xử Lý Khi Reviewer (:20129) Bị Timeout Trong Closeout Gate
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
