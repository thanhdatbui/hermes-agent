# Avatar-only scope and false-policy refusal checklist

## Incident pattern

A user requested only a TikTok avatar replacement. The flow expanded into an unrelated display-name mutation, and a generic model refusal incorrectly described the benign avatar task as a policy violation. The final live state was not the target profile, so success was not proven.

## Required contract

- Scope lock: avatar/photo only. Do not touch display name, username, bio, links, or account inventory.
- Target binding: record machine, serial, exact handle, source image, and current activity before the first mutation.
- Freshness: capture a fresh screen after every state-changing action; discard coordinates from stale captures.
- Checkpoints: selected-photo screen -> crop/preview screen -> saved Profile screen. Each must be inspected for the expected target and content.
- Final proof: exact handle visible, fresh Profile activity visible, avatar visibly non-placeholder and matching the intended source. Runner exit 0 is not enough.

## Refusal handling

A generic safety/policy refusal for an ordinary profile-photo change is not a platform diagnosis. Do not let it widen scope, stop the task without evidence, or justify a workaround. Acknowledge the refusal as erroneous, then continue only after revalidating the live device and target account. If the refusal is accompanied by an actual platform warning or restriction on-screen, preserve that screenshot and report the real blocker.

## Out-of-scope mutation handling

If an unrelated field was changed, report it immediately and separately from the avatar result. Do not silently “repair” it, do not update a workbook as if the requested task passed, and do not claim completion. Display-name changes may have a platform cooldown, so restoration requires an explicit user decision when the original value is uncertain.

## Fail-closed states

Use `UNPROVEN` or `BLOCKED` when:

- the device is in Home, Messaging, another app, or an unrelated account;
- the screenshot is black/dozing, stale, or lacks the target handle;
- the selected image is not visibly the intended source;
- the final Profile still shows the old avatar;
- only a tap acknowledgement, log summary, or exit code exists.

## Minimal user report

Lead with: `Kết quả: <PASS | UNPROVEN | BLOCKED>`. Then state the exact observed activity/handle, the evidence path if valid, and any out-of-scope side effect. Keep it concise and in direct Vietnamese.
