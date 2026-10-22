# Closeout Gate Payload Guard NEED_CONTEXT Trap & Multi-Scope Decomposition (2026-10-22)

## 1. Bối Cảnh Sự Cố & Triệu Chứng
Khi chạy Closeout Gate cho task lớn gồm nhiều file (ví dụ: 11 files bao gồm logic, catalog JSON và 5 test suites với tổng diff > 30KB):
```bash
python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/tools --base origin/main --files ... --json-output
```
Hậu quả:
- Reviewer Sol High (:20129) không chấm điểm mà trả về ngay dòng thông báo:
  `Verdict: NEED_CONTEXT:skill_lookup.py` (Exit code 1).
- Tiến trình closeout thất bại ngay tại Step 4 dù 19/19 unit tests pass 100%.

---

## 2. Căn Nguyên Kỹ Thuật (Root Cause Analysis)

### 2.1. Cơ Chế Bảo Vệ Mã Nguồn Của SolPayloadGuard
- Trong `sol_payload_guard.py`, `SOL_TARGET_BYTES` được giới hạn ở **36.000 bytes** (để chống tràn trần cứng 40KB của ChatGPT Web payload).
- Hàm `split_budget(36000)` phân bổ 80% cho diff (~28.800 bytes).
- Khi danh sách `--files` quá nhiều hoặc có file monolith lớn, `digest_diff` buộc phải cắt bớt một số file lớn và đánh dấu `(partial)` trong danh sách `omitted`.
- Đồng thời, guard tiêm chỉ thị an toàn vào manifest:
  `"NOTE: Phần bị lược KHÔNG được coi là đã review. Nếu cần xem để kết luận, trả về NEED_CONTEXT:<path>.\n\n"`
- Sol Reviewer tuân thủ tuyệt đối quy tắc bảo vệ an toàn: **Từ chối chấm điểm mù khi mã nguồn bị khuyết**, yêu cầu cung cấp đầy đủ ngữ cảnh bằng cú pháp `NEED_CONTEXT:<file>`.

### 2.2. Lỗi Staged Files Không Khớp Do MSYS Git Path
- Khi trong git index có sót file staged từ phiên trước hoặc từ công cụ worker (`ag_cli.py`, `dispatch_worker.py`), hàm `targeted_candidate` sẽ phát hiện `staged != targets` và fail-closed với lỗi:
  `staged files [...] != --files targets [...]; unstage extras or adjust --files`.
- Trên môi trường MSYS Bash Windows, lệnh `git reset HEAD <file>` nếu gọi ngoài thư mục repo có thể không unstage được do lệch đường dẫn tương đối. Bắt buộc dùng `git restore --staged <file>` hoặc chạy `git reset HEAD -- .` tại root repo.

---

## 3. Quy Chuẩn Khắc Phục Bắt Buộc (Multi-Scope Decomposition Invariant)

### 3.1. Bắt Buộc Phân Rã Ngữ Nghĩa (Gate 1 Decomposition)
Tuyệt đối CẤM nhồi toàn bộ các tính năng khác nhau vào một lần Closeout Gate duy nhất.
BẮT BUỘC chẻ nhỏ thành các Scope độc lập O(1):
- **Scope 1 (Core Feature):** Các file mã nguồn và test suite trực tiếp giải quyết yêu cầu của bản vẽ kiến trúc (ví dụ: `build_skill_index.py`, `skill_lookup.py`, `load_selected_skills.py` + tests).
- Đảm bảo diff của từng Scope luôn đạt **`Level: L0`** và **`omitted: []`** (100% diff nguyên vẹn, 0 file bị partial).

### 3.2. Tiêu Chuẩn Index Sạch Trước Khi Chạy Targeted Diff
Trước khi gọi `closeout_gate.py --files ...`:
1. Kiểm tra: `git -C <repo> diff --cached --name-only`
2. Nếu có file sót: Chạy ngay `git -C <repo> restore --staged <files>` để đưa diff cached về rỗng 100%.

### 3.3. Kỷ Luật Loại Bỏ Công Cụ Ad-Hoc Phụ Trợ (Anti-Overengineering)
- Nếu trong phiên có tạo các file thử nghiệm phụ trợ không nằm trong Plan kiến trúc (ví dụ: `farm_error_kb.py`) và bị Reviewer đánh giá là thiếu điểm kết nối thực tế / rủi ro schema giả định:
- **Hành động chuẩn:** Không cố đấm ăn xôi viết thêm test giả tạo để nẹp điểm. BẮT BUỘC dùng `safe_recycle.py` di chuyển các file thử nghiệm vào thư mục cách ly (`D:/.quarantine/`), giữ repo sạch sẽ và chỉ closeout đúng scope cam kết.

---

## 4. Nghiệm Thu Thực Tế (2026-10-22)
- Scope 1 (Dynamic Skill Routing: 8 files): 14/14 tests pass, Sol Reviewer chấm **85 / 100**, Verdict: **`APPROVED`**, cấp `CLOSEOUT_TOKEN` (Tier: strict).
