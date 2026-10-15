# Closeout Gate Invariants: DIFF_TOO_LARGE & Partial Committed Scope Refusal

## 1. Fail-Fast Diff Ceiling (MAX_DIFF_BYTES_GATE = 30,000 bytes)
`closeout_gate.py` có cơ chế bảo vệ cứng chống quá tải context của Reviewer model:
```python
MAX_DIFF_BYTES_GATE = 30_000
```
Nếu candidate diff (`raw_diff_bytes`) vượt quá 30,000 bytes:
- Gate lập tức thoát với `exit code 3` và in:
  `✘ GATE-FAIL(diff-too-large): [Gate Fail-Fast: DIFF_TOO_LARGE] Diff quá lớn (... > 30000 bytes). Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.`
- **Nguyên nhân phổ biến:** Viết quá nhiều test dài dòng, test nhiều kịch bản phụ, hoặc diff bao gồm cả logic refactor không cần thiết.
- **Biện pháp xử lý:** Thu gọn file test, chỉ giữ lại các unit test cốt lõi kiểm tra hàm mới/sửa, dọn sạch code duplication và blank line noise để hạ raw diff xuống dưới 25KB trước khi chạy gate.

## 2. Refusing Partial Committed Scope Invariant
Trong chế độ committed mode (`--base HEAD~1` hoặc `--base origin/master`):
```python
if set(targets) & committed_scope:
    raise ValueError(f"committed {diff_range} scope {sorted(committed_scope)} != --files targets {targets}; refusing partial committed scope")
```
- Khi chạy `closeout_gate.py --files <file1> <file2>`, danh sách targets trong `--files` **phải khớp chính xác 100%** với danh sách các file đã commit trong diff range (`committed_scope`).
- Nếu commit chứa 3 file (`scripts/A.py`, `scripts/cron/A.py`, `tests/test_A.py`) nhưng lệnh gate chỉ truyền `--files scripts/A.py scripts/cron/A.py`: gate sẽ refuse vì coi đây là partial committed scope.
- **Biện pháp xử lý:**
  1. Hoặc truyền đủ 100% các file đã commit vào `--files`.
  2. Hoặc bỏ cờ `--files` để gate tự trích xuất committed diff của toàn bộ commit (với điều kiện tổng diff <= 30,000 bytes).

## 3. Strike 3 Reviewer Hand-off Trigger & Claude CLI Model Warning
Khi gate reject 3 lần liên tiếp trên cùng `scope_hash` (`count_consecutive_rejections >= 3`), gate bật cờ hand-off:
`[REVIEWER_HANDOFF_TRIGGERED: 4 consecutive rejections reached for scope_hash=...]`
- CẤM tiếp tục cho Sol Repair hoặc Worker đoán mò/sinh patch lần 4.
- BẮT BUỘC bàn giao cho Claude CLI:
  `claude -p "<finding history + exact allowlist + acceptance command>" --allowedTools "Read,Edit,Write,Bash" --dangerously-skip-permissions --max-turns 15`
- **Lưu ý Claude CLI:** Claude CLI trên máy có thể cảnh báo unrecognized model nếu env default là `claude-sonnet-5-5`. Claude CLI vẫn tự sửa code và verify test bình thường trước khi chạm turn limit. Luôn kiểm tra `git status` và `pytest` sau khi tiến trình kết thúc.

## 4. Bẫy Tử Huyệt TRUNCATION_MANIFEST (Ngưỡng Ngầm 15KB Trừ Điểm Reviewer)
Mặc dù trần `MAX_DIFF_BYTES_GATE = 30_000` bytes mới kích hoạt Exit 3, trong hàm đóng gói prompt gửi cho AI Reviewer (`build_review_prompt`), Closeout Gate áp dụng ngưỡng cắt ngầm:
- Nếu một file trong diff (thường là file test mới viết quá dài với 300-400 dòng) vượt quá ~15,000 ký tự, gate sẽ **tự động cắt ngắn nội dung file và chèn cờ `[TRUNCATION_MANIFEST]`**.
- **Hậu quả chấm điểm của Sol Auditor:**
  * Sol Auditor có luật kiểm duyệt nghiêm ngặt: Khi phát hiện `TRUNCATION_MANIFEST`, Reviewer sẽ coi phần diff bị lược là **CHƯA ĐƯỢC CHỨNG MINH (UNVERIFIED CODE)**.
  * Reviewer sẽ ghi rõ trong Key Findings: *"TRUNCATION_MANIFEST xác nhận file test bị lược một phần. Vì vậy, không thể coi toàn bộ các dòng test là đã review đầy đủ... Phạm vi diff test bị lược khiến chưa đủ cơ sở để chấm mức sẵn sàng đóng việc."*
  * Điểm số bị kẹp trần ở mức 70–78 điểm, **TUYỆT ĐỐI KHÔNG THỂ ĐẠT NGƯỠNG APPROVED >= 85**.
- **Kỷ Luật Tinh Gọn File Test & Candidate Diff (User Invariant: Diff < 15KB):**
  1. File test unit/integration đi kèm diff BẮT BUỘC viết tinh gọn dưới **120 dòng (< 5KB)**.
  2. Dùng `@pytest.mark.parametrize` và gộp các assertions có cùng cấu trúc mock thay vì copy-paste 20–30 test methods dài dòng lặp đi lặp lại.
  3. Đảm bảo toàn bộ candidate diff gửi sang Closeout Gate luôn **dưới 15KB (zero truncation)** để Reviewer có thể đọc trọn vẹn 100% diff và chấm điểm tối đa.
