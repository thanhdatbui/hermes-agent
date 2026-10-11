# Dashboard nurture-health implementation lessons

## Scope
Use this reference when extending TikTok feed watchdog reporting or the Port 1905 dashboard with per-account nurture health.

## Required data split & Starvation thresholds
- Telegram watchdog is aggregate-only: render the 8-Row health line inside each farm block, once for Kibe and once for Admin.
- The Web Dashboard owns micro-level account inspection: account, machine, slot/Row, last nurture time, hours waiting, and status.
- **Ngưỡng chu kỳ và bỏ đói đồng bộ (96h + 12h grace):**
  * Hằng số chuẩn hóa: `NURTURE_CYCLE_H = 96.0h`, `STARVATION_THRESHOLD_H = 108.0h` (96h + 12h dung sai cho trễ ca / retry).
  * 3 dải trạng thái hiển thị:
    - 🟢 Đúng chu kỳ (healthy): `<= 96h` (trong vòng 1 chu kỳ 4 ngày).
    - 🟡 Trễ trong dung sai (pending grace): `> 96h` và `<= 108h` (đang chờ ca theo lịch hoặc trễ nhẹ).
    - 🔴 Bị bỏ đói thật sự (starved): `> 108h` -> Kích hoạt cảnh báo.
  * **Cảnh báo bẫy toán học 120h của Random Parity:** Nếu đảo ngẫu nhiên chẵn/lẻ đầu mỗi chu kỳ 4 ngày (Odd-first <-> Even-first), hàng lẻ chạy Day 0 chu kỳ N và Day 1 chu kỳ N+1, tạo khoảng cách $5 \text{ ngày} = 120\text{h}$, gây bão đỏ báo động giả ở 16/60 chu kỳ. BẮT BUỘC giữ Fixed Parity (`_is_cycle_odd_first == True`) để khoảng cách giữa 2 lần nuôi của mọi Row chính 1-8 luôn là **CHÍNH XÁC 96 GIỜ** (`gaps == {timedelta(hours=96)}`).

## Dashboard UI & Data Integrity Invariants
- **Số lượng động (Dynamic Total):** CẤM hardcode số tĩnh "1,280 máy". Bắt buộc lấy động từ `${escapeHTML(sm.total || 0)}` khớp với số account thực tế trong DB (ví dụ: 1,255 accounts).
- **Múi giờ đồng bộ:** Helper và Watchdog bắt buộc chuẩn hóa `Asia/Ho_Chi_Minh` (`HCMC`).
- **Phòng chống XSS:** Mọi giá trị động (`username`, `cluster`, `err.message`) khi render vào `innerHTML` BẮT BUỘC phải qua hàm `escapeHTML()`.
- **Minh bạch lỗi DB:** BẮT BUỘC trả mã HTTP 503 và thông báo rõ ràng khi DB lỗi/thiếu bảng, CẤM nuốt ngoại lệ `except Exception: pass` âm thầm khiến API trả 200 với danh sách rỗng giả tạo.

## Mapping invariant
`farm_account_info.tik` is the account's slot/Row (1..8) on a machine. Do **not** infer Row from `may` using `((may - 1) // 8) + 1`; that groups machines and gives the wrong account-level Row. Normalize invalid or missing `tik` to Row 1 and test with accounts whose `may` values differ but whose `tik` values differ.

## Watchdog implementation pattern
- Parameterize the live root; call the same summary function independently with `runtime/kibe/live` and `runtime/admin/live`.
- The summary scans only the bounded recent date folders and `row-<R>-<HHMMSS>` children, selecting the newest timestamp for each Row 1..8.
- Return both a compact formatted summary and a list of starved Rows so the caller can append a warning only when needed.
- Keep the existing watchdog parser and farm result blocks unchanged apart from inserting the health lines immediately before the cluster block is appended.

## Dashboard implementation pattern
- Add a sibling API route (`/api/nurture-health`) next to `/api/follow-health`.
- Return a stable JSON envelope with `summary`, `accounts`, and optional telemetry/error fields.
- Add a dedicated view/container rather than mixing account rows into the main farm table. The view needs client-side search and filters for cluster and status.
- A passing baseline dashboard suite is not evidence that the new route/view works; add a focused test for the new endpoint/source markers and run it.
- **Pythonpath pitfall in `tools/tests`:** `D:/Taadaa/tools/pytest.ini` does not specify `pythonpath = .`. Any newly created test file under `tools/tests/` MUST include `import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))` at the top before importing tool modules; otherwise pytest collection fails with `ModuleNotFoundError`.

## Worker dispatch pitfalls
- For delegated edits, put literal `FILE: <absolute path>` lines in the worker context. Keep each task to at most two files (one implementation file and one test file).
- **Never dispatch parallel workers within the same repo workspace without worktrees:** A second dispatch overwrites the first worker's active Scope Lock, causing immediate `[WORKER GATE - SCOPE LOCK BREACH]` when the first worker attempts to write. Always serialize edits in the same repo.
- **Provide O(1) Patch Contracts on monoliths (>1,500 lines):** Never dispatch open-ended exploratory goals to `tiktok_dashboard.py` (3,200+ lines). Workers burn their 12-15 calls paginating the file and hit `ABORT_SCOPE`. Pre-verify unique anchors with `grep -F -c == 1` and provide explicit `OLD_STRING` / `NEW_STRING`.
- A worker report saying “completed” is not verification. Re-read `git status`, inspect the target markers, run the focused test, and check `py_compile` for Python modules.
- If an earlier worker had a mismatched scope lock, re-dispatch with a fresh exact contract; do not treat the abort as a code result.

## Performance and evidence guard
- Never use an unbounded recursive scan of a live farm as a dashboard request path. Use bounded date directories, explicit `row-*` children, or a cached/indexed source.
- If a live-data probe exceeds the focused timeout, report it as an unverified performance issue and switch unit tests to mocked/offline fixtures. Do not claim the dashboard is complete until the new API/view test passes.
- Verified session evidence: the existing watchdog suite passed 42 tests, the runner preflight suite passed 62 tests, and the pre-existing dashboard suite passed 51 tests; these do not replace focused tests for the new nurture feature.
