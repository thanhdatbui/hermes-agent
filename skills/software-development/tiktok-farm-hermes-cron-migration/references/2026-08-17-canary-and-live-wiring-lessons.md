# 2026-08-17 — Canary 5-máy + live-wiring: accident, classifier bug, evidence

## Accident: `-Preset full` + `-Machines` → chạy CẢ FARM 73 máy

CMD sai đã chạy:
```
powershell ... run-feed-session.ps1 -Preset full -Row 1 -Machines 1,2,3,4,5 -Run ...
```
Kết quả: artifact `.ai-runs/20260817-005226/machines/machine_{1..74}` (73 máy, thiếu 35/47/68/72 = offline) — toàn bộ farm, mất ~1h (bị timeout 3600s ở Python wrapper vì session chạy lâu hơn 1h lẫn lộn!).

Root cause: `run-feed-session.ps1` dòng 98-99:
```powershell
if (-not $Preset -and -not $Machines) { throw ... }
```
`-Preset full` → nhánh Preset (dòng ~141+): đọc TOÀN BỘ máy từ workbook row (`list_feed_session_machines`) + lọc assignment manifest → bỏ qua `-Machines`. `-Machines` chỉ có hiệu lực ở nhánh else (khi KHÔNG có Preset).

Lệnh ĐÚNG cho N máy — **KHÔNG dùng `-LocalRun` khi kèm `-Machines`**:
```
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/run-feed-session.ps1 \
  -Row 1 -Machines 1,2,3,4,5 -Run -SkipAccountWorkbookSync \
  -MachineStartStaggerMs 2000,8000 -RandomizeMachineOrder \
  -ArtifactRoot D:\Taadaa\runtime\kibe\live_canary_5machines_parallel \
  -Python D:\Taadaa\python-envs\automation\Scripts\python.exe
```
Nhánh else (không Preset, không LocalRun) chỉ chạy đúng list máy; assignment gate cần
`-AssignmentManifest`/`-WorkerId` — env kế thừa Task Scheduler cũ
(`TIKTOK_FEED_ASSIGNMENT_MANIFEST=tiktok-feed.json` resources máy 1–74 = siêu tập; `TIKTOK_FEED_WORKER_ID`) OK,
hoặc tạo manifest canary riêng. **Viết sai ngày 17/08**: `-LocalRun` + `-Machines` → ps1:106
`throw "LocalRun cannot be combined with -Machines"` (LocalRun buộc `-Preset full` và CẤM Machines);
`-LocalRun` + `-Preset full` → chạy TOÀN BỘ máy row bỏ gate. 3 nhánh: Preset (máy row, bỏ qua -Machines) /
LocalRun (buộc Preset, cấm Machines) / else (-Machines thuần, cần gate). Xác nhận trước khi gọi:
`grep -nE 'LocalRun cannot|LocalRun requires' scripts/run-feed-session.ps1`.

## Kết quả máy 1-5 trong đợt 73 máy (lỡ chạy) — vẫn là dữ liệu canary dùng được

| máy | serial | status | ghi chú |
|---|---|---|---|
| 1 | 9885b64957334f5a46 | success | 30/30, follow hook OK |
| 2 | 9885e6303951513337 | success | |
| 3 | 9885e6344655484754 | **manual-needed** | account switcher bug (dưới) |
| 4 | 9885e6484432423046 | manual-needed | login/account screen — user bỏ qua |
| 5 | 9885e64b4a434a3037 | success | |

Follow hook: `follow_result.json` — `exit_code 0 status OK followed_count 0 failed false` (organic 6%, có thể 0). `selected_total_videos` random 15-30.

## Classifier bug máy 3: account switcher → manual-needed

Trình tự log máy 3 (18:02-18:04 UTC):
1. tap_profile OK → identity_guard OK (profile chính chủ)
2. tap_profile_switch_anchor (bounds [367,519]) → mở switcher
3. switcher_1_guard classify → **manual-needed**
4. verify_tiktok_focus → **TikTok focus lost** (`extra: {safety_status: failed, detected_screen: com.android.systemui}`)
5. navigate_profile fail → session fail

Screenshot switcher_1_guard/attempt_1/screen.png: TikTok profile + bottom sheet "Chuyển đổi tài khoản" — `ninhy05100` (tick đỏ active), `trangtran168432` (9+), `lequynh2043`, `Thêm tài khoản`.

Root cause: `_is_account_switcher_sheet` (core/classifier.py dòng ~101-106) yêu cầu:
```python
has_selected_account = any(
    element.attrib.get("selected") == "true"
    and bool(element.text.strip() or element.content_desc.strip())
    and "android.widget.button" in element.attrib.get("class", "").lower()
    ...)
```
XML thật: row active `ninhy05100` — `selected="true"` nhưng `class="android.widget.TextView"` → `has_selected_account=False` → switcher không được nhận → rơi popup bucket → manual-needed → flow KHÔNG tới bước tự chọn.

Fix (consumer): bỏ `and "android.widget.button" in class` — chấp nhận mọi selected element có text. Verify (đã chạy):
- `classify_tiktok_screen(ui.xml thật)` → `screen: manual-needed:account-switcher, conf 0.9, reasons ['account switcher sheet present']`
- `_is_legitimate_profile_account_switcher_xml(xml, "trangtran168432")` → True (flow sẽ tự tap nick row 1)

