# Avatar runner lifecycle and exact-account identity binding

## Session-derived failure pattern

A canonical avatar-smoke run on one machine reported all of the following:

- the workbook row and target account were resolved correctly;
- the source path was resolved to the render-folder avatar;
- force replacement entered the edit-profile, gallery, crop, and save stages;
- the runner logged avatar upload success and updated `Avatar = OK`;
- the run report still contained `post_verified: false`;
- the runner then force-stopped TikTok and returned the device to Home before an independent profile screenshot was captured.

A later ad-hoc verifier relaunched TikTok and captured a different account. That screenshot was not valid evidence for the target account, even though the original runner's mechanical upload log was successful.

## Durable rule

The post-action screenshot/XML must be produced by the canonical runner before teardown, under the same run/attempt namespace, with the target account identity still bound. A fresh screenshot from a later session is acceptable only if it independently proves the exact target username and the expected mutation; a screenshot of another account, SplashActivity, Launcher/Home, black/dozing output, or an unconfirmed switcher is `UNPROVEN`.

## Required evidence fields

- machine number and ADB serial;
- workbook physical row and Tik slot;
- target username/display name;
- exact source asset path and source hash when available;
- pre-action profile identity evidence;
- post-action UI XML path and screenshot path from the same attempt;
- post-action identity match;
- semantic asset/mutation match;
- teardown timestamp after evidence capture;
- final verdict: `DONE`, `UNPROVEN`, or `BLOCKED`.

## What not to do

Do not treat runner exit code, `verified=True`, workbook `Avatar = OK`, or a crop/save receipt as the final semantic verdict. Do not write a one-off verifier that taps guessed coordinates or assumes the currently visible profile is the target. If the canonical runner lacks capture-before-teardown, patch that runner and add a focused mocked regression test rather than compensating with manual ADB taps.