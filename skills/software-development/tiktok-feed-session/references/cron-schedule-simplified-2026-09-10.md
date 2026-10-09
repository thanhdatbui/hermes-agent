# Cron Schedule Don Gian (2026-09-10)

## Background

User yeu cau tinh gian toan bo he thong picker/cohort/manifest. Subagent truoc do da over-engineering: ve them picker.py, cohort.py, manifest.py, staging.py voi validator block_index chi accept (1,2,3) — giet chet toan bo farm khi Ca 4 (block 4) xuat hien.

## Schedule hien tai

Runner: `C:\Users\Kibe\AppData\Local\hermes\scripts\tiktok_runner.py`
Launcher: `D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1`
Workbook: `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`

```
00h -> Row 8/7 (Ca dem — slot dau ngay)
06h -> Row 2/1 (Ca sang)
12h -> Row 4/3 (Ca trua)
18h -> Row 6/5 (Ca toi)
01-05h = Dead zone
```

- Ngay chan (day%2==0): Row 8, 2, 4, 6
- Ngay le (day%2==1): Row 7, 1, 3, 5
- 0h chay slot dau ngay nen parity `day%2` binh thuong (khong cross-midnight)

## Pitfalls

1. **Artifact root PHAI dung path**: `D:\Taadaa\runtime\kibe\live\{date}\row-{row}-{HHMMSS}`
   - PS1 default la `.ai-runs/` -> watchdog khong tim thay -> khong report
   - tiktok_runner.py phai pass `-ArtifactRoot` dung

2. **KHONG dung Hermes venv** cho run_tiktok.py -> PIL crash (`cannot import name '_imaging'`)
   - Phai dung: `D:/Taadaa/python-envs/automation/Scripts/python.exe`
   - PS1 tu xu ly venv noi bo

3. **Dead code picker/cohort/manifest**: KHONG import, KHONG dung, KHONG sua
   - `python_runner/hermes_cron/` directory van ton tai nhung la dead code
   - `run_tiktok.py` va `multi_machine_feed_session.py` da go het references

4. **State dedup**: `D:/Taadaa/runtime/kibe/cron-state/runner_simple_state.json`
   - Format: `{"last_row": N, "last_window": "YYYY-MM-DDThh", "last_run_at": "ISO"}`
   - Moi window chi spawn 1 lan
