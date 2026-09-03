# Follow Incident Routing & Canary Discipline

## Hard-Routing Seam
When an alert with `• Script: tiktok-follow` arrives:
- Repo: `D:\Taadaa\tiktok-follow`
- Runner: `follow_runner/run_follow.py`
- Arguments: `--machine <N> --mode 2 --config config/machine<M>.yaml --account-row-index <slot>`

## Invariant
- Never invoke `tiktok-luot nuoi acc` / `run_tiktok.py` when fixing or verifying `tiktok-follow` incidents.
- State in `follow_state_<machine>_row_<slot>.json`:
  When verifying `FOLLOW_FAILED` reset or re-running canary, inspect and reset `follow_failed` and `follow_failed_date` in the per-slot state file if testing a fresh attempt.
