# Claude Sonnet Architectural Audit & Closeout Gate Integrity Lessons (06/10/2026)

## 1. Bối cảnh sự cố & Lịch sử kiểm chứng
Trong phiên làm việc ngày 06/10/2026, Closeout Gate bị kẹt 11 vòng loop liên tiếp (từ 14:18 đến 16:13) do:
1. Antigravity Gemini cạn quota/lỗi 403/429/502 trên OmniRoute (`:20129`) tự động fallback sang Luna (`gpt-5.6-luna-high`).
2. Luna over-engineer bôi thêm helper, mock test, code phòng thủ (+612 dòng), đẩy diff từ 20KB phình lên 92KB.
3. Diff vượt 24KB làm mất cơ chế review nhanh của Sol Web 0đ (15–20s), kích hoạt fallback bắt buộc sang Terra Codex (`cx/gpt-5.6-terra-high`), nơi reviewer chấm rất chậm và trừ điểm nặng (57–77 điểm).
4. Quy chế "No-cap remediation" cho phép Coordinator tiếp tục đẻ task remediation sửa đi sửa lại vô tận khi điểm < 85.
5. Hiện tượng "vác rác phiên trước đi review": file uncommitted dirty cũ bị gom vào diff của phiên sau.

Sau khi thực hiện bản vá Fail-Fast 24KB (`MAX_DIFF_BYTES_GATE = 24_000`) và cô lập scope `--files`, Claude Code CLI (`--model sonnet`) đã được triệu tập để thẩm định độc lập và phát hiện ra các điểm chí mạng dưới đây.

---

## 2. Các lỗ hổng kiến trúc & kiểm chứng (Claude Sonnet Audit Findings)

### A. Lỗ hổng Suy yếu Kiểm chứng trong `check_audit_binding` (Security Regression)
- **Cơ chế gốc**: Đối chiếu mảng `scope` và `scope_hash` trong binding trực tiếp với **trạng thái Git thật** (`diff-tree --no-commit-id --name-only -r HEAD`). Nếu Git thật khác scope đã duyệt $\to$ BỊ CHẶN NGAY.
- **Bẫy suy yếu**: Khi viết thêm targeted mode, nếu chỉ kiểm tra:
  ```python
  if scope_hash != audit_scope_hash(bound_scope):
      return False, "scope hash mismatch"
  ```
  thì hàm chỉ đang "tự-so-với-chính-nó" (internal consistency check). Bất kỳ đối tượng binding giả mạo nào tự nhất quán nội bộ cũng sẽ lọt qua cửa kiểm soát, làm mất tính chống gian lận (tamper-proof) trước khi commit/push.
- **Khắc phục chuẩn**: BẮT BUỘC đối chiếu với Git thật (hoặc danh sách target đã được xác nhận với HEAD/staged) trong mọi mode binding.

### B. Kẽ hở TOCTOU giữa Bước 2 (`extract_diff`) và Bước 3 (`resolve_audit_binding`)
- **Triệu chứng**: `diff_sha256` được tính ở Bước 2 (`diff_res.diff_sha256`), sau đó Bước 3 gọi lại `git diff` trong `targeted_candidate` và tính ra một mã SHA mới mà không đối chiếu chéo với Bước 2.
- **Rủi ro**: Nếu working tree bị sửa đổi hoặc tiến trình nền ghi đè giữa Bước 2 và Bước 3, diff được gửi lên Reviewer và diff được bind vào audit log có thể lệch nhau.
- **Khắc phục chuẩn**: Truyền `diff_res.diff_sha256` từ Bước 2 vào `resolve_audit_binding` và `check_audit_binding`. Nếu SHA tái tạo ở Bước 3 không khớp tuyệt đối với Bước 2 $\to$ ném lỗi `TOCTOU_DIFF_MUTATION_DETECTED` fail-closed ngay lập tức.

### C. Phân biệt Exit Code cho Fail-Fast Diff Budget
- **Vấn đề**: Khi diff vượt 24KB, nếu script chỉ `sys.exit(1)` (cùng exit code với test failed hoặc syntax error), Coordinator sẽ tưởng lầm là "code sửa sai" và tiếp tục dispatch Worker sửa lại. Worker Luna tiếp tục sửa $\to$ diff tiếp tục to $\to$ lại fail-fast trong 0.1s $\to$ tạo thành vòng lặp vô tận (spin loop) với tốc độ cao.
- **Khắc phục chuẩn**:
  - Gán mã exit riêng biệt cho Fail-Fast (ví dụ: exit code 3 hoặc structured JSON `{"verdict": "DIFF_TOO_LARGE"}`).
  - Coordinator khi nhận tín hiệu này BẮT BUỘC dừng remediation code, thực hiện phân rã task (Decompose) hoặc loại bỏ bớt file ra khỏi `--files`.

