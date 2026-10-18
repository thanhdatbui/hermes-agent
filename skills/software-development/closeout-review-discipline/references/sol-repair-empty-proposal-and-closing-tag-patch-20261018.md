# Sol Repair Empty Proposal & Closing Tag Invariant (2026-10-18)

## 1. Bản Chất Hiện Tượng Proposal Rỗng (`patches_count: 0`)
Trong nhiều session (`20261012_111302_8b9ed930`, `20261014_222847_b55a7842`, `20261018`), khi gọi `sol_repair.py` độc quyền ở Strike 1, file JSON kết quả trả về `valid: true` nhưng `file_patches: []` và `patches_count: 0`.

## 2. Ba Nguyên Nhân Kỹ Thuật Đã Được Khắc Phục Triệt Để

### a) Lệch thẻ đóng Regex: `<</FILE>>` vs `<</FILE>>>`
- **Thực tế model trả về:** Mô hình Sol High (`gpt-web-sol` qua port 20129) hầu như luôn kết thúc khối code bằng `<</FILE>>` (chỉ 2 dấu ngoặc nhọn `>>`).
- **Lỗi regex cũ:** Parser trong `_parse_repair_response` định nghĩa cứng `r"<<<FILE:\s*([^\n>]+)>>>(.*?)<</FILE>>>"` (bắt buộc 3 dấu `>>>`).
- **Hậu quả:** Sai lệch 1 ký tự khiến toàn bộ khối patch hợp lệ của model bị vứt bỏ hoàn toàn.
- **Giải pháp:** Chuyển sang regex linh hoạt tolerant:
  `r"<<<FILE:\s*([^\n>]+)>>>(.*?)(?:<<\s*/FILE\s*>{1,3}|(?=<<<FILE:)|(?=<<<TEST_SUGGESTIONS)|$)"`
  Tương tự cho thẻ `<</TEST_SUGGESTIONS>>`.

### b) Mù Ngữ Cảnh Diff Khi Gọi CLI Thủ Công
- Khi Coordinator hoặc script gọi `sol_repair.py --repo ... --files ...` mà không có `--diff-file`, biến `diff_text` bị gán rỗng `""`.
- Khi không có diff, Sol High không biết đoạn mã `<<<OLD>>>` trong file monolith 6.000 dòng viết thế nào nên chuyển sang xuất Markdown giải thích, khiến parser không bắt được thẻ.
- **Giải pháp:** Bổ sung auto-git diff extraction trong `main()`:
  Tự động chạy `git -C <repo> diff origin/master -- <files>` (hoặc `HEAD`). Nếu diff rỗng, tự nạp 200 dòng đầu của các file mục tiêu vào prompt.

### c) Tự Động Khôi Phục Findings Từ Scorecard Gần Nhất
- Nếu thiếu `--scorecard-json` và `--findings`, script tự động bốc scorecard từ `D:/Taadaa/logs/latest_closeout_scorecard.json` hoặc dòng cuối cùng bị `REJECTED` trong `D:/Taadaa/logs/gate_audit.jsonl`.

### d) AST Parse Validation Cần Textwrap / Indentation Isolation
- Đoạn code thay thế `<<<NEW>>>` do Sol High sinh ra thường là một khối code thụt lề (ví dụ bên trong một hàm hoặc khối `with closing(...) as conn:`).
- Khi gọi `ast.parse(new_snippet)`, nếu `new_snippet` bắt đầu bằng thụt lề hoặc có dòng unindent lệch cấp, `ast.parse` sẽ văng `SyntaxError: unindent does not match any outer indentation level`.
- **Giải pháp:** Khi validate cú pháp một snippet Python độc lập, cần bọc thử trong một hàm dummy hoặc `textwrap.dedent` trước khi parse AST, tránh đánh rớt oan các patch có logic đúng nhưng mang thụt lề ngữ cảnh.
