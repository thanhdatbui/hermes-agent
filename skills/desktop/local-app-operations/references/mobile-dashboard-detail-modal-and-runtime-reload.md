# Mobile dashboard detail modal and runtime reload

## Use case
A local fleet dashboard exposes per-account history, quota, UID lists, or audit details. On mobile, a small icon plus a desktop-only two-column modal makes the feature effectively unusable, and operators dislike hunting for tiny icons inside cards.

## Reusable implementation pattern

1. **Promote deep inspection views to a first-class Dashboard Tab (Full-Page View Pattern):**
   - When master-detail records contain dense data (quota breakdowns, long UID tables, health history) that operators check regularly, do not trap them in a popup/modal.
   - Add a top-level tab button on the main toolbar (e.g. `📜 Sổ Bệnh Án` -> `setView('follow_records')`) right next to the related fleet overview tabs.
   - Embed the master-detail HTML directly inside a full-page container (e.g. `<div id="followRecordsContainer" class="fleet-container" style="display:none;">`) rather than a fixed-position popup (`.modal-backdrop` with `100vw/100vh`).
   - The close button (`&times;`) in the card header should act as a breadcrumb returning to the parent overview (e.g. `onclick="setView('follow_health')"`).

2. **Cross-view deep linking from overview cards:**
   - Keep inspection buttons or clickable cards on the overview page (`🩺 Sức Khỏe Follow`), but instead of launching an isolated popup, have them seamlessly route to the dedicated view tab:
     ```javascript
     function openFollowDetailModal(machine, row, username) {
         fdSelectedKey = fdAccKey(machine, row || 1);
         setView('follow_records');
         selectFdAccount(machine, row || 1, username);
     }
     ```
   - Make the entity card itself clickable where appropriate. Guard the card handler so clicks on links/buttons keep their original behavior: `if (!event.target.closest('a,button')) openFollowDetailModal(...)`.

3. **Master-Detail Layout with Mobile Stacking:**
   - Keep desktop master-detail columns (340px left pane, flex-1 right pane).
   - Add a responsive breakpoint (e.g. `@media (max-width: 900px)`) that stacks the body vertically (`flex-direction: column`), makes the account list full width with bounded height (`max-height: 34vh`), removes the right border, and adds a bottom border.
   - Set the card bounds: `width: 100%`, `height: min(78vh, 780px)` (or `height: auto` on mobile stack) with clean scroll areas.

4. **Interactive Group Filter Tabs (Pill Buttons) & Auto-Focus:**
   - In master-detail sidebars with large entity pools (hundreds to thousands of accounts), never stack all categories into a single unsegmented vertical scroll list (forcing endless mouse wheeling past 900+ items).
   - Render horizontal filter pill buttons at the top of the sidebar for each cohort with counts: `[Tất cả (N)]`, `[🔴 Cooldown (N)]`, `[🟡 Hồi phục (N)]`, `[🟢 Khỏe (N)]`.
   - Toggle visibility to only render the active cohort's items when a pill is selected.
   - When navigating to the tab or selecting an account, automatically detect the target account's cohort and default `fdFilterGroup` to that cohort so the selected account is immediately visible and isolated without scrolling.

## Verification recipe

- Read the exact source diff and confirm only the intended component/static asset files changed.
- Run the focused syntax check for embedded Python templates: `python -m py_compile <server-or-component>.py`.
- Run architecture and regression tests: `pytest tests/test_dashboard_architecture_gate.py`.
- Start a fresh isolated dashboard instance on a separate port when verifying changes before restarting the default listener; this separates source correctness from stale process memory.
- Hard-reload/navigate the browser and verify the tab button in the toolbar, full-page embedded rendering, card clickability, selected username, cohort pill filtering, and legible content.
- Use vision on the exact post-action screenshot before sending it. Reject black, clipped, stale, or unrelated screens.
- If the default port still shows old markup while an isolated fresh port shows the new markup, restart the target listener PID cleanly and re-verify.

## Common pitfalls

- Changing the source does not hot-reload HTML/JS/CSS already held in a running Python daemon on Windows. Kill the listening PID explicitly before testing production rollout.
- A browser snapshot can prove DOM labels but not visual legibility; pair it with a fresh visual inspection via vision.
- A card-level click handler can hijack the TikTok link or secondary chart/detail buttons unless it excludes `a,button` targets.
- Stacking 1,000+ accounts in a single scroll container without cohort tabs triggers immediate operator frustration ("r sao k chia từng nhóm mà bắt tao kéo chuột tìm"). Always provide pill filters.
