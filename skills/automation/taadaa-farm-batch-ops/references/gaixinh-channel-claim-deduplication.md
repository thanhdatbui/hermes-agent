# Gaixinh Channel Claim Deduplication System

## Context & Motivation
When running multi-folder download scripts (`smart_gaixinh_distributor.py` and `download_gaixinh_pipeline.py`) simultaneously or sequentially across multiple folders (e.g. 31, 63, 79, 95), channels must not be duplicated across folders to avoid multiple TikTok accounts sharing identical source video pools.

## Core Modules & Protocol

### 1. `scripts/gaixinh_claims.py`
Provides thread-safe / persistent channel claim management:
- Persistent file: `D:/Taadaa/Tiktok-video/data/gaixinh_channel_claims.json`
- Per-folder backup discovery: Scans `channel_info.json` within `<output_root>/<folder>/` if present.
- `normalize_channel_key(url_or_uploader)`:
  - Normalizes full URLs, user handles, and video URLs.
  - Strips trailing slash, lowercases, and extracts `@uploader` before any `/video/...` path.
- `load_claims(claims_path, output_root=None)`:
  - Loads JSON dictionary mapping channel URL -> `{"folder": str, "uploader": str, "claimed_at": str}`.
  - Seeds `DEFAULT_SEEDS` on creation.
- `is_channel_claimed(claims, channel_url, current_folder=None)`:
  - Returns `(True, folder)` if already claimed by another folder.
  - Returns `(False, None)` if unclaimed or already claimed by `current_folder`.
- `claim_channel(claims, channel_url, folder_num, uploader, claims_path, output_root=None)`:
  - Claims channel, writes atomically via `.tmp` swap to `claims_path`.
  - Also outputs `channel_info.json` directly into folder directory if `output_root` provided.
- `release_claim_for_folder(claims, folder_num, claims_path)`:
  - Used during `--clean-old` to release ownership of channels mapped to that folder.

### 2. Integration Points
- **`smart_gaixinh_distributor.py`**:
  - Checks `is_channel_claimed(claims, url)` during candidate scanning; skips channels claimed by other folders.
  - Calls `claim_channel(...)` when assigning channels in exclusive and auto modes.
  - Calls `release_claim_for_folder(...)` when `--clean-old` is specified.
- **`download_gaixinh_pipeline.py`**:
  - Filters out claimed channels from manifest before passing to `extract_candidate_videos`.
  - Claims channel upon downloading videos into `folder_name`.
  - Releases folder claim when `--clean-old` runs.
