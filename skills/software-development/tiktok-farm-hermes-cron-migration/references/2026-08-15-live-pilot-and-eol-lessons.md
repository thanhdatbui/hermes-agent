# 2026-08-15/16 — Phase 9C.2 live pilot + EOL/autocrlf audit lessons

## Live entry recipe (máy 5 row 2 → máy 6 row 2, đều FAILED/success qua live_entrypoint)

Flow thật: `run_9c2_live.py` gọi `live_entrypoint.run_once({"permit_file": ...})` → validate permit
(canonical schema) → consume-once (`.consumed.json` marker, atomic O_EXCL) → `launcher_arguments(permit)`
→ `_production_launcher` spawn `powershell -File scripts/run-feed-session.ps1 -Row N -Machines M ... -Run`
(cwd=repo, env sạch PYTHONPATH) → feed session chạy thật trên máy → F1 verifier check observation.

### Permit phải CANONICAL (13 keys + schema_version), không phải pilot permit

- `run_once` → `_load_permit` → `_validate_permit`: allowed_keys = `{"schema_version"} | _REQUIRED_PERMIT_KEYS`
  (permit_id, manifest, manifest_sha256, manifest_id, entry_id, machine, row, serial, host_id, worker_id,
  account_workbook, artifact_root, repo). Pilot `build_activation_permit` thêm
  `logical_day/expiry/nonce/consumed` → `permit_invalid:permit has unknown keys`.
- Fix: build permit dict trực tiếp + `canonical_json(permit)` (từ `models`), KHÔNG qua pilot builder.
- `_consume_once` dùng marker file riêng (`permit.consumed.json`) — không cần key `consumed` trong permit.

### Manifest phải là assignment manifest đầy đủ

- Hand-rolled `{"manifest_id", "entries": [...]}` → `manifest_invalid:SOURCE_CONFIG_INVALID` (load_snapshot
  cần schema assignment đầy đủ).
- Dùng đúng pattern `_live_fixture` trong `test_hermes_cron_p1_r2.py`:
  `SourceConfig.from_dict(...)` → `_entry(account, day, f"provisional:{day}", iso, "feed_only", seed)`
  → `build_manifest_payload(day, source, seed, worker_id, worker_id, [entry], [])` → ghi `canonical_json(payload)`.
- Import path: `python_runner` là namespace package (không `__init__.py`); thêm cả repo root VÀ
  `repo/python_runner` vào sys.path; dùng Windows path cho sys.argv (MSYS `/d/...` không resolve).

### Launcher production bugs (cả 2 gây launcher_failed, đã fix + AG APPROVED)

1. `PYTHON_EXE = "/d/Taadaa/..."` (MSYS) → PowerShell `CommandNotFoundException`.
   Fix: `r"D:\Taadaa\python-envs\automation\Scripts\python.exe"` + sửa 2 test assert argv.
- `_spawn_subprocess` kế thừa `PYTHONPATH` của Hermes session (trỏ hermes-agent venv) → child resolve PIL
  từ sai venv → `ImportError: cannot import name '_imaging' from PIL`.
  Fix: `env = dict(os.environ); env.pop("PYTHONPATH", None); subprocess.run(..., env=env)`.
- **16/08 — ImportError `DeviceLockNeedsUserDecision` trong feed batches KHÔNG phải PYTHONPATH leak**
  (đừng vội áp lesson 9C.2 cho mọi ImportError): traceback hiện path hermes venv nhưng root cause là
  **version skew 3 env** — hermes venv **0.4.43** / Python312 global **0.4.44** / automation env **0.4.45**;
  class CHỈ có từ 0.4.45. `run-feed-session.ps1` default `$Python="python"` → bare python = Python312/0.4.44
  → fail từ 14/08. Fix: `pip install --force-reinstall wheel 0.4.45` (path Windows `file:///D:/...`,
  KHÔNG MSYS `/d/...`) vào CẢ 3 env; verify `hasattr(d,'DeviceLockNeedsUserDecision')` smoke từ chính env
  (pip show không đủ). Traceback path ≠ nguyên nhân — hỏi "symbol này có trong version nào" trước.

### LIVE feed misclassification (máy 5 swipe_16 → dừng sớm 16/30)

- Trieu chứng: feed session chạy 16/30 swipe rồi fail `feed not confirmed`; artifact cho thấy rơi vào
  TikTok LIVE (sponsored multi-guest live: "Đang LIVE", "LIVE", "Tử Gia Vĩ", "Yêu cầu").
- Root cause: `automation_core.detect_allowed_generic_popup` → `detect_live_room_invite_overlay` match
  LIVE thật (fullscreen `long_press_layout` + live terms) → `GENERIC_POPUP_SCREEN="manual-needed:popup"`
  → flow dismiss → post-dismiss observe fail → dừng session.
