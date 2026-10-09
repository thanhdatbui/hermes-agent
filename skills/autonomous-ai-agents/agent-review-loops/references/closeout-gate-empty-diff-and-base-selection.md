# Quy Tắc Chọn Base Ref Cho Closeout Gate & Xử Lý Bẫy "Diff is empty"

## Bối cảnh & Bài Học Thực Chiến (04/10/2026)
- **Hiện tượng**: Khi user ra lệnh `Done` / `Chốt phiên`, Coordinator chạy `closeout_gate.py` và gặp lỗi:
  ```text
  · Không có staged diff, thử git diff HEAD...
  · Không có uncommitted diff, thử so với origin/main..HEAD...
  · git diff origin/main..HEAD failed, fallback HEAD~1..HEAD...
  · Extracted diff: 0 file(s), 0 chars
  ✘ Failed to extract diff: Diff is empty
  ```
- **Sai lầm nghiêm trọng của Coordinator**: Vội vàng suy đoán mò là *"lỗi môi trường Git do diff.external hỏng"* rồi phát lệnh `clarify` bắt User tự gõ lệnh terminal gỡ config.
- **Phản ứng của User**: *"K, nhảm lồn, session khác có bị đâu. Gọi claude cli vào xử lý cho tao"*.

---

## 1. Nguyên Nhân Gốc Rễ Của Lỗi "Diff is empty"
1. **Lệch trạng thái giữa Working Tree và Commit**:
   - Nếu các file thay đổi **đã được commit lên HEAD** (ví dụ commit `f076d31`), thì working tree lúc này hoàn toàn sạch (`uncommitted diff = 0`, `staged diff = 0`).
   - Khi đó, nếu chạy lệnh mặc định `closeout_gate.py --repo <path> --base origin/main`:
     * Script cố chạy `git diff origin/main..HEAD`. Nếu nhánh local bị phân kỳ hoặc remote `origin/main` chưa fetch mốc mới nhất, lệnh diff này thất bại.
     * Script fallback sang `HEAD~1..HEAD` nhưng nếu base ref truyền vào bị ép là `origin/main` thì candidate scope không khớp, dẫn đến `Extracted diff: 0 file(s)`.
2. **Quy tắc bất biến khi chọn `--base`**:
   - Khi đã commit lên HEAD: **BẮT BUỘC dùng `--base HEAD~1`** đúng theo Hard Invariant:
     ```bash
     python D:/Taadaa/tools/closeout_gate.py --repo <đường_dẫn_repo> --base HEAD~1 --json-output
     ```
   - Khi chưa commit: Bắt buộc các file thay đổi phải được `git add <files>` (ở trạng thái staged), lúc này `closeout_gate.py` sẽ trích xuất trực tiếp qua `git diff --cached` với hash sha256 chuẩn xác.

---

## 2. Kỷ Luật Điều Phối Cấm Đoán
1. **CẤM đổ lỗi cho môi trường khi thấy diff rỗng**:
   - Tuyệt đối không phán đoán mò là Git bị hỏng `diff.external`, config bị lỗi hay môi trường hỏng khi chưa kiểm tra `git status -s` và `git log -n 1`.
   - "Session khác có bị đâu!" — Môi trường farm đã được chuẩn hóa, lỗi diff rỗng 100% do chọn sai base ref hoặc chưa stage file.
2. **CẤM dùng `clarify` để đẩy việc xử lý Git cho User**:
   - Vi phạm nghiêm trọng nguyên tắc vận hành chủ động: Agent phải tự kiểm tra trạng thái repo (đã commit hay còn unstaged) để điều chỉnh tham số `--base` hoặc `git add`, không được hỏi xin phép hoặc bắt User tự gõ lệnh sửa git config.

---

## 3. Quy Trình Khi User Yêu Cầu "Gọi Claude CLI Vào Xử Lý" Nhưng Gặp Giới Hạn
- Khi User bức xúc bảo: *"Gọi claude cli vào xử lý cho tao"*:
  - Chạy thử `claude -p "..."`.
  - Nếu Claude CLI báo rate limit 5h: `You've hit your session limit · resets <time>`:
    * Tuyệt đối không đứng im hay lặp lại lệnh gây spam.
    * Báo cáo trung thực tình trạng rate limit của Claude CLI kèm mốc reset.
    * Tự động fallback sang Sol Auditor OmniRoute (`:20129` model `review`) theo đúng quy chuẩn `claude-limit-protection` để hoàn tất chấm điểm Closeout Gate.
