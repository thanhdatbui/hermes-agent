# Report routing and host-specific workbook shape

## Incident pattern
A split watchdog report can appear to work while silently misrouting sections. The Feed destination must contain Feed-only content; Follow and Upload each need their own destination payload. Never append a section header to the Feed payload merely to preserve a summary. Preserve the full section in its dedicated payload instead.

## Focused routing proof
Use a fixture/block containing all three sections and assert:
- Feed payload excludes both the Follow and Upload sections, including their headers.
- Follow payload contains the Follow section and is sent to the Follow chat.
- Upload payload contains the Upload section and is sent to the Upload chat.
- Telegram response is checked for `ok`, destination chat id, and message id. A successful Feed stdout is not proof of split delivery.
- The active runtime script and the edited/deploy script are byte-identical or explicitly synchronized before declaring the fix live.

Known destination map used by the TikTok watchdog:
- Feed / nuôi acc: `-5377611430`
- Follow chéo: `-5127276494`
- Upload video: `-5435853713`

## Admin safe-workbook shape
Admin has machines 201–280: 80 machines × 8 slots = 640 data rows, plus one header row. A generated workbook showing 688 data rows is `640 + 48`; the extra 48 are six Kibe-only extra-machine entries × eight slots. Host-specific `EXTRA_MACHINES` must be disabled when generating Admin output. Verify `TAADAA_HOST_ID=admin`/host config and inspect per-machine distribution, not just total row count.

## Dual-Farm SSH and Remote ADB Invariant
- Kibe coordinates Admin remotely via Remote ADB Socket (`tcp:192.168.110.119:5037`) and SSH (`admin-farm`).
- When runner reports Admin skip (0 valid accounts), do not jump to the conclusion that SSH or ADB is broken. Check OneDrive sync conflicts (`taikhoan_run_safe-Admin-PC-XX.xlsx`) first, as OneDrive conflict renames the safe workbook and triggers a fail-closed skip in the runner.

## Communication rule
When the user explicitly asks for repair, report root cause, evidence, and action directly. Do not claim an unverified timeout or ask for permission after the repair was requested. If delivery evidence is missing, say it is missing and verify the destination before asserting success.
