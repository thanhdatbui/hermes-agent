# Follow release vs runner error

User correction: never equate a subprocess failure with TikTok releasing a follow.

- Release (`Nhả Follow`) is only the exact `status: FOLLOW_FAILED` emitted by the post-tap/post-refresh verifier after the action button returns to `Follow`.
- `MANUAL_REVIEW`, `TIMEOUT`, config/search/navigation/profile errors, missing `FOLLOW_RESULT`, and any non-zero exit without exact `FOLLOW_FAILED` are runner/verification errors.
- `SKIPPED` is a separate category for zero-video, cooldown, already-followed, lock, or safety gates.
- **Tik 3..6 Warmup Gate**: Trong 14 ngày đầu nuôi acc, nick thuộc Row 3, 4, 5, 6 (Tik3..6) chỉ lướt feed nuôi acc, tự động skip follow hook với `reason: tik{row}-warmup-feed-only`, không gọi tool follow.
- Keep Feed failure, Follow release, Follow runner error, and Follow skip independent; do not infer one from machine number or another hook.
- Legacy artifacts with `follow_failed: true` are ambiguous if older code overloaded the field with return code; inspect exact `status` before reporting.

Regression requirement: assert that `MANUAL_REVIEW` with exit code 1 is non-release and exact `FOLLOW_FAILED` remains release. Do not modify old artifacts or the original verifier/state contract merely to repair reporting.
