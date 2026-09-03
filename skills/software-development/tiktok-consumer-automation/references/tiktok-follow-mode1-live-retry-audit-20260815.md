# tiktok-follow Mode 1 live-retry gate audit — vòng 4 (2026-08-15)

Verdict: **APPROVED** cho 1 live retry real-Follow máy 1 (sau failure live +
canonical search-submit repair). Read-only: không edit, không đụng device,
không commit, không đọc workbook/credential, `uids.txt`/`NUL` chỉ check tồn tại.

## Signature failure live (artifact `%TEMP%\tiktok-follow-m1-failure1-20260815-090848\`)

Đếm bằng python trên `ui.xml` byte-exact (CRLF, 56890 bytes, cùng giờ với
`screen.png` 175878 bytes):

- `tv_search_textview`: **đúng 1** — `text="Tìm kiếm"`, class
  `android.widget.Button`, `clickable="true"`, bounds `[775,84][1080,216]`.
- `android.widget.EditText`: **đúng 1**, focused, text = UID echo (`lequynh2043`),
  bounds `[150,96][775,204]` — chứng minh "exact UID chỉ nằm trong input".
- 9 suggestion `tvl_unified_sug` đều **approximate** (lêquynh204, mailequynhnhu2043,
  lê quynh2003, le quynh 2024, …) — KHÔNG có suggestion exact.
- Node `xdx` "TikTok Tako" (Button, clickable, bounds `[522,1662][1056,1782]`)
  là bẫy tiềm năng cho selector class=Button — nhưng không trùng resource-id,
  không trùng text label → vô hại.

## Fix đã verify (mode1_search_follow.py, working tree)

- `_nav_search` L148-155: dump mới → `_exact_search_result_from_xml` (không có
  exact) → `_unique_search_submit` → nếu đúng 1 → `tap_center` + sleep 2 →
  `_wait_search_result` 12s. Không submit khi đã có exact suggestion (giữ nhánh
  một-tap cũ).
- `_unique_search_submit` L202-217: match = bounds AND clickable AND class
  `android.widget.Button` AND resource suffix `id/tv_search_textview` AND text
  normalized ∈ {tìm kiếm, search}. 0/2+ match → None → KHÔNG tap (fail-closed).
  **An toàn so với icon feed**: icon "Tìm kiếm" (content-desc, L128-133) là node
  khác — không phải Button class, không có resource-id này → không bao giờ bị
  chọn làm submit; input là EditText → bị loại bởi class filter.
- Mọi gate khác (exact non-input result L220-275, profile identity `id/sf5`
  L180-199, đúng 1 Follow clickable L346-367, fresh identity-bound verify
  verify_follow.py:94-131, active-account exclusion follow_engine.py, budget
  1-attempt run_mode1 L35-71, lockless `SKIPPED_BUSY`, feed precondition
  `ensure_feed_for_follow` → `_back_to_feed`) giữ nguyên từ vòng 2/3.

## Verification đã chạy (tự chạy lại, không tin số cũ)

- Full suite: **245 passed / 154.67s** (mode1 35, verify+cli 35, config+workbook
  35, engine 40, lock+mode2 71, adapter 12).
- `py_compile` PASS, `git diff --check` PASS (chỉ CRLF warning).
- Wheel 0.4.44 trong `dist/` khớp installed site-packages: hash profile.py
  `aa06ee9663bf1c8b6278a9c4fb1f252b` giống hệt; nhưng `pip show` = 0.4.43
  (runtime env chưa cài đúng wheel — P2 vận hành).
- RED→GREEN: `test_nav_search_submits_exact_uid_before_waiting_for_results`
  (test_mode1 L254+) mô phỏng CHÍNH XÁC dump failure thật (EditText echo +
  Button tv_search_textview + suggestion approximate `u_targe`), assert taps
  `[(975,175),(927,150),(135,483)]` = icon → submit → avatar.

## Findings (P1 = không có)

- **P2-1**: `docs/ui-compatibility.md` chưa có record cho nhánh submit
  `tv_search_textview` (L275 chỉ nhắc như signature Back-stack; record Mode 1
  L298-307 không đề cập submit) — vi phạm binding AGENTS.md "selector change
  phải cập nhật local registry". Bổ sung record trước/sau live retry.
- **P2-2**: runtime env `automation-core` 0.4.43 ≠ pin 0.4.44 (profile.py hash
  khớp nên không ảnh hưởng fix, nhưng cài đúng wheel trước live).
- **P2-3**: `config.example.yaml` mặc định `mode: "both"`, `budget_per_session:
  10` — live retry phải dùng config thật `mode: "1"`, `budget_per_session: 1`
  (repo không chứa config thật, chỉ example).

## Kỹ thuật dùng lại: artifact-replay classifier verification

Trước khi đọc code fix, chạy chính các predicate sản xuất trên artifact
failure byte-exact (đếm node bằng regex/python trên `ui.xml` — không cần thiết
bị chạy flow): `tv_search_textview` count, EditText count/focused, suggestion
texts, node class/bounds. Việc này chứng minh (a) fix selector khớp signature
thật, (b) không có cạnh tranh selector nào khác trên màn đó. Sau đó mới đối
chiếu code + test RED→GREEN mô phỏng đúng dump.
