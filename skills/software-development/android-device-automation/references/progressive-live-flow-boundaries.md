# Progressive live-flow boundaries

Use this pattern when the user says the equivalent of “run the real production flow; ask me when you actually reach a step that needs me.” It is a staged live authorization, not a request for more offline-only analysis and not blanket permission for every later business action.

## Interpret the authorization precisely

- A narrow request such as “launch TikTok for a probe” remains narrow: it does not authorize profile navigation, account switching, Follow/Post, reboot, destructive recovery, lock takeover, or credential entry.
- A progressive-flow request authorizes running the canonical production path through the already-safe/non-destructive stage and all mechanical prerequisites needed to reach the next real boundary. Do not ask pre-emptively about steps that have not been reached.
- Stop and ask only at an actual protected boundary: a Follow/Post or equivalent business mutation not explicitly authorized; account/identity ambiguity; OTP/2FA/CAPTCHA/secret; permission/payment prompt; reboot or destructive recovery; foreign/retained lock; takeover/release outside current ownership; or a choice that materially changes the target.
- The latest wording governs. Never use an older narrow authorization to broaden scope, but do not keep treating a new progressive-flow authorization as “offline verification only.”

## Execution sequence

1. **Finish the offline gate once.** Record exact suite/version/compile/diff evidence. Once green, move to live preflight instead of repeatedly auditing the same offline state.
2. **Resolve target identity without guessing.** Prefer canonical per-machine config. If that path is absent but approved mapping sources exist, read only the machine/serial fields, require two-source agreement when available, and do not read or print account IDs, UIDs, passwords, proxy secrets, or unrelated workbook columns. Report only a redacted serial suffix.
3. **Reconcile the exact live target.** Check exact machine-number parsing (avoid matching machine `1` inside `10`), both machine and serial lock aliases, exact process command line, ADB state, and device model. Never restart ADB or delete/take over a lock merely to pass preflight.
4. **Run the canonical production entrypoint.** Do not substitute an ad-hoc runner. Scope flags must stop before the protected business action (for example, `--startup-only` to reach and prove Feed with zero Follow).
5. **Verify the resulting state.** Read back absolute artifact paths, package/activity, structured-capture metadata, semantic state proof, business-action counters/absence, and ownership-aware lock release or `failed_locked` retention.
6. **Then ask at the boundary actually reached.** State what the next action would mutate and request only that decision.

## Evidence-based progress language

Use these states literally:

- `planned`: command/worker not launched.
- `worker_dispatched`: worker request accepted, but no proof of a device action yet.
- `preflight_complete`: identity/process/lock/ADB gates passed.
- `device_action_started`: a real target process, owned lease, or first live artifact proves execution began.
- `state_reached`: package/activity/UI evidence proves the named UI state.

Never report “đang mở TikTok” or “đang ở bước 1” from delegation acceptance alone. Say “worker đã được dispatch; chưa có bằng chứng chạm máy” until live evidence exists.

## Worker/transport failure reconciliation

If a worker returns an API/connection/transport error before a usable result:

1. Check the exact target process, both lock aliases, and newly created artifacts.
2. If all are absent and no device-side evidence changed, report `zero device action` and re-dispatch only after exclusivity is proven.
3. If any process/lease/artifact/action may exist, classify the attempt as unknown, retain ownership/locks, and do not launch a replacement in parallel.
4. A worker completion envelope, API-call count, or elapsed time is not action proof.

## Concise status format

Lead with the business boundary, then evidence:

- `Chưa vào Follow. Đã xong preflight; chưa có bằng chứng mở app.`
- `Đã tới Feed. Zero Follow; evidence: <PNG/XML/JSON>; lock đã release.`
- `Dừng tại <boundary>: cần bạn quyết định <exact action>.`

Do not bury the current step under test history. Include only the latest exact gate and the next protected action.