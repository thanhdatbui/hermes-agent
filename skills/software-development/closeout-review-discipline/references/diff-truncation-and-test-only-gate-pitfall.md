# Bẫy Diff Truncation & Commit Test-Only Trong Closeout Gate

## Vấn Đề 1: Diff Quá Lớn Bị Truncate (>30KB / >500 dòng)
Khi tạo mới một tool hoàn chỉnh (ví dụ `claude_worker.py` + tests = 558 dòng), nếu chạy `closeout_gate.py --base HEAD~2` bao gộp toàn bộ feature:
- Sol High / LLM Reviewer bị giới hạn diff size và cắt ngang diff (`[... output truncated — 51 lines omitted ...]`).
- **Hậu quả:** Reviewer ghi: *"51 dòng bị truncate trong diff khiến không thể audit 100% logic main(). Điểm bị trừ nặng vì diff bị cắt."*
- Điểm tự động rớt xuống 68-72 dù test pass 100%.

### Cách khắc phục:
1. **Thin-slice Commit Discipline:** Không bao giờ tích luỹ 1 commit khổng lồ >500 dòng rồi mới chốt phiên.
2. Tách thành chuỗi commit nhỏ:
   - Commit 1: Core skeleton + basic tests (~150 dòng) → gate check
   - Commit 2: Extended features + edge cases (~150 dòng) → gate check
3. Nếu đã lỡ tạo file to: Chạy gate với `--base HEAD~1` từng bước thay vì gộp cả chuỗi vào 1 lần review.

---

## Vấn Đề 2: Bẫy Commit "Test-Only" Khi Sửa Lỗi Gate (Strike 3 Trap)
Khi Closeout Gate bị reject ở Strike 2 do "thiếu test", Agent vội vã viết thêm unit tests và commit riêng 1 commit chỉ có file test (`tests/test_foo.py`).

Sau đó chạy Gate với `--base HEAD~1`:
- Sol High thấy diff **chỉ có file test, không có dòng code production nào** (`+53 lines in tests/test_...`).
- Reviewer chấm:
  - `telemetry_observability = 0/15` (vì không có code production để soi logging/metrics)
  - `code_architecture = N/A` (không có diff production)
  - *"Không có diff production code nên không thể đánh giá. Phiên làm việc thực chất chỉ là viết thêm unit test. Điểm tổng thấp."*
- **Hậu quả:** Điểm tiếp tục < 85 dù test pass 32/32!

### Cách khắc phục:
- **Nguyên tắc "Code + Test song hành":** Mỗi commit remedia BẮT BUỘC phải có cả thay đổi production code (dù nhỏ: comment giải thích, refactor 1-2 dòng, thêm logging) đi kèm với test mới. Không bao giờ commit test đơn độc rồi chạy Gate lên commit đó.
- Khi cần gộp: Dùng `git commit --amend` để gộp test mới vào commit có production code, sau đó chạy Gate trên commit gộp.
