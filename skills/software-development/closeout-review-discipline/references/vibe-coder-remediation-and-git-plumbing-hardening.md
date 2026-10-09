# Vibe Coder Autonomous Remediation & Git Plumbing Hardening (06/10/2026)

## 1. Vibe Coder Autonomous Remediation Invariant
- **Bối cảnh**: User tuyên bố rõ: *"Báo tao cũng đéo biết AI phải tự xử lý chứ không phải tao, tao chỉ vibe coder"*.
- **Kỷ luật điều phối bắt buộc**:
  1. Khi Closeout Gate chấm `< 85` hoặc REJECTED: CẤM TUYỆT ĐỐI dùng `clarify` để hỏi xin phép, thanh minh, hay ném lỗi kỹ thuật bắt user vibe coder phải ngồi debug.
  2. Coordinator BẮT BUỘC tự động bám đuổi remediation: bóc tách exact finding từ scorecard, chỉ thị Worker thực hiện micro-diff O(1) (<= 30 dòng, 1-2 files), chạy focused test và gọi lại gate.
  3. Khi phát hiện diff phình to hoặc lỗi lặp: tự động rollback về baseline tối giản, chuyển sang phương án an toàn nhất thay vì buông xuôi báo BLOCKED.

## 2. Loại bỏ hoàn toàn nợ kỹ thuật toàn cục (Global Debt)
- Khi `docs/uiautomator.md` bị xóa trên toàn bộ 16 repo farm, nếu để trạng thái `D docs/uiautomator.md` dirty lơ lửng, mỗi repo sẽ bị gánh thêm 40KB diff rác.
- **Giải pháp**: Tách commit riêng `docs: remove deprecated uiautomator.md` trên từng repo độc lập trước khi chạy Closeout Gate tính năng/fix lỗi. Khi đó diff của task chỉ còn đúng vài chục dòng code thực chất.
- Khai tử vĩnh viễn `uiautomator.md`, mọi ràng buộc chống hồi quy chuyển 100% sang focused unit test + `closeout_gate.py`.

## 3. Git Plumbing Hardening trong Closeout Gate
- **Three-dot Merge-Base (`...`)**: Khi tính diff range cho committed candidate, sử dụng `merge-base actual_base HEAD` thay vì two-dot `base..HEAD` để tránh kéo nhầm các commit mới trên remote không thuộc về nhánh làm việc hiện tại.
- **Hỗ trợ Repo Offline / Non-main**: Hàm `_resolve_base_ref` kiểm tra lần lượt `base_ref`, `origin/main`, `master`, `origin/master`. Nếu không có remote (offline/detached), fallback an toàn về `HEAD~1..HEAD` mà không gây crash.
- **Canonical UTF-8 & Raw Bytes Hashing**:
  - Dùng `_git_bytes(repo, "diff-tree", "-z", "--root", "-m", "--no-commit-id", "--name-only", "-r", "HEAD")` để trích xuất file path dạng raw null-delimited `-z`, không bị escape các ký tự non-ASCII/tiếng Việt.
  - Cả Step 2 (`extract_diff`) và Step 3 (`staged_diff_sha256`) đều hash trực tiếp raw git stdout bytes với cờ canonical hermetic `_DIFF_FLAGS` (`--binary --no-color --no-ext-diff --no-textconv`), triệt tiêu hoàn toàn false-positive TOCTOU do CRLF/LF trên Windows.
- **Đối xứng Dirty Overlap Check**:
  - Cả `staged`, `committed`, và `committed_targeted` đều kiểm tra `dirty = set(_z_paths(_git_bytes(repo, "diff", "--name-only", "-z")))`. Nếu bất kỳ file nào trong candidate scope có unstaged edit dở dang ngoài working tree $\to$ REJECT NGAY với lý do `tested tree != reviewed diff`.
- **Fail-Closed Base SHA & Diff SHA**:
  - Bắt buộc `base_sha` phải là chuỗi hợp lệ >= 40 ký tự và khớp với git state. Bỏ trống hoặc xóa key `base_sha` đều bị từ chối fail-closed.
  - Bắt buộc `diff_sha256` phải là chuỗi 64-hex hợp lệ và khớp tuyệt đối với diff bytes tính lại từ git.
