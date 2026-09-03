## Cache Cleanup

Must run `pm trim-caches` (NOT `pm clear` — that logs out) at both:
- **Pre-CACHE** (after INIT, before READ_WORKBOOK)
- **Post-CACHE** (after DELETE_REMOTE_MEDIA, before RELEASE)

## Device Readiness — USB popup & Wi-Fi gate (core 0.4.22+)

Samsung farm: USB popup `MtpApplication/USBConnection` xuất hiện sau PC sleep
chặn uiautomator + mọi UI tap; wifi có thể văng tự nhiên và reboot không tự
lên. Core `prepare_device` (0.4.22) tự dismiss popup qua shell + verify bằng
`dumpsys activity`; `watch_device_reconnect` (0.4.23) defer on_ready tới khi
wifi lên (`WIFI_NOT_READY`). Chi tiết detect/dismiss/verify + lệnh chạy env
sạch + PS 5.1 pitfall: `references/core-device-readiness.md`.

## Video Selection

- `Video Đã Đăng + 1` = next video number.
- Video at: `D:\TIKTOK-videonuoinick\{Folder Video}\{video_number}.mp4`
- `--video-number` for debug override; override must update context and workbook.
- Upload duplicate guard: `is_video_already_posted()` check before proceeding.

## Hashtag Selection

- Random 3-6 from `Hashtag Pool` column in workbook.
- Each run picks differently (random seed not pinned).
- Pool may be comma/space/newline delimited; parse and dedupe.
- If pool < 3, fall back to safe default hashtags.
- Keyword Video field can influence selection priority.

## Workbook Write Safety

- `atomic_workbook_update()` from `automation_core.workbook` with:
  - `backup=True`
  - `lock_timeout=30`
  - Save → reopen → verify cycle.
- Only write after verified post success.
- `dry_run` must propagate to `AccountSource`: if `dry_run=True`, update logs but does not write.

## ADB Install Troubleshooting (Samsung Farm Devices)

ADB install/install-multiple timeout trên Samsung S7 (SDK 26) có 2 nguyên nhân chính:

### 1. Stale Install Session

Khi `adb install-multiple` bị kill giữa chừng, packageinstaller giữ session dangling. Mọi lệnh install sau treo vì pm chờ session cũ.

**Phát hiện:** `adb -s <serial> shell "pm install-create"` trả về session ID cũ (VD `[131451610]`).

**Xử lý:** `adb -s <serial> shell "pm install-abandon <session_id>"`
**Verify:** `adb -s <serial> shell "pm install-create"` → session mới; abandon luôn session test.

### 2. Samsung Device Security Verifier

SM (`com.samsung.android.sm.devicesecurity`) là requiredVerifier. Khi thiếu `-i installerPackage`, SM treo kiểm tra sideload → timeout.

**Giải pháp — `-i com.android.vending`:**
```bash
# Single APK
adb -s <serial> shell "pm install -i com.android.vending /path/to/app.apk"

# Multi-split
SES=$(adb -s <serial> shell "pm install-create -S $TOTAL_SIZE -i com.android.vending" | grep -oP '\[(\d+)\]' | tr -d '[]')
adb -s <serial> shell "pm install-write -S <size> '$SES' 'base' /path/base.apk"
adb -s <serial> shell "pm install-write -S <size> '$SES' 'split1' /path/split1.apk"
adb -s <serial> shell "pm install-commit '$SES'"
```
`-i com.android.vending` giả danh Google Play Store, bypass Samsung verifier.

### 3. Push-then-Install cho ADB chậm

Samsung S7 transport ~1.0 MB/s (USB 2.0). `install-multiple` streaming dễ timeout.

**Workflow:** push trước → install local:
```bash
adb -s <serial> push <source_dir> /data/local/tmp/apks/
adb -s <serial> shell "pm install -i com.android.vending /data/local/tmp/apks/app.apk"
# Multi-split: install-create → install-write × N → install-commit
adb -s <serial> shell "rm -rf /data/local/tmp/apks/"
```

Luôn dùng timeout ≥ 300s cho push & install-commit.

## Consumer Project Topology (where source actually lives)

The TikTok automation project has a **dual-location** architecture that can make code review confusing, especially when Codex made changes.

### Two source trees

| Location | Purpose |
|---|---|
| `D:\Taadaa\<project-name>\` | **Real source** — editable development tree. `social_reg_v1.py` here is the full ~6000+ line source file. |
| `D:\OneDrive\Tiktok_Reg\` | **Deployed bootstrap** — the `social_reg_v1.py` here is a 16-line loader that imports a compiled `.pyc` from `__pycache__/`. |

The OneDrive copy runs in production; the Taadaa copy is the canonical source. **Editing the OneDrive `.py` bootstrap does not change behavior** — the real logic is in the `.pyc` loaded at runtime.

### Finding the real source tree for review

Before searching for a function, identify both trees:

```bash
# 1. Find automation-core's editable install to find the parent tree
pip show automation-core
# → Editable project location: D:\Taadaa\automation-core

