# Canary and fallback verification

Use this reference for TikTok follow canaries and Mode 2 → Mode 1 fallback verification.

## Valid targeted-hook canary

1. Bind the exact machine/account row. Targeted hooks must be non-interactive; treat `canary_hook` as a non-business path so stdin row prompts cannot occur. Pass `--account-row-index` when the row matters.
2. Run bounded startup before the hook: `prepare_device` → `open_tiktok` → popup dismissal. Bind the selected row identity on the engine. Do not add account-switcher verification unless identity switching itself is under test.
3. Invoke exactly one hook (`_nav_search`, `_open_following_tab`, etc.). A hook canary is not a full follow-session canary.
4. Capture the screenshot/XML while the target app/result screen is active. Launcher/Home/Splash/Dozing, post-teardown, or tiny blank screenshots are invalid evidence.
5. Require structured result + target-screen evidence. Exit code 0 alone is insufficient.

## Fallback proof levels

Report these separately:

- `mode2_fallback_to_mode1=true`: branch decision only.
- Module 1 invocation: the runner actually entered `run_mode1`.
- `mode1_followed_count > 0`: Module 1 successfully followed a target.
- Full-session pass: result and target-screen/readback evidence both pass.

Never call a fallback canary successful when `mode1_followed_count=0` or when the only screenshot is teardown/Launcher.

## Failure handling

After repeated live failures, stop only blind UI retries for that exact machine/row. Continue offline diagnosis, focused tests, and canary-contract repair; do not stop the overall task. Preserve the real status as `CANARY_FAILED`, `CONFIG_ERROR`, `TIMEOUT`, or `BLOCKED` rather than normalizing it to `OK`.
