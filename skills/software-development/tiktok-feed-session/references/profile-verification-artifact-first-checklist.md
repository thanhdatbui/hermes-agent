# Profile verification incident evidence checklist

Use this checklist for any TikTok profile/account mismatch, wrong-tab suspicion, or later Home/Launcher screenshot.

## Required sequence
1. Identify the exact run, machine, account scope, and artifact root.
2. Read `log.jsonl` around the terminal `verify_profile` event and the immediately following cleanup/recovery events.
3. Resolve the exact final-attempt paths. A logged directory is not an XML artifact; enumerate it and require the actual `ui.xml` and `screen.png` files.
4. Open the final XML tree and matching screenshot before concluding which screen was visible.
5. Compare the final capture with the last known-good preflight/profile XML and the last in-flow feed capture.
6. Label each conclusion `confirmed`, `excluded`, or `unproven`; missing final artifacts mean `capture_artifact_missing`/`unproven`, not a guessed screen.

## Evidence rules
- `selected=true` on the Profile/Hồ sơ tab plus a profile identity anchor is strong evidence of the Profile screen.
- A successful tap/ADB acknowledgement is not evidence that navigation completed.
- A parser field such as `texts[0] == "Message"` is not identity evidence and cannot prove the Inbox tab was selected.
- A later Android Launcher/Home screenshot does not prove the earlier flow or cleanup sent Home. Correlate timestamps and search independent recovery/reaper actors for `KEYCODE_HOME`, `input keyevent 3`, force-stop, and timeout paths.
- Never report `xml_available=true` from a directory path alone. The exact XML and screenshot must exist and be linked in metadata.

## Implementation contract
Every profile verification capture, including retries and mismatch attempts, must persist the exact `ui.xml` and `screen.png` before identity parsing. If either capture fails, return a capture-invalid/incomplete result and preserve the scene; do not downgrade it to `profile account mismatch`.

## Reporting format
Keep the final report short and factual in Vietnamese: `Mục đích`, `Kết quả`, `Bằng chứng`, `Unproven/Blocker`, `Đã sửa/Chưa sửa`. Include exact paths and timestamps when available. Do not claim to have read an XML/screenshot that was not actually opened.
