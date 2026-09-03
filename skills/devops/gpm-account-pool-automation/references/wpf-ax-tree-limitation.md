# WPF AX Tree Limitation — GPMLogin v4.3.6 Custom Dialogs

## Finding (2026-09-02)
GPMLogin v4.3.6 uses custom WPF rendering for internal dialogs (browser update, license validation, etc.). The dialog buttons **do not appear in the UIAutomation / AX tree** — only sidebar menu items (`btnMenuProfiles`, `btnMenuSetting`, etc.) are exposed.

## Evidence
- `computer_use(action="capture", mode="som", app="GPMLogin")` returns 0 elements over the update dialog
- PowerShell UIAutomation enumeration shows only 62 descendants total — all sidebar/menu items
- No dialog buttons (Cập nhật, Hủy, Tải xuống, etc.) appear in the tree
- Physical coordinate clicks on known button positions had no effect on AX tree state

## Implication for Automation
**Do not rely on `computer_use` / UIAutomation to click GPM internal dialogs.** They are effectively invisible to accessibility automation.

## Workaround
1. **Direct Chrome launch bypass** (verified working): Launch the GPM Chrome core binary directly via subprocess with `--remote-debugging-port` and `--user-data-dir` pointing to the profile folder. Connect Playwright over CDP. This completely bypasses GPM API and the update dialog.

2. **Manual user click**: Ask the user to click the update button in the GPM UI before running automation.

3. **Future GPM versions**: Verify dialog AX accessibility before building automation that depends on clicking them.

## Related
- Skill: `gpm-account-pool-automation` — Section 15 (API bypass) and Section 16 (WPF limitation)
- Tool: `computer_use` — Failure mode entry for custom WPF dialogs