# 2. Look for sibling consumer projects under the same parent
ls D:\Taadaa\
# → Tiktok_Reg/  automation-core/  Tiktok-video/  ...
```

Always check `D:\Taadaa\Tiktok_Reg\` first for function definitions. The OneDrive tree will be invisible to `grep`/`search_files` when the function exists only in compiled form.

### Compiled `.pyc` pitfall (Codex review blind spot)

Codex sometimes modifies the **compiled** `.pyc` directly without updating the `.py` source. This creates a critical blind spot:

- `grep`, `search_files`, and `git diff` on the `.py` files will **not find** Codex's changes.
- The `__pycache__/social_reg_v1.cpython-311.pyc` contains the actual runtime logic.
- A function like `_soft_reboot_recovery` may exist **only** in the `.pyc`.

**Detect this during review:**

1. Check the deployment tree's `social_reg_v1.py` — if it's a <20-line bootstrap with `marshal`/`importlib` loading a `.pyc`, the real code is compiled.
2. Compare file sizes: OneDrive bootstrap is ~600 bytes; Taadaa source is ~290KB.
3. If Codex ran on a worktree pointing to the OneDrive bootstrap, it may have modified the `.pyc` only. **Request a decompile or source commit before approving.**
4. When you can't find a function in either `.py` tree, check `__pycache__/` for a `.pyc` larger than the expected loader.

## Safety Guards (do NOT add)

- Do NOT add `is_device_locked` flag on `StateContext` — the consumer's unlock detection is a temporary implementation detail of `_handle_connect_device`, not a cross-state flag.
- Do NOT add `locked_or_secure` as a permanent workflow block. The consumer retries swipe with better parameters. Only escalate to MANUAL_REVIEW when retries are also exhausted (indicating a real lock, not swipe timing).

## Consumer-Side Unlock Recovery (Core `prepare_device` Still Returns locked_or_secure)

`automation_core.device.prepare_device()` does `wake` + `swipe_unlock` + `lock_rotation`, but some Android devices (Samsung S7 series, SM-G930F/G930S) still report `locked_or_secure` even after a successful swipe when:
- The screen was off for a long time before the workflow started
- The swipe duration (core uses 280ms) is slightly short for the device's sensor
- The swipe start height (core uses 85%) doesn't reach the unlock trigger zone

The consumer MUST NOT block on `locked_or_secure` without attempting recovery, and MUST NOT blindly proceed when the device is genuinely locked (TikTok won't render).

### Required Pattern — Insert Between prepare_device and rotation_locked Check

```python
readiness = prepare_device(self.context.adb_client, **prepare_kwargs)

