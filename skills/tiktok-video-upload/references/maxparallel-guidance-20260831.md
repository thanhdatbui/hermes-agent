# MaxParallel Guidance Update (2026-08-31)

**Source:** Farm automation session — running TikTok upload batch with `-Tik 2 -MaxParallel 20`

## Finding
- Script `run_tiktok_upload_batch.ps1` has `ValidateRange(1, 30)` for MaxParallel
- MaxParallel 20 is **within the script's validated range** and the config step accepts it
- Output displays "Số runner song song tối đa: 20" confirming acceptance
- **However**, the original load-pattern evidence (2026-08-14, rule 126) still applies: MaxParallel 30 → ~20/30 passing due to ADB/uiautomator overload
- A fresh batch at MaxParallel 30 clips at ~20/30 passing; the 10-worker ceiling remains the proven safe default for production runs **without** prior testing on your exact machine mix

## New Finding from This Session
- Running a **small test subset** with `-Tik 2 -MaxParallel 20` successfully passed the config phase and displayed the correct parallelism count
- This confirms 20 is technically permissible by the script's validation function
- However, this does NOT guarantee stability at scale — only that the script **accepts** the value

## Recommendation (Updated 2026-08-31)
1. **If you need >10 parallelism:** test a small subset first (e.g. `-Tik 2 -MaxParallel 20`), monitor the first 5-10 machines for `ui_dump_error` or `DEVICE_STARTUP_FAILED`, then scale up if clean
2. **Never launch a fresh big batch at MaxParallel 30** — use 10 as the documented safe ceiling
3. **Treat 11-20 as "test-and-scale" territory**, not default — always test small before scaling
4. **For production batches of 80+ machines:** stick with MaxParallel 10 until you have evidence your specific machine mix handles higher parallelism

## Test Command (proposed)
```cmd
cmd /c "echo RUN | powershell -NoProfile -ExecutionPolicy Bypass -File D:/Taadaa/Tiktok-video/run_tiktok_upload_batch.ps1 -Tik 2 -MaxParallel 20"
```

## Monitoring Checklist During Test
- Watch for `DEVICE_STARTUP_FAILED ui_dump_error: non_xml_ui_dump` in the first 5-10 machines
- Watch for `SKIPPED_LOCKED` — check if locks are stale vs cross-project contention
- Monitor `post-completion` — did machines that succeeded at MaxParallel 20 also succeed in a subsequent MaxParallel 10 run?