## 3. Các bài học sâu về Git Plumbing & Binding Integrity (Audit Vòng 4-5)

### D. Bẫy Fail-Open khi thiếu Base SHA (`committed_targeted`)
- **Triệu chứng**: Nếu code viết `if binding.get("base_sha"): verify(...)` thì khi kẻ tấn công hoặc bug xoá rỗng `base_sha = ""` khỏi binding record, điều kiện `if` bị bỏ qua hoàn toàn $\to$ bypass không cần check base commit!
- **Khắc phục**: Bắt buộc `base_sha` phải là chuỗi hex SHA hợp lệ (>= 40 ký tự). Nếu thiếu hoặc rỗng $\to$ REJECT NGAY (`"base_sha missing or invalid"`). Đồng thời bắt buộc tái tính và so khớp `diff_sha256` cho cả `committed_targeted`, không chỉ cho `worktree_targeted`.

### E. Xác thực Định dạng 64-Hex SHA Bắt buộc
- Không được coi một chuỗi bất kỳ là SHA hợp lệ chỉ vì nó "truthy".
- Bắt buộc kiểm tra `len(sha) == 64 and all(c in "0123456789abcdef" for c in sha.lower())`. Bất kỳ chuỗi nào sai độ dài hoặc chứa ký tự lạ đều bị chặn ngay tại cửa.

### F. Đồng nhất Domain Hashing: Raw Bytes vs Text Re-encoding
- **Bẫy False TOCTOU**: Nếu một nơi tính hash trên `diff_text.encode('utf-8')` (sau khi đã decode và convert CRLF/LF trên Windows) trong khi nơi khác tính hash trực tiếp từ raw git stdout bytes, thì dù working tree không hề thay đổi, hai giá trị SHA vẫn lệch nhau $\to$ gây lỗi giả `TOCTOU detected` làm tê liệt hệ thống!
- **Khắc phục**: Toàn bộ luồng từ `extract_diff` đến `staged_diff_sha256` và `resolve_audit_binding` bắt buộc phải hash trực tiếp raw bytes từ git stdout với cờ hermetic đồng nhất:
  `--binary --no-color --no-ext-diff --no-textconv`.

### G. Nhất quán Path Listing với cờ `-z`
- Git trên Windows mặc định escape các đường dẫn có ký tự tiếng Việt hoặc dấu cách nếu không có `-z` (hoặc khi `core.quotepath` bật).
- Nếu nơi này dùng `git diff --name-only` cắt dòng bằng `splitlines()` còn nơi khác dùng `_z_paths` (`-z` với ký tự `\0`), danh sách file sẽ bị lệch format quote $\to$ gây false `scope mismatch`. Bắt buộc dùng `-z` ở mọi lệnh trích xuất danh sách file.

### H. Quy tắc Đưa Code cho Reviewer CLI One-Shot (`--tools ""`):
- Khi gọi Claude Code CLI với cờ `--tools ""` (để tránh lỗi nuốt turns), model **hoàn toàn không có quyền đọc file trên đĩa**.
- Nếu prompt chỉ tóm tắt bằng lời ("đã fix xong, 28/28 tests passed"), reviewer chuyên nghiệp sẽ lập tức **TỪ CHỐI (NOT APPROVED)** vì không thể xác minh code thật dựa trên self-report.
- **Quy chuẩn**: BẮT BUỘC paste toàn bộ mã nguồn thực tế của các hàm liên quan và toàn bộ thân hàm test vào trong prompt để reviewer trực tiếp phân tích từng dòng code.

---

## 4. Quy chuẩn gọi Claude Code CLI Review trên Windows (MSYS/Git-Bash)
Khi điều phối Claude CLI (`claude -p`) để thẩm định code/diff trên Windows:
1. **BẮT BUỘC cờ `--tools ""`**: Với các tác vụ review mà diff/code đã nằm sẵn trong prompt, nếu không tắt tools thì Claude sẽ cố gọi `Read`/`Bash` ở turn 1, nuốt sạch turn budget và văng lỗi `Error: Reached max turns`.
2. **CẤM pipe MSYS**: Tránh `cat prompt.txt | claude` vì lỗi hang pipe không nhận EOF trên Windows. Luôn dùng:
   ```bash
   claude -p "$(< /path/to/prompt.txt)" --tools "" --model sonnet
   ```
3. **Chạy Background cho Long Tasks (>60s)**: Foreground terminal có thể bị guard timeout 60s clamp. Hãy dùng `terminal(background=True, notify_on_complete=True, timeout=240)`.
