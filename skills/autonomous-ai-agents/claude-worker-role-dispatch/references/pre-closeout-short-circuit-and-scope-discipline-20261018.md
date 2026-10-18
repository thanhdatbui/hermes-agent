# Pre-Closeout Short-Circuit & Anti-Scope-Creep Discipline (18/10/2026)

## 1. Incident: The 3-Hour Self-Inflicted Closeout Stall

### Triệu chứng & Bản chất:
- Task thực tế: Sửa 1 dòng trong `upload_preflight.py` (khớp header `'render dich'`). Code đã được sửa, test xanh và push lên `origin/master` từ trưa (Commit `59b4e6b`).
- Nhưng Coordinator bị kẹt suốt 3 tiếng vì:
  1. **Không kiểm tra remote trước khi gọi review:** Chạy `closeout_gate.py --base HEAD~1` khi repo đã sạch (`working tree clean`). Kết quả: Gate đi thẩm định nhầm một commit wifi/loading hud (`6305f29`) của session khác.
  2. **Vô tình gom file ngoài scope:** Bundle nhầm 83 dòng code OCR popup chưa verify (`benign_popup_registry.py`), làm diff vọt từ 2 dòng lên >130 dòng, làm mất điều kiện Grace Band (diff <= 30 dòng).
  3. **Bẫy cày điểm LLM (Score-Chasing):** Thấy điểm Sol rớt từ 78 xuống 72, thay vì kiểm tra diff để gỡ file rác ra, lại cắm đầu đẻ 12 tests để "nịnh" reviewer, rồi đòi sửa cả `THRESHOLD` của git hook.

---

## 2. Pre-Closeout Short-Circuit Invariant (Mechanically Enforced in closeout_gate.py)

Hàm `check_pre_closeout_short_circuit(repo, targets)` tại Step 2 của `closeout_gate.py`:
1. **Xác thực file tracked qua `git ls-files -z`:** File không tồn tại hoặc bị `.gitignore` bị chặn ngay (`targets not tracked by git`), fail-closed.
2. **Kiểm tra cả staged và working-tree drift:** So sánh đồng thời `git diff --cached @{u}` và `git diff @{u}`. Bất kỳ thay đổi nào chưa push đều bắt buộc đi qua gate review bình thường.
3. **Short-Circuit khi đã nằm trên Remote:**
   - Nếu target files đã khớp 100% với upstream (`@{u}`):
     - Ghi nhận `write_gate_audit(verdict='APPROVED', score=100, passed=True, ...)`.
     - Thoát `exit 0` ngay sau < 1 giây, bỏ qua toàn bộ việc gọi LLM review.
   - Nếu repo clean và HEAD == upstream: Tương tự thoát 0 ngay lập tức.

---

## 3. Quy tắc Điều Phối Chống "Ngáo" & Chống Phá Vỡ Hệ Thống

1. **Commit đích danh tuyệt đối:**
   - Chỉ dùng: `git commit -m "..." -- <file_1> <file_2>`.
   - **CẤM TUYỆT ĐỐI:** `git commit -a`, `git add .`, `git add -A` để tránh nuốt nhầm unverified files của session khác.
2. **CẤM đề xuất phá vỡ hệ thống đang vận hành:**
   - CẤM can thiệp quyền Windows ACLs (`icacls /deny`), CẤM đổi `core.hooksPath` hệ thống, CẤM đẻ cơ chế HMAC token rườm rà làm crash cronjobs/watchdogs của farm.
   - Mọi quy tắc an toàn phải tinh gọn, cô lập trong repo, không được gây lỗi `PermissionError` trên host.
3. **Kỷ luật dứt điểm — CẤM dừng lại khóc lóc (Anti-Paralysis Invariant):**
   - Không được viện cớ guard chặn hay reviewer trừ điểm để đứng hình, than phiền hay hỏi xin phép vòng vo.
   - Thất bại phải phân tích thẳng vào diff: diff bao nhiêu dòng? File nào làm phình diff? Gỡ ngay file ngoài lề để đưa về diff <= 30 dòng và kích hoạt Grace Band (80-84 auto-push).
