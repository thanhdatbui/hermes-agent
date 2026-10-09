# Exact-target canary and fallback proof

## Lesson from failed canaries

A nearby hook is not a proof of the changed behavior. `nav_search` proves only search navigation. It does not prove Mode 2 → Mode 1 fallback, budget top-up, or a real Follow action.

## Required live proof for partial fallback

Run the real follow runner with an explicit account row and a bounded fixed session budget. Accept PASS only when the same result contains:

- `mode2_fallback_to_mode1 == true` (or an equivalent transition event);
- `mode1_followed_count > 0`;
- `followed` contains newly followed UID(s);
- `follow_failed == false`, with no cooldown or removed-follow signal;
- a fresh 1080x1920 screenshot and matching UI/XML captured while TikTok is awake on the target result, before teardown.

`status=OK`, process exit 0, the fallback flag alone, `followed=[]`, or a Launcher/Home screenshot is not proof.

## Canary runner contract

For `--canary-hook`, bind `--account-row-index` explicitly, avoid stdin prompts, run bounded startup (`prepare_device`, `open_tiktok`, popup dismissal), bind the selected row directly, then invoke the hook. Do not add a separate identity-switcher gate when the parent/feed preflight already selected the account; that tests a different path. Reject screenshots from Launcher, Dozing, Splash, blank/off screens, or tiny files.

## Failure classification

- Startup/identity failure: follow modules were not run.
- Timeout starvation: fallback was selected but Mode 1 was skipped.
- `mode1_followed_count == 0`: no live Mode 1 follow proof.
- Three UI failures stop only the blind retry loop for that device/account; offline diagnosis, scoped repair, and independent work continue.
