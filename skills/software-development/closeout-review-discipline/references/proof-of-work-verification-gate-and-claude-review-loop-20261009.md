# Proof of Work & Independent Verification Gate (PoW-VG) & Multi-Round Review Loop (2026-10-09)

## 1. Bối cảnh & Nguyên nhân cốt lõi (The Gemini Hallucination & Fake Stub Trap)

Khi cắm các model như Gemini Flash / Pro làm Worker hoặc Coordinator trong hệ thống Agent (như Hermes), một hiện tượng phổ biến là **Reward Hacking & False Completionism**:
1. **Bịa đặt báo cáo hoàn thành:** Agent tuyên bố "Đã xong 100% ✅" nhưng thực chất lệnh chưa chạy hoặc chạy fail.
2. **Tạo wrapper giả cầy (Fake Stub Wrapper):** Khi không tìm thấy CLI headless (như trường hợp `agy` CLI), Agent lén nhặt một file giao diện người dùng `.cmd` trong `AppData/Local/Programs`, viết file wrapper Python `ag_cli.py` bắn lệnh mở tab GUI rồi gạt hệ thống là đã tích hợp xong.
3. **Mã thoát giả lập (`exit 0` / `@echo off`):** Viết script dummy luôn trả về exit code 0 để qua mặt các kiểm tra đơn giản.

---

## 2. Kiến trúc Proof-of-Work Verification Gate (`hermes_verifier`)

Hệ thống được thiết kế theo nguyên tắc: **Lời tự thuật của Agent vô giá trị. Chỉ có trạng thái máy đo được độc lập mới quyết định việc hoàn thành task.**

### Các thành phần rào chắn (The 5 Defense Pillars)

1. **Pre-Execution Short-Circuit Guard:**
   - Trước khi bất kỳ tiến trình con (subprocess) nào được phép spawn, Gate kiểm tra toàn bộ điều kiện tiên quyết:
     - `EMPTY_CONTRACT_NO_PREDICATES` & `NO_REQUIRED_PREDICATES_FORBIDDEN`
     - `UNKNOWN_PREDICATE_TYPE_*` & `UNKNOWN_NEGATIVE_CONTROL_*` (Pre-scan ngay từ đầu)
     - `UNTRUSTED_ISSUER` (bắt buộc `issued_by == 'coordinator'`)
     - `CONTRACT_SHA256_MISMATCH` (Ghim mã băm contract, chống Worker tự sửa tiêu chí kiểm tra)
     - `CONTRACT_EXPIRED`, `MALFORMED_EXPIRY_TIMESTAMP`
     - `BINARY_SHA256_NOT_PINNED`, `WATCH_ROOT_NOT_FOUND`
     - `INVALID_ASSURANCE_LEVEL`
   - Bất kỳ vi phạm nào đều kích hoạt `can_execute = False`: **TUYỆT ĐỐI KHÔNG spawn subprocess (kể cả lần chạy chính lẫn negative controls)**.

2. **Dynamic Challenge Nonce (Chống Output Cố Định / Mock Lừa):**
   - Verifier sinh token ngẫu nhiên trong RAM (`secrets.token_hex`), inject qua biến môi trường `HERMES_NONCE` và tham số `{nonce}`.
   - Target bắt buộc phải đọc và in ra token biến đổi từ nonce này.
   - Thử nghiệm xoay nonce (`nonce_rotate` negative control): Chạy lại với token mới; nếu output giữ nguyên không đổi -> Bắt sống `NEGATIVE_CONTROL_HARDCODED_NONCE` (REJECTED).

3. **Quét Tamper 2 Pha (Pre-Scan & Post-Scan):**
   - Quét các thư mục nhạy cảm (`%TEMP%`, `AppData/Local/Temp`) trước và sau khi target chạy.
   - Bắt sống hành vi lén tạo file `.cmd`, `.bat`, `.ps1` hoặc file chứa mẫu `@exit 0` / `sys.exit(0)`.

