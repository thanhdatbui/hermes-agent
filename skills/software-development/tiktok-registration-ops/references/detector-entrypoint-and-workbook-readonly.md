# Detector entrypoint and workbook read-only verification

Use this reference before answering “máy nào còn mail Hotmail chưa reg”.

## 1. Resolve the entrypoint on the active revision

`_detect_clean.py` and `_run_all_targets.py` are not guaranteed to exist on every branch. Before invoking either:

```bash
git branch --show-current
git ls-files | grep -E '(^|/)(_detect_clean|_run_all_targets|_detect_all_targets)\.py$'
```

If the detector is absent, do **not** invent an OpenPyXL reader or silently copy a detector from another branch. Locate the exact canonical revision/runtime that owns the target policy, verify its dependencies and host-path behavior, and report the revision used for the read-only result. A result from another revision is not proof about the active branch unless the policy/path behavior is explicitly checked.

## 2. Use the host configuration first

For the Kibe machine:

```bash
TAADAA_HOST_CONFIG='D:/Taadaa/machine-config/kibe.yaml'
```

Set it before importing/running the detector. It selects the host `workbook_root` and prevents accidental reads from legacy workbook locations. Never print passwords, OTPs, or full mailbox credentials from the manifest/log.

## 3. Workbook lock/read failure

The detector is read-only, but Excel/OneDrive can still hold a workbook open. If the canonical detector reports a workbook read/permission failure:

1. Close the named workbook in Excel/preview/sync-conflict UI.
2. Rerun the same canonical detector with the same host config.
3. Keep the original exit code and report the exact blocker if the retry still fails.

Do not switch to a custom parser or conclude that machines are ineligible merely because the workbook was temporarily locked.

## 4. Interpret the result conservatively

The standard policy is:

- source-backed mailbox;
- password present;
- TikTok ID empty in tracking;
- at most one selected target per machine.

Report provider/STT from the redacted selection manifest. “TikTok ID empty” means “pending according to current tracking”; it is not independent proof that the mailbox has never been registered. If the target list conflicts with a confirmed recent registration, verify tracking by mailbox and stop that target rather than rerunning registration.

## 5. Evidence boundary

A detector result proves only the workbook-based candidate selection. It does not prove live TikTok state, mailbox classification, OTP freshness, or registration success. Live registration still requires the canonical `social_reg_v1.py` flow and its per-machine evidence.