- Fix ở CONSUMER (`core/classifier.py`): trước `detect_allowed_generic_popup`, nếu có live markers
  ("đang live", "nhấn để xem live") + feed tabs ("trang chủ", "bạn bè", "đã follow", "đề xuất") →
  `ScreenClassification("for-you", 0.85, manual_needed=False)`. LIVE thật có tab feed; room-invite
  overlay thật KHÔNG có tab feed.
- Verify: chạy `classify_tiktok_screen` lên ui.xml thật → `for-you`; feed thường vẫn `following`;
  `_is_live_feed_screen` False trên feed thường.
- Cấp độ: tiktok-follow dùng `core/popup.py` riêng + `automation_core.dismiss_popup` (KHÔNG qua
  detect_allowed_generic_popup) → không ảnh hưởng → fix consumer đủ, không đụng core.

### User REJECT synthetic verifier — bài học lớn

- Live entry máy 6: feed session `summary.txt` = `status: success`, 17/30 swipe, có profile screenshot —
  NHƯNG live_entrypoint báo `verifier_not_accepted` vì thiếu `verifier_record.json` (script không bao giờ
  viết). User: "Nguỵ trang cc gì phiền phức chế đâu ra v" — REJECT cơ chế chế ra.
- Fix (`_build_observation_from_evidence`): dùng bằng chứng THẬT — `summary.txt` (regular, non-symlink,
  chứa `final_status: success` hoặc `status: success`) + `_find_profile_screenshot` (PNG path chứa
  "profile", mtime mới nhất, regular non-symlink). Identity fields copy từ permit; SHA-256 thật; verified_at
  = now. Thiếu bất kỳ → `verified: None` (fail-closed). `verifier_record.json` nếu tồn tại vẫn dùng verbatim.
- **Nguyên tắc vận hành: bằng chứng verify phải là artifact workflow THẬT mà script đã viết, không bắt
  script tạo file mới "để verify".** Khi user nói "chế nhảm", lùi về bằng chứng hiện có.

### Random 15-30 swipe — KHÔNG phải lỗi

- `selected_total_videos = random.randint(15, 30)` (đúng thiết kế "giống người dùng thật"); success =
  `completed_swipes >= selected_total`. Máy 5 random 30, máy 6 random 30 — 16-17 swipe < 30 → fail là
  đúng khi rơi LIVE. Không "fix" tỉ lệ này.

## EOL / core.autocrlf — bẫy audit re-binding (mất ~5 vòng re-audit)

Repo có `core.autocrlf=true`. File baseline MIXED EOL (vd `core/classifier.py`: 681 CRLF + 73 LF-only)
là cạm bẫy lớn nhất:

- Patch tool trên file mixed-EOL → LF-hoá cả vùng CRLF → `git diff --stat` nhảy 681/681 (toàn file),
  `git diff --check` báo `trailing whitespace` trên dòng `+...\r`.
- Chèn dòng mới: dùng script line-based — `raw.split(b"\n")`, mỗi phần tử giữ `\r` nếu CRLF, chèn dòng
  với cùng EOL vùng đó, `b"\n".join(lines)`; KHÔNG dùng patch tool.
- Normalize toàn bộ về LF là cách thoát duy nhất cho file mixed + autocrlf, NHƯNG phải làm TRƯỚC audit
  (mọi byte đổi sau APPROVED = rebuild prompt + re-audit; session này re-audit 3 lần vì normalize sau).
- Staged hash mismatch: working CRLF vs staged LF (autocrlf) → sha256 khác nhau. Giải pháp: normalize
  working về LF rồi `git add --renormalize` hoặc reset+add lại.
- File `MM` (staged + working modified) sau normalize: `git reset -q HEAD -- <f>` + `git add -- <f>`.
- Audit prompt diff phải dùng `git diff HEAD -- <f>` (bao gồm staged) — `git diff -- <f>` TRỐNG nếu file
  đã stage → auditor không thấy diff.
- `git add -A -- <deleted-path>` fail `pathspec did not match any files` khi deletion đã staged
  (`git rm` từ trước) → dùng `git add -A` không pathspec, verify `git diff --cached --name-only` exact.

## Commit helper pattern (dùng lại cho phase sau)

Guarded commit: verify HEAD/branch/status exact → response `APPROVED` → audit binding sha256 (từ prompt)
vs current bytes → EOL/BOM gate → `git add -A` → staged name-only exact → staged blob sha256 vs current
→ commit `-- <allowlist>` → post-commit HEAD^/files/status. External dirty (agent khác): tách EXTERNAL
list không stage, hoặc thêm vào allowlist nếu user "commit luôn". AGENTS.md mixed-EOL cũng cần normalize
LF trước khi stage để khớp staged blob.