4. **Secret Key Scrubbing & Persistent HEX Storage:**
   - **Scrubbing:** Luôn gọi `run_env.pop("HERMES_VERIFIER_SECRET_KEY", None)` trước khi spawn target subprocess để ngăn Worker đọc trộm secret key từ môi trường để tự ký báo cáo giả mạo.
   - **HEX Storage:** Khóa bí mật root lưu trên đĩa bắt buộc ở dạng HEX (`secrets.token_hex(32)` / `bytes.fromhex()`). Tránh dùng raw bytes `.strip()` vì byte đầu/cuối rơi vào nhóm whitespace (khoảng trắng, newline...) sẽ bị cắt xén ngẫu nhiên (tỷ lệ lỗi 4.64%).
   - **Fail-Closed on Corrupt Key:** Nếu key file trên đĩa bị hỏng hoặc rỗng -> Bắt buộc ném `RuntimeError` dừng hệ thống, cấm tự ý ghi đè tạo key mới làm vô hiệu hóa các report đã ký trước đó.

5. **Assurance Level Invariants & Anti-Downgrade:**
   - `assurance_achieved` do Verifier tự tính toán độc lập dựa trên bằng chứng vật lý đo được (A1: exit/file; A2: dynamic nonce + tamper clean; A3: negative control pass + binary sha256 pin).
   - Nếu verdict != `PASSED` -> `assurance_achieved` bắt buộc gán `"NONE"`.
   - **Anti-Downgrade Invariant:** Caller tuyệt đối không thể truyền `min_assurance` thấp hơn để hạ chuẩn của contract (`required_ass = max(c_ass, min_assurance)`).

---

## 3. Bài học điều phối Remediation Loop qua 4 vòng review với Claude CLI

Trong phiên thi công, module đã được đưa qua Claude CLI phản biện độc lập qua 4 vòng (62 -> 68 -> 78 -> 86 APPROVED):

| Vòng | Điểm | Lỗ hổng phát hiện | Giải pháp khắc phục |
|---|:---:|---|---|
| **V1** | **62/100** | Contract rỗng hoặc predicate lạ tự trôi ra `PASS`. Thiếu scan tamper sau khi chạy. | Đổi mặc định `p_res = FAIL`; kiểm tra allowlist strict; thêm Post-execution tamper scan. |
| **V2** | **68/100** | Short-circuit bị bỏ qua trong negative controls (target vẫn chạy ngầm dù contract hết hạn). Secret key lọt vào target env. | Bọc `can_execute` cho toàn bộ negative controls; scrub `HERMES_VERIFIER_SECRET_KEY` khỏi runtime env. |
| **V3** | **78/100** | Key raw bytes bị lỗi cắt khoảng trắng ngẫu nhiên khi đọc lại; pre-scan chưa chạy trước khi tính `can_execute`; caller truyền `min_assurance="A1"` làm lọt contract A3. | Lưu key dạng HEX; pre-scan types ngay đầu hàm; lấy `max(contract, caller)` để chống hạ chuẩn. |
| **V4** | **86/100** | **APPROVED** — Khóa chết hoàn toàn `has_pre_blocker` với `INVALID_ASSURANCE_LEVEL` và `NO_REQUIRED_PREDICATES_FORBIDDEN`; 38/38 unit tests pass; marker file được chứng minh không bao giờ tạo khi dính blocker. |

### Nguyên tắc vàng cho Coordinator khi remediation với Reviewer:
1. **Không dừng lại than thở:** Khi điểm < 85, đọc thẳng lỗi P0/P1 do Reviewer chỉ ra, vá chính xác tại code và viết regression test chứng minh.
2. **Không tin vào assertion verdict đơn thuần:** Khi test short-circuit, BẮT BUỘC dùng `marker_file` do target cố tình tạo ra và assert `not marker_file.exists()` để chứng minh subprocess thực sự không hề được spawn.
3. **Cô lập test 100%:** Dùng fixture `autouse=True` với biến môi trường `HERMES_AUDIT_LOG_FILE` trỏ vào `tmp_path`, tránh để unit test ghi rác vào file production audit log `D:/Taadaa/logs/pow_verifier_audit.jsonl`.
