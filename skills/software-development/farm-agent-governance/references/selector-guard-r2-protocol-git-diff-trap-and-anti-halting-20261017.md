# Selector Guard R2 Protocol, Git External Diff Trap, and Anti-Halting Discipline (17/10/2026)

## 1. Selector Guard Rule R2 & R1 Protocol (`Tiktok-video`)

Trong repo `D:/Taadaa/Tiktok-video`, hook `.git/hooks/pre-commit` tự động kích hoạt `python tools/guard_selector_change.py --cached` để bảo vệ tính toàn vẹn của hệ thống tự động hóa giao diện TikTok farm.

### Rule R2: Quy Chuẩn Sửa Đổi Layout Profile
Bất kỳ commit nào có sửa đổi file trong `scripts/tiktok_workflow/profile_layouts/*.py` BẮT BUỘC phải đi kèm 2 điều kiện:
1. **Case Documentation (`docs/farm-automation-cases.md`):** Phải có một entry mô tả ca tự động hóa mới (hoặc cập nhật case tương ứng) với đầy đủ 3 trường bắt buộc:
   - `Layout:` Tên layout bị ảnh hưởng (ví dụ: `top_left_pencil`).
   - `Fixture:` Đường dẫn fixture XML dump tương ứng trong `tests/golden/profile/`.
   - `Anti-pattern:` Mô tả chi tiết hành vi sai hoặc bẫy false-positive mà layout giải quyết.
2. **Real Golden Dump XML Fixture:** Phải đính kèm file XML dump thu thập từ máy thật trong `tests/golden/profile/<layout>/dump.xml` (không dùng XML tự bịa).
3. **Cấm sửa bừa:** Nếu thiếu 1 trong 2 điều kiện trên, hook sẽ lập tức từ chối commit:
   ```text
   SELECTOR_GUARD REJECT: R2: Sửa profile_layouts bắt buộc kèm cập nhật docs/farm-automation-cases.md.
   SELECTOR_GUARD REJECT: R2: Sửa profile_layouts bắt buộc kèm golden dump.xml thu thập từ máy thật trong tests/golden/profile/.
   ❌ COMMIT BLOCKED: Vi pham selector hoac anti-skip guard!
   ```

### Rule R1: Vùng Cấm Delegate State Machine
Cấm sửa bất kỳ dòng nào bên trong vùng `PROFILE_SELECTOR_DELEGATE` của `state_machine.py`. Mọi logic nhận diện nút bấm mới phải được đóng gói vào class layout độc lập trong `profile_layouts/`.

---

## 2. Cạm Bẫy Biến Môi Trường `GIT_EXTERNAL_DIFF` Trên Windows

### Hiện tượng lỗi
Khi biến môi trường `GIT_EXTERNAL_DIFF` được export với giá trị rỗng (`GIT_EXTERNAL_DIFF=''`) trong môi trường Git-Bash / MSYS trên Windows:
- Mọi lệnh `git diff` trong hook hay subprocess Python không có cờ `--no-ext-diff` sẽ bị chết ngắt với lỗi:
  ```text
  error: cannot spawn : No such file or directory
  fatal: external diff died, stopping at <file>
  ```
- Lỗi này làm các script guard (`guard_selector_change.py`, `closeout_gate.py`) không thể đọc diff staging index và văng lỗi `GIT_ERROR`.

### Khắc phục
1. Trong các script Python gọi `subprocess` chạy `git diff`:
   - Luôn kẹp tham số `--no-ext-diff` ngay sau lệnh `diff`:
     `cmd = ["git", "-C", str(repo_dir), "diff", "--no-ext-diff", "-U0", base, "--", path]`
   - Hoặc pop biến `GIT_EXTERNAL_DIFF` khỏi `os.environ` trước khi chạy `subprocess.run`.
2. Trong lệnh shell tương tác: `git diff --no-ext-diff ...`.

---

## 3. Kỷ Luật Anti-Halting ("Làm Đi Cứ Dừng Lại Khóc Hỏi Hoài Thế")

### Bối cảnh tâm lý Operator
Khi Operator (User) đã ra chỉ thị hành động dứt khoát (*"làm đi"*, *"xử lý đi"*), Operator kỳ vọng Agent tự hành động liên tục qua toàn bộ chuỗi mắt xích cần thiết cho đến khi deliverable đạt trạng thái nghiệm thu.

### Anti-Pattern: Micro-Halting & Asking Loop
- Sau khi hoàn thành một commit nhỏ (lát cắt 1), Agent dừng lại hỏi: *"Em bắt đầu làm lát 2 nhé?"*
- Sau khi hoàn thành lát cắt 2, Agent lại dừng lại: *"Em tiếp tục lát 3 nhé anh?"*
- Hành vi này làm đứt gãy luồng công việc, biến Agent thành một trợ lý nhút nhát, đùn đẩy trách nhiệm ra quyết định cho Operator và gây ức chế tột độ.

### Invariant Bắt Buộc: Autonomous Pipeline Rollout
Khi đã nhận lệnh thực thi:
1. **Tự động cuộn qua toàn bộ các lát cắt (Continuous Thin-Slicing):**
   - Slice 1 $\to$ Test $\to$ Audit $\to$ Commit $\to$ Push.
   - Tự động chuyển ngay sang Slice 2 $\to$ Test $\to$ Audit $\to$ Commit $\to$ Push.
   - Tiếp tục cho đến khi mục tiêu kiến trúc hoàn tất 100% (ví dụ: đưa dashboard từ 3.400 dòng về < 620 dòng).
2. **Điểm dừng DUY NHẤT được phép:**
   - Hoàn thành toàn bộ mục tiêu của phiên và báo cáo tổng kết.
   - Gặp lỗi vật lý không thể tự giải quyết (thiết bị offline, cổng USB rơi, đụng trúng Hard Guard R2 cần fixture máy thật).
   - Thao tác tốn phí tiền thật (SMS OTP, Captcha trả phí, xóa database).
