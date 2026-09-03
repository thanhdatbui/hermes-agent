# TikTok historical discovery: distinguish cached URLs from runtime crawling

## Why this reference exists

When a current TikTok manifest contains profile URLs but no `video_urls`, do not conclude that the older run used a manually prepared URL cache. The older downloader itself may have crawled the profile and persisted the resulting video URLs in its state database.

## Proven historical pattern

The older `download_by_niche.py` path handled a source in this order:

1. If `Source.video_urls` was already populated, use those URLs.
2. Otherwise call `yt_dlp.YoutubeDL(...).extract_info(source.url, download=False)` on the profile URL.
3. Read `entries` from the flat result and turn each entry into a video candidate.
4. Persist the candidate URL (`https://www.tiktok.com/@handle/video/<id>`) in `state.db`.
5. Download the candidate through the normal yt-dlp media path.

Therefore the old database can contain many concrete `/video/<id>` rows even when the original source manifest only contained profile URLs. The database rows are evidence of successful *runtime discovery*, not proof of manual pre-seeding.

## Differential investigation recipe

For a historical-vs-current question, inspect all three boundaries:

```bash
# Compare discovery implementations
 git show <old-revision>:scripts/download_by_niche.py
 git show HEAD:scripts/download_by_niche.py

# Find the discovery seam
 grep -n -E 'def discover_source|video_urls|extract_info|/video/' scripts/download_by_niche.py

# Inspect persisted evidence
 python - <<'PY'
import sqlite3
c = sqlite3.connect(r'D:/CodexRuntime/tiktok-video-downloader/state-real-1-tiktok-final.db')
print(c.execute("select count(*) from videos where platform='tiktok' and source_url like '%/video/%'").fetchone()[0])
print(c.execute("select count(*) from videos where platform='tiktok' and status='downloaded'").fetchone()[0])
PY
```

Use the actual old revision and state database available in the workspace; do not invent counts. Check reports for `insufficient_pool` vs concrete `/video/` candidates to distinguish discovery failure from media-download failure.

## Current route classification

Keep these claims separate:

- **Direct URL download OK:** a known `/video/<id>` URL produced a valid MP4 and passed `ffprobe`.
- **Profile discovery OK:** the current profile route returned candidate URLs.
- **Batch ready:** the current source pool produced enough candidates for a real folder and the production runner created TikTok-specific downloaded records/files.

A direct canary proves only the first claim. A current manifest with empty `video_urls` does not by itself prove manual preparation in the past.

## Root-cause pattern seen in the July-to-August transition

The historical route was profile extraction through yt-dlp. The current route was changed after TikTok began returning `Unexpected response from webpage request`, secondary-user-ID errors, or a slider challenge. The fallback stack became Camoufox item-list capture, then public indexed search, then direct TikWM media resolution. That explains why the media resolver can still work while batch discovery does not.

## Reporting discipline

Answer the user's exact question first, in concise Vietnamese facts. State the evidence and label uncertainty. Do not recommend lowering the folder threshold or mixing channels before proving that discovery is the bottleneck. Do not describe the old URL set as "manually prepared" unless the source-generation evidence proves it.
