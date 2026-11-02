---
name: live-profile-mutation-recovery
description: "Use for live TikTok profile mutation recovery."
---
# Live TikTok Profile Mutation Recovery

Use this class-level workflow for pinning videos, changing avatars, editing profile metadata, or any other live mutation on a farm Android device when target identity, UI state, and post-action result must be proven.

## Non-negotiable completion contract

A dry-run, worker exit code, queue state, workbook flag, or local asset marker is not completion proof. Completion requires:

1. Exact machine/serial mapping from the canonical O(1) inspection tool.
2. Fresh UI evidence showing the intended account and intended profile surface before mutation.
3. The live action performed through the bounded runner with the correct device lock.
4. Independent post-action read-back from the exact account.
5. A fresh screenshot inspected with vision/OCR showing the expected result and no popup, black screen, clipping, or wrong account.

If any identity or read-back gate is missing, report `BLOCKED` with the actual error and evidence path. Never infer success.

## Runner lifecycle and exact-account closeout contract

The canonical runner must capture its own post-mutation evidence **before** force-stop/HOME/teardown and must carry the target identity through that capture. A later ad-hoc verifier that relaunches TikTok, guesses a profile tab, or uses an unbound account switcher can land on another farm account and create a false failure or false success. Therefore:

1. Bind `machine -> serial -> workbook row/slot -> target username -> source asset` in the run artifact before launch.
2. Confirm the target identity on the live Profile immediately before mutation.
3. Perform the mutation, then capture fresh UI XML and screenshot on that same target surface before cleanup. Persist both under the same attempt/run ID.
4. Verify exact username/display identity and expected avatar/pin marker from those fresh artifacts. Only after this gate may the runner update workbook state or teardown.
5. If the runner's current lifecycle tears down first, classify the result as `UNPROVEN`; the durable fix belongs in the canonical runner's closeout hook, not in a one-off script that taps guessed coordinates after the fact.

`exit=0`, `verified=True`, `FORCED_REPLACED_VERIFIED`, `Avatar=OK`, or a successful crop/save log are mechanical receipts only. They cannot override `post_verified=false`, a black/Home/Splash screenshot, or a screenshot showing another account. See `references/avatar-runner-lifecycle-and-identity-binding-20261021.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
