# Workbook Header Aliases, Admin Downloader Proxy, and Profile Milestone Popup Triage (2026-10-17)

## 1. Parenthesized Workbook Header Aliases
- **Symptom:** Workflow canary or runner fails during initial workbook load with:
  `Workflow target error: Missing required fields: Folder Video`
  even though the Excel sheet has data and columns.
- **Root Cause:** Real workbook headers in `Tik1.xlsx` .. `Tik8.xlsx` often carry parenthesized descriptions:
  - `Folder Video (Render Dich)`
  - `Video Goc (Nguon Cao)`
  When `normalize_header()` preserves parentheses, `account_source.py`'s `CANONICAL_HEADERS` dictionary fails to match if it only looks for bare `"folder video"` and `"video folder"`.
- **Fix:** Update `CANONICAL_HEADERS` in `account_source.py` to include:
  ```python
  "Folder Video": {
      "folder video",
      "video folder",
      "folder video (render dich)",
      "folder video render dich",
      "sttvideo",
  },
  "video gốc": {
      "video goc",
      "video source",
      "source video",
      "video goc (nguon cao)",
      "video goc nguon cao",
  },
  ```
- **Verification:** Run `pytest tests/test_account_source_concurrency.py -p no:cacheprovider` to verify 4/4 passing tests. Commit with `[L2-surgery]` and sync to Admin host (`D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\account_source.py`).

## 2. Admin Downloader Proxy Loopback (502 Bad Gateway)
- **Symptom:** Admin host downloader (`download_by_niche.py` / `download_admin_p10.log`) throws repeated:
  `ProxyError: ('Unable to connect to proxy', OSError('Tunnel connection failed: 502 Bad Gateway'))`
- **Root Cause:** `proxy_pool_69.txt` on the Admin host used the public DDNS domain:
  `mirotik1.taadaa.click:10001` .. `10035`
  The Admin machine (`192.168.110.119`) sits on the internal LAN. Loopback requests out to the WAN domain and back to the MikroTik router are rejected or fail with 502.
- **Fix:** Replace `mirotik1.taadaa.click:` with the LAN gateway IP `192.168.110.2:` across all entries in `proxy_pool_69.txt`.
- **Crucial Pitfall:** Existing `download_by_niche.py` worker processes cache the proxy pool in memory. Seducing the file on disk is not enough — kill existing downloader processes so `run_admin_downloader_service.py` spawns fresh workers that reload the LAN proxy configuration.

## 3. Profile Screen Milestone Popup ("Tổng lượt thích")
- **Symptom:** Runner successfully opens TikTok and taps the Profile tab, but fails at `ACCOUNT_SWITCHER`:
  `[ACCOUNT_SWITCHER_FAILED] open_switcher failed: SWITCHER_NOT_CONFIRMED: switcher markers were not confirmed`
- **Root Cause:** TikTok presents an in-app milestone modal on the Profile tab:
  - Header: `"Tổng lượt thích"`
  - Body: `"<username> đã nhận tổng cộng N lượt thích cho tất cả video"`
  - Action button: `[OK]` (center bounds around `[506, 1389, 575, 1425]`)
  The modal dialog intercepts taps to the top switcher / profile name anchor.
- **Handling:** Must be dismissed by tapping `[OK]` or Back key before attempting to resolve switcher anchors. Do not confuse this with lost login session or account deletion.

## 4. Guarded Soft-Reboot Recovery & Proxy Watcher Dependency
- **Symptom:** When a runner hits a recoverable UI deadlock and executes `SOFT REBOOT RECOVERY`, the device reboots cleanly, but the post-reboot check fails with:
  `Guarded reboot recovery failed: proxy watcher did not publish post-reboot readiness after reboot`
- **Root Cause:** Android phones on the farm (Samsung S7) do not auto-start `vn.vichanger.app` after boot. The workflow relies on the central proxy watcher daemon (`gan_proxy_fleet.py watch`) to detect reconnects, wake the device, launch ViChanger, and establish `tun0`.
- **Gotcha:** If `GanProxyWatcherTray` scheduled task is `Disabled` on the host, no proxy watcher is alive. Post-reboot, the device remains without VPN, timing out the workflow's guarded recovery.
