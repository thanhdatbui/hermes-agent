# Preserve-scene cross-component debugging

Use this when a live feed run should stop at a blocker and preserve the scene, but a later alert screenshot shows Android Launcher/Home.

1. Read the target-scoped JSONL at the failure boundary. Confirm `cleanup_close_all=skipped`, `preserve_blocker_screen=true`, and the skip reason `preserve_blocker_screen`.
2. Compare the last verified in-flow package/screen with the alert image. Distinguish TikTok Home/For You from Android Launcher/Home.
3. Search the full execution tree for independent Home senders: TTL/dead-owner reaper, recovery hard-stop, timeout hooks, follow/upload hooks, cache jobs, and wrapper finalizers. Search semantic APIs and raw `keyevent 3`/`KEYCODE_HOME`.
4. Correlate timestamps, lock owner/TTL, machine, and serial. Label candidates `confirmed`, `excluded`, or `unproven`.
5. Do not blame local cleanup when the log proves it was skipped. In live work, capture evidence and stop; do not rerun, probe, or modify without explicit authorization.

For `profile verification mismatch`, a feed log may show the blocker and skipped cleanup while a later alert shows Launcher/Home. That proves the local feed cleanup was excluded, but not which external actor caused the later transition. A `blocked` lock with `owner_active=true` excludes an immediate dead-owner reaper at the failure timestamp, not necessarily a later TTL/recovery action.
