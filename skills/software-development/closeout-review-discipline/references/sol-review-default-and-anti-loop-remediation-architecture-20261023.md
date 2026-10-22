# Sol Review Mặc Định & Kiến Trúc Chống Kẹt Vòng Lặp 3-Strike Remediation (2026-10-23)

## 1. Bối Cảnh & Thực Tế Vận Hành (Problem Statement)
- **Vấn nạn đốt Quota của Sonnet Reviewer**: Khi ép `closeout_gate.py` dùng `--model claude-sonnet`, mỗi vòng review đọc full diff + scorecard chiếm 10k–15k tokens. Trải qua 3 vòng reject + 1 vòng hand-off sửa + 1 vòng re-audit = ~60k tokens Sonnet $\rightarrow$ cạn kiệt 85% hạn mức 5h của Claude CLI (`CLAUDE_QUOTA_GUARD_BLOCKED`).
- **Nghịch lý Moving Goalposts**: Sonnet Reviewer có xu hướng "kính hiển vi", liên tục đổi tiêu chí qua từng vòng:
  * Vòng 1: Chê thiếu telemetry & test âm.
  * Vòng 2: Sửa xong telemetry & test âm $\rightarrow$ lại chê "tại sao dùng substring mà không dùng prefix".
  * Vòng 3: Sửa xong prefix $\rightarrow$ lại chê "prefix chưa đủ hẹp" dù 72/72 tests pass 100%.
- **Điểm yếu của Sol Repair**: Tạo proposal JSON mà không có bước sandbox test nội bộ $\rightarrow$ dễ sinh patch dính lỗi cú pháp (`SyntaxError: unindent`) hoặc chắp vá hời hợt, làm lãng phí Strike.

## 2. Kiến Trúc Khắc Phục Tinh Gọn (Anti-Loop Remediation Architecture)

### A. Mặc Định Closeout Qua Sol Review (:20129)
- `closeout_gate.py` mặc định chạy `--model review` (Sol Auditor qua OmniRoute `:20129`).
- **Chi phí**: Tốn đúng 0% Quota Claude (sử dụng pool ChatGPT Web), không bao giờ gây gián đoạn hay khóa tài khoản Claude Code của Operator.
- **Phân vai**: Chỉ bật `--model claude-sonnet` khi Operator yêu cầu tường minh cho các đợt refactor kiến trúc lớn.

### B. Cơ Chế Tự Kiểm Thử Của Sol Repair (Internal Verify-Before-Submit)
- Trước khi ghi proposal ra đĩa, `sol_repair.py` phải thực hiện dry-run: áp dụng patch vào bản sao tạm và chạy `pytest <test_file>`.
- Nếu syntax error hoặc test fail: Sol Repair tự động loop-back sửa lại ngay trong nội bộ nó, không nộp bài thi hỏng lên Gate để tránh bị mất Strike oan.

### C. Khóa Tiêu Chí Chấm Điểm (Anti-Moving Goalposts)
- Reviewer Prompt enforce: Từ Strike 2 trở đi, Reviewer CHỈ ĐƯỢC PHÉP hậu kiểm các lỗi đã nêu tại Scorecard của Strike 1.
- Nghiêm cấm Reviewer tự ý nghĩ ra tiêu chí kiến trúc mới ngoài phạm vi đã bắt bẻ ở Strike 1 nếu diff không phát sinh rủi ro bảo mật mới.

### D. Tận Dụng Grace Band (80–84đ) Cho Diff O(1)
- Nếu diff O(1) nhỏ gọn (<= 30 dòng, 1-2 files), 100% focused tests pass và không có lỗi logic/an toàn farm: Gate tự động áp dụng Grace Band (80đ) để cấp Token APPROVED và push, không ép cày điểm lên >=85đ bằng các test/comment thừa thãi.
