# Mode 1 Search-Follow Re-Audit — APPROVED (2026-08-15, post-fix)

Re-audit read-only của canonical Mode 1 TikTok Follow (`D:\Taadaa\tiktok-follow`)
SAU vòng fix từ findings doc `tiktok-follow-mode1-audit-20260815.md`. Không sửa
file, không live/ADB/workbook. Verdict: **APPROVED** (token dòng đầu tiếng Việt,
rồi file:line + verification bắt buộc).

## Evidence

- HEAD `07b23a1259061ee0c7e1f5213e1c1da25a559593` (master), dirty worktree
  pre-existing (docs + follow_runner + tests).
- Full suite: **241 passed** trong 132.40s; targeted identity/budget/ambiguity:
  **35 passed**; `py_compile` PASS; `git diff --check` PASS (chỉ CRLF warnings).

## Verified implementation (file:line working tree)

### Canonical flow reuse automation-core account-ready (KHÔNG rewrite)
- `follow_engine.py:605-657` `run_session`: `prepare_device` → `open_tiktok`
  (guard monotonic 60s trong feed deadline 90s; ladder B1→B2→B3 có proof) →
  `popup.dismiss_all` → `switch_account_and_verify(row.tik_id)` →
  `active_account_handle = row.tik_id` → `run_mode1`.
- `follow_engine.py:218-287` `_core_switcher`/`_canonical_switch_verify` = đúng 3
  public core API (`open_account_switcher` / `select_exact_account` /
  `verify_selected_account`), core retries pin 1/1/1, ladder B1
  `_recover_account_capture_backend` (adapter.recover_ui_dump /
  recover_persistent_ui) → B2 `_recover_account_relaunch` (prepare_tiktok +
  fresh feed window) → B3 `_run_reboot_recovery`
  (reboot_and_restore_guarded, chỉ khi `allow_device_reboot_recovery`).
  Chỉ các recoverable codes mới advance ladder; signature khác propagate.
- Account-ready path KHÔNG bị rewrite: `run_account_ready_only:566-603` giữ
  evidence `zero_business_actions: {search: False, follow: False}`,
  `followed: []`, final identity recapture qua `verify_selected_account`;
  không FollowState, không workbook lease, không load UID.

### Exact search UID → exact profile identity → đúng 1 Follow → verify identity-bound
- `_wait_search_result` `mode1_search_follow.py:188-261`: candidate = có bounds +
  `class != EditText` + không `editable` + `normalize(text)==normalize(uid)`
  (strip @ + casefold). Đúng 1 → resolve clickable ancestor, rồi ưu tiên đúng 1
  descendant clickable bọc đúng 1 ImageView cùng bounds (semantic avatar cho
  Top-result card); >1 avatar → chờ/fail-closed; timeout/mơ hồ → None.
- **EditText echo**: input search đang focus echo đúng UID đã gõ ở `@index=0` —
  KHÔNG bao giờ là result target (test `test_nav_search_live_suggestion_index_zero_is_opened`).
- **`tvl_unified_sug` one-shot** `mode1:147-157`: tap suggestion unified có thể
  chỉ submit sang Search Top → re-evaluate ĐÚNG 1 lần một exact result; result
  trực tiếp là terminal; không bao giờ diễn giải node identity trên profile
  thành target thứ hai.
- `_classify_exact_profile_action` `mode1:166-185`: `profile_identity_from_xml`
  + `username_element.resource_id` kết thúc `id/sf5` + ĐÚNG 1 node sf5 có text +
  normalized username == uid; sai → `identity_mismatch` → manual, không tap.
  **Caveat core helper**: `profile_identity_from_xml` trả element text bắt đầu
  `@` ĐẦU TIÊN (`automation_core/tiktok/profile.py:12-15`) — chính cặp check
  sf5/element mới chặn bio/comment bắt đầu `@` bị coi là username.
- `_tap_follow_button` `mode1:317-338`: exact token match (set intersection của
  giá trị normalized text/content-desc) với `{follow, follow lại, theo dõi}`;
  clickable + bounds; `len(matches)==1` else False. Không substring →
  "Follower" không bao giờ match.
