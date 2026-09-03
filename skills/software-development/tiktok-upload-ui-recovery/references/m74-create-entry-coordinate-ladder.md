# m74 4-tier UI recovery ladder + create-entry coordinate evidence (2026-08-09)

Machine 74 (serial `ce061606c21e153d03`, TikTok 46.2.3) — user request: run and document the
complete 4-tier UI recovery ladder INCLUDING the user-authorized final coordinate fallback,
preserving raw evidence for automatic handler implementation. This run PROVIDED the missing
evidence for the `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` signature (m74's historical failure).

## Pre-flight identity + lock (both aliases)

| Field | Value |
|---|---|
| machine_74.lock.json | machine=74, serial=ce061606c21e153d03, host=DESKTOP-3PFPGQC |
| serial_ce061606c21e153d03.lock.json | pid=46708, project=tiktok-upload, status=handoff, owner_active=false, lock_id=6335de1a107d4c9eb89085306c082809 |
| PID 46708 proof of death | `wmic process where "ProcessId=46708" get ...` → "No Instance(s) Available"; `tasklist /FI "PID eq 46708"` → no match. BOTH confirmations required (tasklist alone can silently lie on git-bash). |
| No replacement worker | wmic CommandLine scan for `tiktok_workflow` empty |

Archived both aliases (same-project tiktok-upload stale handoff, user-authorized cleanup):
`C:\Users\Kibe\.codex\device-locks\backup_m74_recovery_20260809T135448Z\`
+ evidence JSON `evidence_m74_recovery_20260809T135532Z.json` and `evidence_m74_recovery_20260809T135544Z.json`
(pre-sha256 + meta for each alias).

## Display geometry (critical for the coordinate)

```
Physical size: 1440x2560
Override size: 1080x1920   ← SCALE BY OVERRIDE, not physical
```
Create-entry tap: x = override_width // 2 = 540; y = bottom nav strip center = 1857 (strip 1794..1920).

## Ladder execution log (with per-tier evidence artifacts)

Artifact root: `D:\CodexRuntime\tiktok-video\m74-ui-recovery-20260809T133622Z\`

| Tier | Action (exactly once) | Evidence | Verdict |
|---|---|---|---|
| 0 | pre-action capture | `captures/00_pre_atx.*` (screenshot + dumpsys + UI XML 60,586 B) | surface = video detail/related; no bottom nav; no feed proof |
| 1 | ATX kill: `pkill -9 -f atx-agent`; `pkill -9 -f uiautomator`; `am force-stop com.github.uiautomator`; `uiautomator quit` | `actions/01_atx_kill.json`; `captures/01_after_atx.*` | dump readable but still no feed/bottom-nav proof |
| 2 | force-stop + `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1` (one pair) + ~12s wait | `actions/02_force_stop_monkey.json`; `captures/04_after_force_stop_monkey_wait.*` | **FEED VERIFIED** — XML 69,983 B: tabs "Bạn bè"/"Đã follow"/"Đề xuất" (selected); bottom nav `o3g` Trang chủ / `ejz` Cửa hàng / `o3c` Quay(+) / `o3h` Hộp thư / `o3i` Hồ sơ; vision confirmed full feed + central "+" |
| 3 | soft reboot | — | **SKIPPED BY EVIDENCE** (feed valid after tier 2). Note: skip-by-evidence ≠ ladder over; coordinate fallback still required because create-entry proof is a SEPARATE objective |
| 4 | coordinate fallback (user-authorized, ONE tap) | `actions/03_coordinate_tap.json` (+stderr/child.stdout); pre `captures/05_pre_create_tap.*`; post `captures/06_after_create_tap.*` | **CREATE-ENTRY PROVEN** — post-tap XML 54,901 B shows camera composer (see below). STOP at safe state; no further taps, no post |

## Post-tap create surface evidence (for handler + regression + COMPAT)

Node basis for the tap (from fresh tier-2 dump):
- `content-desc="Quay"` resource-id `com.ss.android.ugc.trill:id/o3c`, class Button,
  `clickable=true`, bounds `[432,1794][648,1920]` — bottom-center "+" create button (SAFE, not Post/Delete).

After the tap, the camera composer showed (mode tabs resource-id `com.ss.android.ugc.trill:id/x7f`):
- Mode tabs: "ẢNH" (selected=true), "VĂN BẢN", "AI SELF", "CAMERA" (selected=true), "MẪU", "LIVE"
- Duration chips: 10 phút / 60s / 15s
- Right rail tools: Lật, Flash, Hẹn giờ, Bố cục, Tỷ lệ, Làm đẹp
- Top: "Thêm âm thanh" (id `dvp`/`dvm`/`tv_top_text`); "Menu thả xuống" (`yg4`); gallery thumbnail bottom-left

This is the create-entry target surface — exactly what the worker needs a handler for
(open create button → land on camera composer → pick media path).

## Evidence-preservation recipe (reuse for every ladder run)

1. Timestamped artifact root: `m74-ui-recovery-<UTCts>/` with `captures/` + `actions/` + `REPORT.md` + `manifest.json`.
2. Per tier: capture BEFORE the action and AFTER (screenshot via `exec-out screencap -p`, raw `dumpsys activity activities`, raw UI XML via `uiautomator dump` to a FRESH remote path, `rm -f` first — prevents reading stale XML).
3. Per-capture JSON manifest: label, utc, screenshot rc/bytes, all command rc/stdout_bytes/stderr_bytes.
4. Action evidence: command list with rc + stdout/stderr decoded; if a script bug aborts mid-way, the action did NOT execute — verify no tap happened before re-issuing (2026-08-09: first tap attempt failed with NameError BEFORE `input tap`; corrected and issued exactly once).
5. Record `wm size` (both Physical and Override), the coordinate and its derivation, and the exclusion of dangerous controls.

## Vision fallback note

2026-08-09: primary `vision_analyze` returned 401 (invalid API key on the primary route). Used the
auxiliary vision model to confirm screenshots (feed at tier 2, camera composer at tier 4) and recorded
the limitation in REPORT.md. UI-dump markers remain the primary machine-readable evidence.

## Outcome

- Create-entry coordinate evidence collected: node `o3c`, (540, 1857), scale = override wm size.
- Prepared for automatic handler implementation: coordinator proves `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`
  → tap center create → recapture verify camera composer markers → proceed; regression test + COMPAT entry.
- No source/docs/workbook/credential modifications; no commit; no pm clear; no Post/Delete tap.