# After prepare_device but before rotation check: consumer-side unlock retry
_UNLOCK_RETRIES = 3
if readiness.unlock_state == "locked_or_secure":
    logger.warning(f"Device locked after core prepare_device. Retrying swipe ({_UNLOCK_RETRIES} attempts)...")
    width, height = readiness.screen_size or (1080, 1920)
    for retry in range(1, _UNLOCK_RETRIES + 1):
        # Swipe from sát bottom edge (95% height), longer duration (500ms)
        adb_client.shell(["input", "swipe",
                          str(width // 2), str(round(height * 0.95)),
                          str(width // 2), str(round(height * 0.25)),
                          "500"], timeout=10, check=False)
        time.sleep(1.5)

        # Verify unlock via dumpsys window policy
        policy = adb_client.shell(["dumpsys", "window", "policy"], timeout=10, check=False)
        if policy and policy.ok and not _is_locked_in_dumpsys(policy.stdout):
            logger.info(f"Consumer swipe retry {retry} succeeded ✓")
            break
    else:
        # All retries exhausted → MANUAL_REVIEW
        self.context.is_ui_unavailable = True
        self.context.error = "[DEVICE_LOCKED] ..."
        return False

if readiness.rotation_locked is not True:
    # rotation check — unchanged, only reached if unlock succeeded or was never needed
    ...
```

### Key Rules

- **Separate recovery layers, in strict order:**
  1. `prepare_device` (core) — standard wake + swipe (85%→35%, 280ms)
  2. **Consumer swipe retry** — more aggressive (95%→25%, 500ms), verified via `dumpsys window policy`
  3. `rotation_locked` check — only reached after unlock is confirmed or was never needed
  4. OPEN_TIKTOK → force-stop + relaunch + `_wait_for_feed` + optional soft reboot
  5. MANUAL_REVIEW → user opens TikTok / unlocks device manually

- **Do NOT grab `screen_size` from `adb shell wm size` separately** — `prepare_device` already returned it as `readiness.screen_size`. Use it directly with a fallback of `(1080, 1920)`.

- **Do NOT add the rotation check before the unlock retry** — rotation must wait until unlock is confirmed because `settings put system` commands may not apply on a locked screen.

- **Reuse `_is_locked_in_dumpsys()`** (defined at module level) rather than inline-regexing dumpsys output in the handler. The patterns must match `automation_core.device._window_state()` exactly so both layers use the same definition of "locked".

- **Fallback screen size `(1080, 1920)` is safe** — the Samsung S7 farm devices all use 1080×1920. For other resolutions, `readiness.screen_size` will be populated by `prepare_device`'s `wm size` call.

## Commit đúng worktree

Trước commit luôn chạy `git worktree list --porcelain`, `git branch --show-current`, `git status --short --branch` trong **path mà user gọi là "tree này"**. Stage file cụ thể; không stage dirty/untracked ngoài scope. Nếu commit nhầm tree, chuyển commit sang đúng branch bằng cherry-pick semantic (resolve handoff theo nội dung của target branch), rồi đưa pointer branch nhầm về commit trước bằng phương án không phá untracked/dirty state.

**Pitfall — `git add <file>` commit luôn CẢ pre-existing dirty changes (2026-08-07):** workspace có 30+ file modified SẴN từ trước session (worker khác chưa commit). `git add social_reg_v1.py` lấy TOÀN BỘ working-tree diff của file đó → commit 2871 dòng, trong đó ~2870 dòng là code người khác (TARGET_INVENTORY, hotmail_recovery imports, `_redacted_adb_command`...) không phải của mình. Trước khi commit:
1. `git status --short` — biết file nào dirty sẵn từ trước (KHÔNG phải của mình).
2. `git diff --cached --stat` sau khi add — verify staged diff CHỈ chứa hunk của mình; nếu phình to bất thường (vd 2871 dòng cho 1 fix nhỏ) → file có sẵn dirty.
3. Nếu file đã dirty từ trước: hỏi user (giữ cả / tách hunk của mình bằng `git add -p` / stash). Không tự ý commit trọn file khi phần lớn diff không phải của mình. CRLF churn (LF source + core.autocrlf) cũng làm `git add` stage toàn file — kiểm tra `git diff --ignore-space-at-eol` để phân biệt line-ending churn với thay đổi thật.

**Check `REQUIRED_CORE_VERSION` against real git history before trusting it.**
A runner may pin a version that never existed (e.g. `0.4.30` — actual bumps:
`...→0.4.28→0.4.31→0.4.35`). Verify with
`git log -p --all -- pyproject.toml | grep -E "^\+version"`. The safest pin is
the **last commit that still exports the runner's API** — for the
`recover_android_transport` / `recover_missing_android_vpn` era that is
**0.4.31** (commit `64f0206`); HEAD 0.4.35+ replaced those with
`soft_reboot_and_wait` / `reboot_and_restore`, breaking old runners on import.

**Never `pip install -e .` automation-core into the Python env that runs the
consumer runner.** Editable install points the env at the source tree, so the
pinned 0.4.31 silently becomes the source HEAD (0.4.35/0.4.36) → runner dies on
`ImportError: cannot import name 'AndroidTransportRecoveryError'`. Test core
with `PYTHONPATH=D:\\Taadaa\\automation-core\\src` instead, and after any core
test reinstall the pinned wheel:
`pip install --force-reinstall --no-deps <pinned-wheel>.whl`.

**PYTHONPATH override trap (version mismatch "expected=0.4.40; actual=0.4.32"):**
Các runtime venv của consumer (vd `D:\CodexRuntime\tiktok-video\venv-core024`)
được tạo từ chính Hermes venv: `pyvenv.cfg` có
`include-system-site-packages = true` và `executable =
C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`. Hệ quả:
- Hermes session export `PYTHONPATH=C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages` (kèm thư mục hermes-agent) → **mọi process con kế thừa**, và sys.path đặt hermes venv lên TRƯỚC venv-local.
- `import automation_core` resolve từ hermes venv (0.4.32) dù `venv-core024\Lib\site-packages\automation_core-0.4.40.dist-info` đã có → preflight `metadata version did not match expected contract` dù dist-info mới vừa cài xong.
- **Debug nhanh:** chạy đúng python của venv: `"<venv>\Scripts\python.exe" -c "import importlib.metadata as m; print(m.version('automation-core')); import automation_core; print(automation_core.__file__)"`. Nếu `__file__` trỏ vào hermes venv → đúng là PYTHONPATH override.
- **Fix:** chạy runner/script với `PYTHONPATH=` rỗng (đã chứng minh: version trả về đúng 0.4.40 từ venv-local). Rule cũ: launcher/PS1 wrapper nên tự `$env:PYTHONPATH = ""` (hoặc chỉ set đường dẫn cần thiết) trước khi spawn child — đừng để kế thừa PYTHONPATH của session cha. `importlib.metadata` đọc dist-info theo sys.path, nên cũng dính y hệt.

## Recovery executor fallback: Codex quota → Hermes CLI one-shot (2026-08-07)

Auto recovery (schedule recovery watch, consumer `tiktok-luot nuoi acc`) gọi
`codex exec --model ...` qua `build_repair_command` / `build_advisor_command`
(supervisor) và `_repair_with_codex` / `_advise_with_codex` (runtime). Khi
Codex/OpenAI hết quota, output chứa `ERROR: You've hit your usage limit...` →
recovery fail 100% (`FINAL_BLOCKED` → lock blocked hàng loạt).

**Hermes CLI one-shot thay thế Codex khi quota:**
```bash
hermes -z "<prompt>" -m deepseek-v4-flash --provider 9router   # stdout-only
```
- `-z` = one-shot, in CHỈ final response ra stdout, không banner/spinner — chạy
  ngầm từ scheduler được. `-Q` KHÔNG dùng chung với `-z` (chỉ `hermes chat`).
- Executable KHÔNG nằm system PATH: pin abs path
  `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe`,
  override qua env `HERMES_EXECUTABLE`.
- Model/provider của Hermes đang chạy: `deepseek-v4-flash` / `custom:9router`.

**Quota detect → kích hoạt fallback (3 mảnh):**
1. `detect_provider_quota(output)` — regex `usage limit|quota|rate limit|429|
   403|hit your|insufficient quota|credit balance|out of credits` (IGNORECASE)
   → evidence `{"code": "quota_exhausted", "provider": "codex", "model",
   "source"}`. Chỉ trả safest identifiers, KHÔNG nhúng raw output (tránh rò
   secret vào ledger).
2. Map sang `PlannerResult` status `PROVIDER_UNAVAILABLE` + evidence — KHÔNG
   `invalid("planner-process-failed")`. `ready_for_fallback` (chỉ mở khi
   status == PROVIDER_UNAVAILABLE + evidence hợp lệ + digest) → kích hoạt
   `_run_deepseek_executor_mode` qua ladder `cmc/deepseek/deepseek-v4-flash/pro`.
3. DeepSeek slot command builder trả `[hermes.exe, "-z", prompt, "-m",
   slot.model, "--provider", "9router"]` — KHÔNG `--sandbox`/`--output-schema`/
   `--output-last-message` (Hermes in stdout). Prompt inline.

**CRITICAL bug — quota check phải chạy TRƯỚC `PatchDecision.from_result`:**
`PatchDecision.from_result({})` KHÔNG bao giờ trả None (mapping rỗng → empty
PatchDecision). Nếu code `if code != 0 and decision is None:` thì với output
quota (json_object → None → `{}`), `decision is None` = False → nhánh quota bị
bỏ qua → trả `{"patched": false}` sai lầm thay vì `PROVIDER_UNAVAILABLE`.
Fix đúng: `if code != 0:` → check quota trước; chỉ khi quota None mới xét
`if decision is None:` (INVALID). Áp dụng cho CẢ `_repair_with_codex` lẫn
`_repair_with_hermes`.

**Test offline (không chạy ADB/live):**
- quota detect → PROVIDER_UNAVAILABLE + `ready_for_fallback=True`
- build command deepseek slot → `[hermes.exe, "-z", ..., "--provider", "9router"]`,
  không `--sandbox`/`--config`
- `_repair_with_hermes` mock `_run_capture` trả quota → `planner_status:
  PROVIDER_UNAVAILABLE`; trả JSON hợp lệ → `patched: True`
- Lưu ý: test cũ assert deepseek build ra `codex --sandbox workspace-write`
  sẽ FAIL — cập nhật assert sang Hermes command.

**Watch process KHÔNG dính PYTHONPATH trap:** `run-schedule-recovery-watch.ps1`
set `$env:PYTHONPATH = $runnerRoot` (dòng ~534, ghi đè hoàn toàn) trước khi
spawn child → watch dùng core đúng của Python 3.12 (0.4.37 site-packages), KHÁC
với Tiktok-video launcher (không clear PYTHONPATH → dính hermes venv 0.4.32).

**Chẩn đoán schedule recovery nhanh:**
- `python_runner/runs/schedule-recovery-ledger.jsonl` — event
  `ADVISOR_RESERVED` → `ADVISOR_NOT_READY` (reason `planner-process-failed`)
  → `FINAL_BLOCKED` → `MANUAL_REQUIRED`
- `.ai-runs/schedule-recovery/<incident>/slot-*/advisor-output.txt` — chứa
  stderr thật của Codex CLI (bằng chứng quota: `You've hit your usage limit...
  try again at <date>`)
- `schedule-recovery-watch-lease.json` — heartbeat còn sống = watch chạy đều.
- Khi quota: mọi incident fail-closed đúng contract nhưng vô dụng; fix là
  fallback provider, không phải gỡ lock (lock blocked là hậu quả đúng).

Chi tiết triển khai + diff + test: `references/hermes-cli-fallback-2026-08-07.md`.

**Delegation pitfall (Windows/MSYS):** worker tạo git worktree qua đường dẫn
MSYS bị path mangling (`D:\d\Taadaa\...`) → registration git lỗi, branch
"already exists", cần `git worktree prune` + xóa dir rác + `git branch -d`
trước khi spawn lại. Khi giao repo work cho worker trên Windows, hướng dẫn
**làm trực tiếp trong working dir (`git checkout -b`)** thay vì tạo worktree,
và yêu cầu worker chạy test + commit (không để dở); parent phải tự verify
diff + chạy lại test + sửa test fail + commit nếu worker hết iteration.

## Workbook Writer Identity Env Contract

`transactional_workbook_update()` → `single_writer_workbook_update()` requires
**both** `TIKTOK_REG_WRITER_ID` and `TIKTOK_REG_EXPECTED_WRITER_ID` env vars
(declared == expected, else `BLOCKED_WRONG_WRITER_ID`). When a runner omits
them, EVERY workbook mutation fails with
`BLOCKED_EXPECTED_WRITER_ID_MISSING:tiktok_tracking` / `:gmail_clean_v2` —
including CAPTCHA cleanup, where the device account is already removed
(`ALREADY_ABSENT`) but the Excel row survives. Symptom: log shows
`[captcha-delete] ... device=ALREADY_ABSENT gmail_clean=DELETE_FAILED`.
Fix: runners that spawn workers or apply deferred results must
`env.setdefault("TIKTOK_REG_WRITER_ID", "<machine-local>")` and the same for
`TIKTOK_REG_EXPECTED_WRITER_ID`.

## Recovery-Runner Gating (startup/profile fails)

- `--recover-after-failure` is **off by default** and **requires
  `--full-scope-takeover`**. Without it, `TIKTOK_STARTUP_NOT_FOREGROUND` /
  `PROFILE_TAB_FAILED` are final-blocked without any transport recovery.
- `recover_android_transport` only does **proxy reassign** (`rebooted: false`).
  When the recapture succeeds but TikTok still crashes back to the launcher
  (`mCurrentFocus=...LauncherActivity`), transport recovery will NOT fix it —
  the device needs a real `adb reboot` + `sys.boot_completed=1` wait before
  retry.
- After reboot, VPN may not be back: no `tun0` → `VPN_RECOVERY_FAILED: proxy
  readiness timed out`. Check `ip addr show tun0` and the proxy watcher before
  assuming the run is broken.

### Why machines did NOT auto-reboot (and the fix)

Root cause: the runner's `_transport_verifier` only checked `adb get-state` +
UI XML length. A device that crashed to the **Launcher** still returns a long
UI XML, so the verifier passed → `recover_android_transport` declared success
after proxy reassign and **never rebooted**. Two more gaps:

1. `_should_recover_transport` required an `adb_transport_lost` /
   `window_dump_` marker in the log — `TIKTOK_STARTUP_NOT_FOREGROUND` and
   `PROFILE_TAB_FAILED` never carried those markers, so transport recovery was
   not even attempted for them.
2. The core transport primitive never launches apps, so a relaunch was needed
   **before** the reboot escalation.

Fix (all in the recovery runner):
- `_transport_verifier` must additionally require `social.APP_PACKAGE in xml`
  (or `com.google.android.gm` during OTP). Launcher-only XML → verifier False →
  reboot path triggers.
- `_should_recover_transport` returns True for the three signatures directly
  (drop the log-marker check).
- In `_recover_transport`, before calling `recover_android_transport`:
  `am force-stop <pkg>` + `monkey -p <pkg> 1` + ~8s wait + capture
  (`recovery_new_<stt>_after_relaunch`). Only if TikTok is still not
  foreground after relaunch does the core reboot path run — exactly the
  user-required order "force-stop relaunch trước rồi mới reboot".

Verification pattern: stub `get_ui_xml` to return Launcher-only XML (long but
no `APP_PACKAGE`) and assert `_transport_verifier` returns False; stub
`enter_otp_code`/fresh-OTP for the OTP-reject branch tests. Always restore
monkeypatched module attributes (unrestored monkeypatching corrupts later tests
in the same run — isolate with save/restore in `finally`).

## Detector Manifest Staleness

Re-run `_detect_clean.py` (to the runner's `artifacts/pending/
tiktok_reg_clean_targets.json`) **after any source-workbook edit**. A stale
manifest keeps `SOCIAL_PREFERRED_EMAIL` pointing at a removed mail →
`Email override ... khong co trong Gmail source` final-block. Also: an email
that hits the TikTok "đã có tài khoản" login path but has no ID in tracking was
created outside this pipeline — remove it from source; it is not a reg target.

## Proxy Watcher vs Cockpit sidecar (misdiagnosis trap)

After a reboot, machines with no `tun0` → `VPN_RECOVERY_FAILED`. Before
debugging the device, check whether the **real proxy watcher is running**:
`wmic process where "name='python.exe'" get processid,commandline | grep gan_proxy`.
The watcher lives in the **gan-proxy project**
(`D:\Taadaa\gan-proxy\scripts\gan_proxy_fleet.py watch --all --mapping
D:\OneDrive\codex_gmail_debug\PROXYgandienthoai.xlsx --adb <adb> --runtime
D:\CodexRuntime\codex_gmail_debug-gan-proxy --poll-interval 15`). It is NOT the
`cockpit-cliproxy.exe` process — that is an Antigravity Cockpit quota sidecar
and has nothing to do with proxy assignment. If the watcher is down, no machine
gets VPN back after reboot; relaunch it and test by rebooting one machine and
watching `tun0` appear within ~1-2 min (watcher polls 15-30s + VPN startup).

## `DEVICE_NOT_PROVISIONED` — persistent UI backend semantics

`ProvisioningPolicy.REQUIRE_PROVISIONED` (core default, `ui_capture.py`) fails
with `DEVICE_NOT_PROVISIONED` when the persistent UI backend (atx-agent on
`/data/local/tmp/atx-agent`, port 7912) is not running. It is **not** a device
"not set up" state in the sense of missing TikTok config — it's specifically
the UI-capture backend. Diagnosis order:
1. `adb shell "ps -A | grep atx-agent"` — is the agent process alive?
   (`atx-agent` auto-restarts via a watchdog, so a PID change is normal.)
2. `adb shell "netstat -tlnp | grep 7912"` — is the port listening?
3. If the agent is up, `capture_ui_xml(..., provisioning_policy=...)` may
   already work — the error may have been transient at run time.

If a fleet has machines without atx-agent, switch the consumer to
`ProvisioningPolicy.ALLOW_LEGACY_SHELL_ONLY` (fallback to `uiautomator dump`).
Verified: capture succeeds under ALLOW_LEGACY on both machines with and without
a running atx-agent; do not keep REQUIRE_PROVISIONED if any target lacks the
agent. (Note: killing atx-agent to simulate absence does NOT work — a watchdog
restarts it within ~2s; find a real agent-less machine to test the fallback.)

## Vietnamese Header Aliases (target eligibility)

`gmail_clean_v2.xlsx` headers are Vietnamese: `số máy` / `tài khoản gmail` /
`pass mail`. Alias maps must include `tai khoan gmail` / `tai khoan` for
`email`. Do NOT alias bare `tik` to `tiktok_id` — the tracking sheet has both
`Tik` (slot number) and `ID` (username) columns, so `tik` makes header
detection ambiguous.

## Mailbox-Liveness Health Checks (Gmail vs Hotmail)

- Gmail OTP timeout already runs `run_google_live_check` (core `google_health`)
  → `HEALTH_CAPTCHA` triggers `cleanup_captcha_account` (device + Excel).
- Hotmail/Outlook had **no** liveness check: dead mail was never removed.
  Core now ships `automation_core.outlook_health` (0.4.36):
  `run_outlook_health_check(callbacks, ...)` returns `HEALTH_NORMAL` /
  `HEALTH_RELOGIN` / `HEALTH_LOCKED` / `HEALTH_MANUAL` / `HEALTH_UNKNOWN`;
  classifiers `is_outlook_sign_in_xml` / `is_outlook_locked_xml` strip
  Vietnamese accents **including `đ`→`d`** (NFKD alone leaves `đ`). Wire it in
  the consumer OTP-fail path; only remove mail on RELOGIN/LOCKED, never NORMAL.
  See `references/core-version-pin-and-writer-env.md`.

### Two OTP-fail paths — health check must be in BOTH

`social_reg_v1.py` has **two** distinct OTP-failure branches; a health check
wired into only one still leaves dead mail behind:

1. `handle_tiktok_email_otp` → the `if not code:` block (~line 8026) — runs
   after all OTP sources time out. This is where the Gmail
   `run_google_live_check` and the first hotmail health check live.
2. `_enter_tiktok_email_otp_with_one_fresh_retry` → the
   `if not fresh_code: raise OTP_REJECTED_NO_FRESH_CODE` branch (~line 7813) —
   runs when TikTok **rejects** the OTP and the resend returns no fresh code.
   This path does NOT pass through path 1. Add the same hotmail inbox-liveness
   probe (`_canonical_hotmail_login` → `_outlook_inbox_visible`) here, and only
   `mark_mail_die_in_audit_pending` + `remove_captcha_dead_email_from_source`
   when the inbox is NOT visible. Live inbox → keep mail.

Symptom that path 2 was missed: worker fails with
`HOTMAIL_OTP_TIMEOUT` / `[otp][OTP_REJECTED_NO_FRESH_CODE]` but the log has no
`hotmail-health-` / `inbox KHÔNG live` lines — the mail survives in source and
gets re-selected next run.

## Extending Core Detectors for Locale Variants (consumer wrapper)

Core detectors often match only English markers (vd `detect_add_phone_popup`
chỉ match "Add phone" / "Add your phone number") trong khi farm TikTok render
popup tiếng Việt ("Thêm số điện thoại"). Fix ở consumer adapter — KHÔNG patch
core (provider/UI policy thuộc consumer, khỏi build wheel):

```python
def detect_add_phone_popup(root):
    match = _impl.detect_add_phone_popup(root)   # thử core trước (an toàn nếu core sau này thêm)
    if match is not None:
        return match
    # re-implement marker logic với term tiếng Việt; tái dùng helper core:
    # _all_values / _has_contains / _close_candidate (được re-export qua globals().update(_impl))
    # ... return _impl.BenignPopupMatch("add_phone", markers, close)
```

**CRITICAL trap — override cả dispatcher, không chỉ leaf detector**:
Core `detect_tiktok_popup_action` hardcode detector tuple chứa `detect_add_phone_popup`
→ tuple đó tham chiếu hàm CORE, không phải wrapper của bạn. Symptom: gọi thẳng
`detect_add_phone_popup(root)` trả match, nhưng `detect_tiktok_popup_action(root)`
vẫn trả None. Phải override dispatcher trong wrapper:

```python
def detect_tiktok_popup_action(root, **kwargs):
    match = detect_add_phone_popup(root)          # wrapper consumer trước
    if match is not None:
        return _impl._action_match(match)          # BenignPopupMatch -> TikTokPopupActionMatch
    return _impl.detect_tiktok_popup_action(root, **kwargs)  # fallback core dispatcher
```

Notes:
- Dòng `globals().update({name: value for name, value in vars(_impl).items() if not name.startswith("__")})` (đầu `core/benign_popup.py`) re-export mọi hàm core (kể cả private `_all_values`/`_has_contains`/`_close_candidate`) vào namespace wrapper. Hàm consumer định nghĩa SAU dòng đó shadow core name cho lời gọi trực tiếp — nhưng lời gọi NỘI BỘ trong hàm core vẫn dùng reference core.
- `_impl._action_match(match)` (private nhưng ổn định) chuyển `BenignPopupMatch` → `TikTokPopupActionMatch`; `action.action == "dismiss_close_x"` đến từ core `_dismiss_action(popup_type)` (map `add_phone` → `dismiss_close_x` đã có sẵn).
- Verify: chạy test classifier mới (trước fail) + test variant English (no-regression) — cả 2 phải pass.
- Case thực tế đầy đủ (XML markers, bounds, test): `references/vietnamese-add-phone-popup-2026-08-06.md`.
- **TikTok Shop CTA popup** ("Mua ngay"/"Đóng"): same consumer-wrapper pattern —
  `detect_tiktok_shop_cta_popup` in the dispatcher chain after add-phone, before
  core fallback. Close button ("Đóng") is the safe element; "Mua ngay" enters
  purchase flow. Package-scoped to `com.ss.android.ugc.trill`. Full implementation
  + test strategy: `references/tiktok-shop-cta-popup.md`.

## User Frustration Signals (do NOT ignore)

- If user says "xoá" (remove), remove it from ALL mentioned locations. Do not keep a guard in other projects.
- If user says "đừng gọi tao" (stop calling me), run the loop to completion internally; relay only the final APPROVED result.
item. Fix: add `am force-stop <package>` with `time.sleep(1.5)` before monkey/am start inside `launch_app()`. 
14. **`import re` inside `while` loop degrades performance on large UI XML** — Python caches the module lookup but the dict lookup still runs on every iteration over hundreds of XML nodes. Fix: import all stdlib modules (`re`, `xml.etree.ElementTree`, `time`) at the **top of the method**, never inside a loop.
15. **Consumer skips unlock_state check after `prepare_device`** — core `prepare_device` may return unlock_state=locked_or_secure on Samsung S7 devices even after a swipe attempt. Without consumer-side retry, TikTok opens on locked screen -> SplashActivity -> MANUAL_REVIEW cascade. Fix: consumer-side retry with aggressive swipe (95%->25%, 500ms) and dumpsys-window-policy verification.
16. **reboot_and_restore() callbacks are Callable[[], object] — zero arguments** — See `references/reboot-and-restore-callback-contract.md`. Old `soft_reboot_and_wait` removed in core >=0.2.40. Callbacks capture `adb` via closure: `lambda: wait_until_unlocked(adb)`, never `lambda a: ...`. Error: `TypeError: <lambda>() missing 1 required positional argument`.
## TikTok New UI Login (post-46.x) & Manual ADB Workflow

Khi reconcile script thất bại (thường do account switcher navigation fail trên máy chưa có tài khoản nào, hoặc UI TikTok đã thay đổi), dùng quy trình ADB thủ công:

### Flow tổng quát (đã sửa cho TikTok 44.x)

```
1. Dismiss post-install consent popup "Đồng ý và tiếp tục" — SWIPE UP (không tap)
2. Dismiss Google sign-in popup (BACK key)
3. Từ màn hình "Đăng ký TikTok" → tap "Bạn đã có tài khoản? Đăng nhập" ← KHÔNG tap "Tiếp tục với email" (đó là signup!)
4. Từ màn hình "Đăng nhập vào TikTok" → tap "Sử dụng số điện thoại/email/tên người dùng"
5. Tap tab "Email/tên người dùng"
6. AdbKeyboard input username → tap "Tiếp tục"/"Đăng nhập"
7. AdbKeyboard input password → tap "Tiếp tục"
8. (Nếu có) 2FA → pyotp.TOTP → input code → tap "Tiếp tục"
9. Dismiss popup bảo mật (tap nút "Đóng") + Từ chối contact permission ("TỪ CHỐI")
10. BACK về feed nếu đang ở Shop → tap Hồ sơ → tap tên → verify
```

### Post-Login Privacy Policy (SparkActivity) — unresolved

Trên TikTok 44.2.3, sau login có thể hiện SparkActivity (WebView privacy policy). UIAutomator không thấy nút trong WebView. Scroll xuống cuối + tap bottom. BACK = dismiss mà không accept → account không fully activated.

### Chi tiết UI mới

Xem `references/tiktok-new-ui-login.md` — bounds, activity names, text patterns cho từng màn hình.

### AdbKeyboard Input Verification

Broadcast `ADB_KEYBOARD_INPUT_TEXT` return code KHÔNG đáng tin cậy. Luôn verify text đã nhập bằng UI XML dump:

```bash
adb shell "uiautomator dump /sdcard/window_dump.xml && cat /sdcard/window_dump.xml" | grep -oP 'text="<expected>"'
```

Nếu nút submit vẫn `enabled="false"` sau broadcast → text chưa vào. Retry broadcast hoặc tap lại input field rồi gửi lại.

### 2FA với pyotp

```python
import pyotp
# Secret từ cột 2FA trong workbook (thường là base32, 32 ký tự)
totp = pyotp.TOTP(secret)
code = totp.now()  # 6 chữ số, hết hạn sau ~30s
```

Code phải được generate và gửi trong cùng một cửa sổ <5 giây. Nếu sai, xóa text cũ (`KEYCODE_MOVE_END` + longpress DEL) rồi tạo code mới.

**Reusable provider:** `login_runner/totp_provider.py` (xem `references/totp-provider-implementation.md`) — đọc 2FA secret từ workbook, tự động match row theo `(machine, identifier)`, cache kết quả. Dùng trong `cli.py`:
```python
from login_runner.totp_provider import WorkbookTotpProvider
challenge_provider=WorkbookTotpProvider(workbook_path, secret_provider)
```

### Workbook Lock Workaround

Khi `pandas.read_excel()` báo `PermissionError` trên file OneDrive, dùng:

```python
wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
```

## Common Bugs Found in This Project

1. `context.current_state` typo — `StateContext` doesn't have this; use `machine.current_state`.
2. AccountSource created without `dry_run=self.context.dry_run` — always passes it.
3. `str(row["Folder Video"])` produces "489.0" — use canonical int-safe conversion instead.
4. `EmptyCell.column_letter` crash — iterate rows by index, not cell object.
5. `Video Da Đăng` typo key — always use canonical aliases.
6. `run_post.py` reporting uses `context.current_state` — must be `machine.current_state`.
7. **New config property added to Config class, mock Config in tests not updated** — when adding a new property to `Config` (e.g. `allow_device_reboot_recovery`) and referencing it in `run_real()`, the mock Config created via `type("Config", (), {...})` in `test_run_post_manual_review_uses_machine_state` MUST include the new attribute. Otherwise tests fail with AttributeError. Always add the new attribute with its default value to the mock.
8. **`_handle_account_switcher` adds consumer-side fallback/recovery tiers** — the consumer must NOT add `_fallback_tap_profile_tab()`, multi-tier recovery pipelines (direct → home-reset → reopen-tiktok), coordinate hacks, or subpage-clearing helpers (`_clear_profile_subpage_before_navigation`, `_verify_clean_profile_root`). Core handles internal retries. The only valid consumer pattern: dismiss popups → call core → core fail → `is_ui_unavailable=True` → MANUAL_REVIEW. Any consumer-side fallback masks core bugs and creates divergent behavior across consumers.
9. **`adapter.tap_profile()` hardcoded `(100, 1800)` is wrong** — position `(100, 1800)` corresponds to the Home tab (leftmost), not Profile tab. Profile tab is typically bottom-right on 1080×1920 devices (`900, 1800`). Fix: make `tap_profile()` use UI dump to find the real profile tab element first, with coordinate fallback only as last resort. Search order: resource-id → text → content-desc → coordinate.
10. **Consumer reimplements core's back-press loop for subpage clearing** — `_clear_profile_subpage_before_navigation` and `_verify_clean_profile_root` with manual `for attempt in range(5): adapter.back()` loops duplicate `leave_profile_subpage(max_back=3)` from core. Fix: import `leave_profile_subpage` from `automation_core.tiktok.account_switcher` and delegate instead.
11. **`_execute_with_ui_retry` outer loop has no awareness of inner retry exhaustion** — the outer loop treats `_handle_account_switcher` returning False as retryable, even though the inner loop already exhausted all retries and fallbacks. Fix: set `is_ui_unavailable=True` after the inner fallback exhausts so `_execute_with_ui_retry` breaks on its `if self.context.is_ui_unavailable: break` guard.
12. **`_handle_open_tiktok` skips force-stop and does not verify feed** — calling `adapter.launch_app()` without `am force-stop` first can leave the app stuck at SplashActivity. The ADB return value says "success" but the UI never reaches the feed. Fix: force-stop before every launch, then poll UI dump for feed indicators (`for you`, `following`, `đề xuất`, `home_tab`) with a 30s timeout. After all retries exhausted, set `is_ui_unavailable=True` to route to MANUAL_REVIEW (not FAILED). This is the root cause of the máy-62 PROFILE_ROOT_NOT_CONFIRMED cascade.
13. **`adapter.tap_profile()` coordinates do not account for device resolution** — the old hardcoded (900, 1800) is correct for 1080×1920 but wrong for 1440×2560 (SM-G930S). Fix: add resolution detection via `wm size` and calculate profile tab at right 1/5 of screen width, or use bottom-nav XML scan to find the rightmost clickable element. Keep multiple coordinate fallbacks for common resolutions.
14. **`adapter.launch_app()` does not force-stop** — without a force-stop before launch, subsequent retries resume the existing stuck process rather than starting fresh. Fix: add `am force-stop <package>` with `time.sleep(1.5)` before monkey/am start inside `launch_app()` itself.
15. **Consumer skips unlock_state check after `prepare_device`** — core `prepare_device` may return `unlock_state="locked_or_secure"` on Samsung S7 devices even after a swipe attempt (swipe timing slightly off, or screen was off for minutes beforehand). Without a consumer-side retry, TikTok opens on a locked screen → sticks at SplashActivity → `_wait_for_feed` fails → PROFILE_ROOT_NOT_CONFIRMED cascade → MANUAL_REVIEW. The fix is NOT a hard block on `locked_or_secure` (swipe-only devices still work); the fix is consumer-side retry with more aggressive swipe parameters (95%→25%, 500ms) and dumpsys-window-policy verification, with escalation to MANUAL_REVIEW only when retries are also exhausted."