- `verify_after_tap` `verify_follow.py:57-131` + `classify_fn` bound: MỌI dump
  mới (sau tap, sau reload) phải re-prove identity == UID rồi mới đọc nút;
  followed → success chỉ từ profile đã prove; identity_mismatch → manual;
  unknown → reload 1 lần (tính budget) rồi manual; not_followed → reload loop
  tới `cfg.verify_reload_retries` → FOLLOW_BLOCKED + `state.set_follow_blocked()`.
- `classify_button` `verify_follow.py:37-54`: exact marker sets; clickable+bounds;
  đúng 1 state → else unknown.

### Active account excluded; không Follower confusion; fail-closed; budget
- `follow_uids` `follow_engine.py:337-349`: `uid_source_mapping.tik_ids()` (full
  safe workbook, deduped) trừ active handle (strip @ + casefold). Production
  symbol `active_account_handle` được set ở `run_session:636`; test
  `test_follow_engine.py:557-579` phủ exclusion.
- `run_mode1` `mode1:35-65`: budget = min(budget_per_session,
  state.budget_remaining()); skip followed/skipped; followed → mark+consume;
  blocked → DỪNG toàn session (FOLLOW_BLOCKED); skipped → marked; **manual →
  MANUAL_REVIEW (KHÔNG ghi skipped, giữ handoff)**; swipe context fail →
  MANUAL_REVIEW, không swipe mù.
- FollowState: rollover theo HOST clock + timezone, save atomic
  tmp + `os.replace` (`follow_state.py:47-51`).

### Mode 2 interplay (read-only note, ngoài scope Mode 1)
- `run_mode2` `mode2:524-695`: gate `res.status != "OK" → return res` (không
  follow sau MANUAL_REVIEW); session budget = `budget_per_session -
  len(res.followed)` (trừ phần mode 1 đã dùng); `_back_to_feed` trước mỗi seed;
  `_open_follower_tab` tái dùng `_nav_search` + sf5 identity gate TRƯỚC tap tab
  Follower; verify row-scoped qua tcj (không classify toàn màn); `_path_b_verify`
  mở profile → exact identity → classify → back đúng 1 lần → verify restoration.

## P2 non-blocking findings (ghi nhận, không cần fix)
- `mode1_search_follow.py:206`: bắt `ET.ParseError` cùng `FollowAdapterError` —
  dead-code hardening (dump_ui đã đảm bảo hierarchy, adapter.py:132).
- `verify_follow.py:116-127`: nhánh unknown→reload→unknown trả manual không
  consume budget reload — vô hại (manual không bao giờ mark), đã ghi nhận.
- `mode2:365-367` `_scroll_follower_list` dùng `swipe_feed` (5/6→1/5 chiều cao,
  theo screen size thật) — an toàn, ngoài scope Mode 1.

## Verification bắt buộc trước live (lặp từ audit)
1. Process `tiktok_workflow --machine 1` không sống (gate SKIPPED_BUSY,
   follow_engine.py:617-620).
2. Config = `config.example.yaml` (swipe_before_search/between,
   verify_reload_retries=2, budget).
3. Live chỉ qua canonical entrypoint
   `python run_follow.py --machine 1 --mode 1 --config <cfg>` (rule canonical
   script AGENTS.md:192-198).

## Reusable audit workflow probes (đã chạy chuẩn 2 vòng)
- **Dirty-tree failing tests = contract spec**: vòng 1 chúng là 5 test đỏ mới từ
  parent edits (định nghĩa invariant cần fix); vòng này chúng xanh (241 passed)
  → contract ĐÃ implement. Luôn `git status --short` trước.
- **Green-for-wrong-reason**: test set `active_account_handle` nhưng production
  `__init__` không tạo attribute → vòng 1 kết luận gate chưa tồn tại; vòng này
  verify symbol production (`run_session:636`) trước khi tin test.
- **Cross-mode asymmetry**: Mode 2 có sf5 gate là chuẩn; so Mode 1 với Mode 2
  trong cùng repo phát hiện gate thiếu nhanh.
- **Read-only discipline**: git rev-parse/status/diff, read_file, pytest offline,
  py_compile, git diff --check; không sửa file, không live/ADB/workbook.
- **Verdict format**: 1 dòng token tiếng Việt (APPROVED/MINOR_FIXES/REJECT) rồi
  file:line chính xác + verification bắt buộc.
