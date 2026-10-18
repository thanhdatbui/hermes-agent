# Mobile dashboard detail modal and runtime reload

## Use case
A local fleet dashboard exposes per-account history, quota, UID lists, or audit details. On mobile, a small icon plus a desktop-only two-column modal makes the feature effectively unusable.

## Reusable implementation pattern

1. Give the action a readable label such as `📜 Bệnh án`; retain the existing handler and title.
2. Make the entity card itself clickable where appropriate. Guard the card handler so clicks on links/buttons keep their original behavior: `if (!event.target.closest('a,button')) openDetail(...)`.
3. Keep desktop master-detail columns, then add a narrow-width breakpoint that stacks the body, makes the account list full width with a bounded height, removes the desktop right border, and lets the detail pane scroll vertically.
4. Use a near-viewport modal on mobile: `width:100%`, `height:min(94vh,900px)`, `max-height:94vh`, small backdrop padding, and a reduced header/content padding. Avoid relying on a fixed desktop `88vh` two-column layout.
5. **Interactive Group Filter Tabs (Pill Buttons) & Auto-Focus**: In master-detail sidebars with large entity pools (hundreds to thousands of accounts), never stack all categories into a single unsegmented vertical scroll list (forcing endless mouse wheeling past 900+ items).
   - Render horizontal filter pill buttons at the top of the sidebar for each cohort with counts: `[Tất cả (N)]`, `[🔴 Cooldown (N)]`, `[🟡 Hồi phục (N)]`, `[🟢 Khỏe (N)]`.
   - Toggle visibility to only render the active cohort's items when a pill is selected.
   - When launching the modal from an entity card, automatically detect the target account's cohort and default `fdFilterGroup` to that cohort so the selected account is immediately visible and isolated without scrolling.

## Verification recipe

- Read the exact source diff and confirm only the intended component/static asset files changed.
- Run the focused syntax check for embedded Python templates: `python -m py_compile <server-or-component>.py`.
- Start a fresh isolated dashboard instance on a separate port when restarting the default listener is not safe; this separates source correctness from stale process memory.
- Hard-reload/navigate the browser and verify the rendered readable action label, card clickability, modal title, selected username, list/detail panes, and legible content.
- Use vision on the exact post-action screenshot before sending it. Reject black, clipped, stale, or unrelated screens.
- If the default port still shows old markup while an isolated fresh port shows the new markup, report `source-fixed/runtime-stale` and do not claim production rollout.

## Common pitfalls

- Changing the source does not hot-reload HTML/JS/CSS already held in a running Python daemon.
- A browser snapshot can prove DOM labels but not visual legibility; pair it with a fresh visual inspection.
- A card-level click handler can hijack the TikTok link or secondary chart/detail buttons unless it excludes `a,button` targets.
- A successful worker summary or `py_compile` proves neither browser rendering nor runtime freshness by itself.
