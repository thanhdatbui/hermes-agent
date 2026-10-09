# ChatGPT Direct-Reg: Bounded Parallel Workers & Evidence Contract

## Trigger
Use when the operator requests a real (non-dry-run) ChatGPT direct-email registration retry with a fixed small account set, one worker per account, and proxy isolation.

## Selection gate
1. Read the authoritative workbook once, preferably the production candidate function or one bounded Excel pass; do not enumerate the whole GPM pool.
2. Resolve each selected email to exactly one GPM profile ID/name and read its `raw_proxy` from the GPM API/DB.
3. Reject Daniel/DONE and known `CHATGPT_READY` evidence before launch.
4. Require password existence and require five distinct raw proxies. Do not rely on profile name alone: duplicate email→profile rows are possible.
5. Persist a pre-launch manifest containing email, profile ID/name, raw proxy, command, and evidence paths.

## Launch contract
- Launch exactly the requested bounded set with `subprocess.Popen`, at most 5 concurrent children.
- Invoke the canonical script directly once per email:
  `python D:/Taadaa/GPM auto/scripts/chatgpt_gpm_direct_reg.py --email EMAIL`
- Do not use the script's batch/limit mode and do not add Google SSO or ad-hoc runner logic.
- Keep the `Popen` object in the worker record under a dedicated key (for example `_process`). Never overwrite/omit the handle before polling; otherwise collection can fail before exit codes are captured.
- Capture stdout and stderr separately to per-email files, and retain the exact command line.
- Wait with a bounded deadline and emit periodic heartbeat evidence. On deadline, report each still-running PID and command; do not return an empty summary and do not run an unbounded retry loop.

## Result collection
For every child, collect and report:
- `returncode` (or explicitly `UNKNOWN` if the coordinator failed before collection);
- complete stdout/stderr artifact paths and relevant tail text;
- exact production status from the log, never an inferred status from process launch;
- screenshot paths discovered from the worker log and whether each file exists and has non-zero size.

A script exit code of zero is not success proof. For `SUCCESS` or `ALREADY_LOGGED_IN`, independently inspect the exact screenshot and run OCR/sanity verification where available. If OCR was not completed, label the result `UNVERIFIED_BY_OCR`, not confirmed success.

## Failure partition
Keep these states distinct:
- `SUCCESS`: production hard gate plus fresh screenshot and independent visual/OCR verification;
- `ALREADY_LOGGED_IN`: script status only unless independently verified;
- `FAIL_*` / `ERROR`: preserve the production status and exact log line;
- `BLOCKED`: operator-level terminal classification only when the evidence shows OTP timeout, Gmail re-login, captcha/manual challenge, or another manual intervention requirement. Preserve the original script status as a sub-status.

Do not retry OTP timeout, Gmail re-login, captcha/manual, or other manual-needed outcomes in a blind loop. Preserve the failure screenshot and mark the worker BLOCKED separately.

## Duplicate-profile pitfall
The canonical `--email` path may return multiple profiles for one email if the GPM DB contains duplicates. Detect this from the worker log (`Tìm thấy N ứng viên`) and report all involved profile IDs. If the task requires one exact profile, a production CLI that accepts only email cannot guarantee that binding; do not silently claim the requested target profile ran exclusively.

## Evidence report template
Use one row per requested email:
`email | profile name/id | raw proxy | exit code | production status | screenshot exists/OCR | stdout/stderr evidence`

If a coordinator wrapper crashes after launching children, report the wrapper exception and preserve child logs/screenshots. Do not fabricate exit codes. The fact that children later ended is not equivalent to a collected return code.
