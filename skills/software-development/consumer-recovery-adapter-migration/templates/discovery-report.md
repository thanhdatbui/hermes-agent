# Recovery Adapter Discovery Report — P<n> `<consumer>`

- **Ngày:** YYYY-MM-DD
- **Phạm vi:** Discovery + baseline-only trong worktree. KHÔNG patch production/test/requirements. Không live/ADB/device/TikTok/cron/subprocess side-effect. Không `pm clear`.
- **Repo gốc:** `D:\Taadaa\<consumer>` — dirty, KHÔNG đụng/reset/clean/stage.
- **Worktree:** `D:\Taadaa\<consumer>-recovery-adapter-p<n>-wt`
- **Branch:** `recovery-adapter/<consumer>-p<n>-discovery`
- **Base SHA (worktree HEAD):** `<sha>`

---

## 1. Preflight

### 1.1 Repo identity & base SHA
Table: origin toplevel/HEAD/branch; worktree toplevel/HEAD (= base yêu cầu)/branch; core repo HEAD + version (e.g. automation-core pyproject.toml:7); pre-existing worktrees (KHÔNG đụng).

### 1.2 Snapshot dirty state repo gốc (chỉ path/status; không mở nội dung)
```
 M ...   (12 files)
```
Manifest lưu: `<evidence-dir>\original-status-pre-write.txt` (chụp TRƯỚC khi write report; đối chiếu lại ở mục 6). Nêu rõ toàn bộ lệnh git trên repo gốc đều read-only; `git worktree add` chỉ ghi metadata `.git/worktrees/`.

### 1.3 Worktree status lúc khởi tạo
`git status --short` = rỗng (sạch, đúng HEAD). Bytecode: baseline dùng `python -B` (không tạo `__pycache__`).

---

## 2. Baseline (chạy TRƯỚC mọi write trong worktree)

```bash
python -B -m pytest -q -p no:cacheprovider <exact suite từ plan>
```
- **Exit / Collected / Passed / Failed** (lưu output thô vào evidence dir).
- **Phân loại từng failure** — PRE-EXISTING (môi trường/sibling project, kèm chuỗi lỗi gốc) hay real. Baseline này là mốc so sánh GREEN bắt buộc.
- **Interpreter/pin thật (FACT, không cài gì):** venv path + CPython version; installed dep version (importlib.metadata); pin file (bản SẠCH HEAD) version; target version (core pyproject). Ghi ASSUMPTION nếu plan nói pin khác mà file dirty không được đọc.
- Ghi chú line-number plan vs sạch HEAD nếu có lệch (plan trích theo bản dirty; report trích theo bản sạch).

---

## 3. Discovery — trace call-site thực (FACT, đọc source sạch trong worktree)

### 3.1 Các runtime path độc lập
Table: Path | Entrypoint | Orchestrator | Recovery loop. Nêu rõ process khác nhau (scheduler subprocess vs CLI in-process).

### 3.2 Trace từng path
FACT path:line cho: entrypoint → orchestrator → hàm mục tiêu (`_collect_with_recovery` …) → terminal paths; call-sites; điều kiện budget-exhausted.

### 3.3 Trả lời câu hỏi cốt lõi của plan
- map FAILED_SAFE/TERMINAL states → NON_RETRYABLE khả thi? (choke point path:line)
- FINAL_BLOCKED budget-exhausted là seam? (điều kiện `lease is None or recovery_state["rebooted"]`)
- retryable paths nơi nối hook? (path:line)
- guided recovery? — grep toàn bộ allowlist: 0 hits = DISPROVED (không phải "maybe")

### 3.4 ASSUMPTION / NEEDS_PROOF
Liệt kê rõ từng dòng; mỗi NEEDS_PROOF có lý do + cách verify ở implementation.

---

## 4. Kết luận

### `READY_FOR_P<n>_IMPLEMENTATION` ✅ (hoặc `NEEDS_PROOF` + dừng)
Lý do theo tiêu chí "concrete offline-testable runtime seam proven": liệt kê từng SEAM (FACT path:line + test offline hiện có phủ seam). KHÔNG claim live-connected. Lưu ý bắt buộc cho implementation (baseline không fully-green; RED test file theo allowlist).

---

## 5. Files đã đọc / không đọc

- **Đã đọc (bản SẠCH trong worktree <sha>):** liệt kê source/rules/docs/tests.
- **KHÔNG đọc (bị cấm):** file forbidden (vd `login_runner/password_change.py` — dirty sẵn), mọi file dirty khác (chỉ status path/status), mọi credential/workbook/log/raw artifact/.env/session/generated runtime. Không live/ADB/device/TikTok/cron/subprocess; không `pm clear`; không cài gì.
- **Không commit/push.** EOL: LF. Không sửa source/test/config/pin.

---

## 6. Verification sau write

- Worktree status → chỉ `?? docs/ai/recovery-adapter-discovery-<consumer>-<date>.md` ✅
- Worktree tracked manifest (`git ls-files -s`) pre vs post: identical ✅ (không sửa source/test/config/pin)
- Repo gốc status pre vs post: identical ✅ (hoặc drift ngoài tầm kiểm soát có bằng chứng — worker không gây ra)
- Evidence dir listing.
- **SHA256 / line count:** ghi trong summary worker (tránh self-reference khi chỉnh sửa file).

---
*Vietnamese report — P<n> Discovery + baseline-only. Không live work.*