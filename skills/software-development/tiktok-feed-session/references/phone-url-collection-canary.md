# Phone-based TikTok URL collection: canary evidence

## Why this reference exists
A web profile extractor and a phone feed/profile collector solve different problems. A direct TikTok URL download can pass while profile enumeration is blocked. Do not merge those results.

## Existing code boundary observed
The current nurture feed flow has a real Android/TikTok session:

- `python_runner/flows/feed_swipe_smoke.py::feed_session_smoke`
- `_perform_feed_swipe()` sends bounded feed swipes and records `swipe_count`.
- `FeedStep`/session summaries record screen, safety, focus, XML and screenshot artifacts.
- `python_runner/flows/benign_popup_registry.py::detect_and_dismiss_share_sheet()` detects Share Sheet markers such as `Sao chép Liên kết` and `Copy link`, then closes the sheet. It does not copy the URL or read clipboard.

A symbol search for `clipboard`, `share_url`, `video_url`, `video_id`, `item_id`, and `aweme` must be repeated against the current tree before implementation; do not rely on this snapshot if the repo has changed.

## Candidate implementation contract
Keep discovery separate from downloading:

1. Lock exactly one authorized machine/account and preserve the live scene on failure.
2. Confirm TikTok package/focus and a real feed/profile screen from fresh ATX/XML plus screenshot evidence.
3. For each candidate video, use semantic Share action and then exact `Sao chép Liên kết` / `Copy link` action. Do not use a blind coordinate or treat Share Sheet detection as a successful copy.
4. Read clipboard through an approved adapter; never print or persist cookies, tokens, passwords, or unrelated clipboard contents.
5. Validate URL host/path and extract a stable video ID. Reject profile, search, share-sheet, login, or malformed links.
6. Deduplicate by normalized video ID/URL and record source profile, collection mode, timestamp, attempt status, and artifact paths without sensitive UI text.
7. Re-capture after copy and before the next swipe/back action. If the action result is ambiguous, mark the candidate unproven and continue only under a bounded policy.
8. Pass the resulting public URL manifest to the existing direct resolver. Validate each MP4 with file size, container/codec and `ffprobe`; downloader success alone is insufficient.

## Profile purity rule
- A feed collector can produce many URLs but usually mixes channels. It is not valid input for a folder requiring 30 videos from one source/channel.
- A profile collector must bind every URL to the profile identity captured in the same app flow. If profile identity or selected Profile screen is not proven, the URL is unproven.
- Never combine feed URLs, public-search URLs, and profile URLs to conceal a shortfall in one source.

## Canary acceptance
Use one machine/account only and an isolated artifact/output directory. Before any batch:

- collect >=5 URLs from one public profile;
- all URLs validate as `/video/<id>` and are unique;
- download >=3/5 using the existing direct route;
- every downloaded file is a real MP4 and `ffprobe` returns duration;
- manifest/report includes candidate count, valid count, unique count, downloaded count, failed count, file sizes and evidence paths;
- no production `state.db`, workbook, `D:\video goc`, render directory, credentials or session secrets are modified;
- stop on login/OTP/2FA/CAPTCHA/security/manual challenge and report the exact blocker.

Only after this gate passes should the collector be expanded to 30 URLs/profile and then evaluated for batch integration.

## Common false conclusions
- Feed swipe success ≠ URL collection success.
- Seeing `Sao chép Liên kết` in XML ≠ clipboard contains the correct video URL.
- A non-zero subprocess exit code or wrapper `success` ≠ candidate/download evidence.
- One direct URL MP4 ≠ profile enumeration support.
- A later Home screenshot ≠ evidence of the earlier feed/profile state.

## Suggested report
Report in concise Vietnamese facts:

- `route`: feed collector or profile collector
- `candidate`: N
- `valid_unique`: N
- `downloaded`: N/N
- `ffprobe`: pass/fail
- `source_purity`: pass/fail/unproven
- `production_mutation`: none or exact path
- `blocker`: exact observed blocker
- `evidence`: real artifact paths