Flow tự chọn đã có sẵn (feed_swipe_smoke.py): `_find_account_switch_option(xml, expected)` → `_tap_ui_element action="tap_expected_account"` → verify — chỉ bị chặn bởi classifier.

## Bẫy PYTHONPATH khi gọi automation python từ Hermes session

Chạy đúng executable `/d/Taadaa/python-envs/automation/Scripts/python.exe` nhưng `import automation_core` → resolve về **hermes venv 0.4.43** (thiếu `escalation`, `DeviceLockNeedsUserDecision`) vì session Hermes export PYTHONPATH. Fix: prefix `PYTHONPATH=""` khi gọi trực tiếp:
```bash
PYTHONPATH="" /d/Taadaa/python-envs/automation/Scripts/python.exe -B -c "import automation_core; print(automation_core.__file__)"
# → D:\Taadaa\python-envs\automation\Lib\site-packages\automation_core\__init__.py
```
(live_entrypoint._spawn_subprocess đã pop PYTHONPATH cho child; chỉ lệnh debug trực tiếp bị dính.)

## Audit khi codex 60818 down + combo sol hết creds

- Codex CLI dùng provider `codex_local_access` (base_url localhost:60818) — service nền codex, KHÔNG watchdog, down = retry mù vô ích. 9router = 20128 (watchdog tự restart).
- Combo `gpt-5.6-sol` qua 9router → 404 `No active credentials for provider: codex` (combo cần codex creds).
- Dùng được: `ag/claude-opus-4-6-thinking` qua `-c 'model_provider="9router"'` (model audit plan 16/08). Lưu ý `codex exec` KHÔNG có flag `--model-provider` (bị reject), và `-p "text"` bị hiểu là `--profile`.
- `codex exec` với prompt qua stdin redirect `< prompt.md` + `--ephemeral --sandbox read-only` cho audit.

## Serial mapping máy 1-5 (D:\OneDrive\Tiktok\Tik1.xlsx sheet TaiKhoan, cột device ID)

máy 1 `9885b64957334f5a46`, máy 2 `9885e6303951513337`, máy 3 `9885e6344655484754`, máy 4 `9885e6484432423046`, máy 5 `9885e64b4a434a3037`.

Workbook run_safe (D:\\OneDrive\\TaadaaData\\kibe\\taikhoan_run_safe.xlsx) mapping (máy,row→nick): máy 3 row 1 = `trangtran168432`, row 2 = `ninhy05100`, row 3 = `lequynh2043` (khớp 3 nick trong switcher).

## Follow hook máy 3: feed SUCCESS nhưng follow MANUAL_REVIEW identity_mismatch

Sau khi fix classifier, chạy lại máy 3 đúng cách (`-Row 1 -Machines 3`, không Preset/LocalRun):
- Feed session: **success 29/29 swipe** — switcher tự chọn `trangtran168432` (row 1), `verify_profile` "profile matched account".
- But **follow hook FAIL**: `follow_result.json` → `exit_code:1 status:MANUAL_REVIEW reason:"MANUAL_REVIEW: exact profile identity không khớp sau tap"`, `follow_failed:true`, followed 0, failed 0, failed_ids [].

Luồng follow (tiktok-follow repo, mode 1 search-follow):
- `follow_runner/flows/mode1_search_follow.py` `run_mode1`: đọc **UID từ safe workbook** (cột ID toàn bộ nick hợp lệ), budget/session random; `follow_one_uid` → `_nav_search(uid)` (tap icon search → type uid → tap result) → `_classify_exact_profile_action(profile_xml, uid)` → nếu `identity_mismatch` = "skipped ID không khớp" (chỉ bỏ qua); nếu `not_followed` → `_tap_follow_button` → `verify_after_tap` (verify_follow.py:218-330, identity-bind mọi fresh dump) → `classify_button(_dump())` fresh → "followed" → `_confirm_not_released` (swipe+check lại); "identity_mismatch" → `MANUAL_REVIEW: exact profile identity không khớp sau tap` (dòng 296) — KHÔNG retry, KHÔNG skip.
- **Phân biệt 2 nơi trả identity_mismatch**: `follow_one_uid` step 2 (sau search, TRƯỚC tap follow) → "skipped: ID không khớp" (KHÔNG dừng session, chỉ failed_ids); `verify_after_tap` step 3 (SAU tap follow) → MANUAL_REVIEW (dừng session, follow_failed=true). Máy 3: lỗi ở verify_after_tap → dừng.
- Chẩn đoán khi gặp: (a) sau tap follow, dump UI mới không còn là profile target — có thể popup (mời bạn bè/login), hoặc navigate sang màn khác; (b) `classify_button` chỉ tin action button id (`id/fds`/`id/ff8`) — TikTok render thay đổi → `unknown` → reload → vẫn lạ → MANUAL. (c) Session id 32 state file `follow_state_32.json` là của MÁY 3 (không suy từ số) — xem `follow_runner/runs/state/` + timestamp, và rất dễ nhầm vì state filename dùng máy trong đợt 73 máy. 
- **Trạng thái cuối (17/08)**: máy 1/2/5 feed+follow PASS; máy 3 feed PASS nhưng follow cần điều tra thêm (chưa xong — nếu làm tiếp: xem artifact screenshot lúc identity_mismatch, kiểm tra action button id trên profile thật, có thể do nick target (UID) search ra profile khác). Máy 4 bỏ qua (user). Cron 3 job đã staged paused nhưng CHƯA resume — kế tiếp cần user duyệt resume + P6 cutover.