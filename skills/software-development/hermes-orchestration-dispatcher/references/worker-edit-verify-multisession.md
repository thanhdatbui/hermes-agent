# Verify worker edits trong môi trường multi-session dirty + EOL pitfalls (2026-08-08)

Khi nhiều session/agent cùng làm việc trên `D:\Taadaa` (mọi consumer repo thường dirty từ
trước), verify worker theo cấu trúc dưới đây:

## 1. So với BACKUP của worker, KHÔNG so `git diff HEAD`
- Spec bắt buộc worker tạo backup dir (`<task>-backup-<ts>\`) — đó là baseline CHÍNH XÁC trước edit.
- `git diff`/`git diff --stat` của repo LẪN các thay đổi pre-existing của session khác
  (vd `Tiktok_Reg` dirty hàng chục file, `gmail_reg_v10.py` có device_lock/`--full-scope-takeover`
  của session khác) → dễ tưởng "worker đụng file lạ" = false alarm.
- Cách đúng: `difflib.SequenceMatcher` backup-vs-current → chỉ đúng N vùng spec
  (delete=0; replace+insert count khớp spec; worker chọn insert thay replace — chấp nhận
  khi nội dung đúng + additive).
- Core dirty files: so `diff --stat` SAU vs baseline snapshot (không đòi git sạch).

**2. Check EOL byte-based**
- CRLF files: `crlf_sau - crlf_truoc == số dòng thêm`, `bareLF` (lf-crlf) delta = 0.
- LF files: `crlf == 0` giữ, `lone == lines` tăng đúng dòng thêm.
- File gốc có thể MIXED sẵn (HEAD LF thuần + working tree LF+CRLF do checkout) — chỉ assert
  "worker KHÔNG thêm lone-LF" (`lone_cur == lone_bak`), không bắt buộc file all-CRLF.
- Không `\r\r\n` (double-CR), BOM giữ (kiểm tra `b[:3] == b'\xef\xbb\xbf'`).

**3. PITFALL: patch tool (mode=replace) đổi EOL → churn toàn file**
- Trên file có LF trong working tree, `patch` có thể normalize TOÀN file sang CRLF → `git diff`
  hiện vài trăm dòng churn.
- Sau mỗi patch vào rule/doc/HANDOFF: đếm CRLF; nếu file store LF (HEAD LF thuần, `crlf_cur == lf_cur`
  nghĩa là all-CRLF mới) và HEAD LF → restore bằng python `b.replace(b'\r\n', b'\n')` ghi wb
  (đừng dùng sed). Ngược lại CRLF file bị về LF thì thêm `\r`.
- Append HANDOFF/policy entry: dùng script python detect EOL (`b"\r\n" in data`), append đúng EOL,
  entry text dùng `\n` chuẩn + replace trong code, không để patch tool chạm file lớn.

**4. search_files IOError trên Windows (MSYS path)**
- `search_files(path="D:\\Taadaa\\...")` bị convert thành `/d/Taadaa/...` → rg "IO error ... not found".
- Fix: chạy grep qua `terminal` (`cd /d/Taadaa && rg ...`) khi search_files fail; hoặc bỏ
JITTER pattern path khỏi tool tìm kiếm.

**5. Verify đa-session thực chiến 2026-08-08 (cả 2 case)**
- Phase A (Tiktok_Reg): 6 call-site wrap `_jitter`, `tiktok_login_v1.py` có **2 import blocks**
  (`from .social_reg_v1 import (...)` main + test path) — thêm import cả 2, không thì NameError
  ở nhánh test. Test: range assert (mọi sample trong [x-6,x+6], `len(set)>1`) KHÔNG seed global
  (`random.seed` đổi RNG state ảnh hưởng test sau); + test source-scan assert mọi dòng shell
  `"input","tap"` chứa `_jitter(`.
- Phase B (register gmail): file dirty chờ user xác nhận → backup + evidence mới; verify
  replay transformer byte-for-byte (chỉ 3 vùng edit). `pytest tests/` có thể fail do venv core
  stale / device_lock guard — phân biệt môi trường vs lỗi file bạn sửa, chạy subset liên quan.
- Anti-detect jitter: `_jitter = coord + random.choice((-1,1))*random.randint(4,6)`; jitter ±6px
  an toàn khi button ≥ 40px; KHÔNG jitter `calibrate.py` (tool đo toạ độ chính xác — nhưng tự
  có bằng chứng trong plan); hardcoded fallback `(999,1041)` vẫn nên jitter.