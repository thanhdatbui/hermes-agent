# Watchdog Candidate Disk Deduplication & Multi-Topic Context Isolation (2026-10-22)

## 1. The Watchdog Stale-Candidate Loop ("Ủa đổi r mắc gì cứ đè ra chạy?")

### 1.1 The Failure Pattern
- An account is successfully renamed by the canonical runner (e.g. M44 `@oquangduong7604` -> `Dương Nấm`, M69 `@tranthibich3499` -> `Thị Xù`, M64 `@toansuong04` -> `Xuân Toàn`), creating a verified report JSON and screenshot in `D:/Taadaa/reports/`.
- However, 15 minutes later, the cron watchdog (`tiktok-rolling-rename-watchdog`) re-dispatches the exact same accounts.
- Upon opening TikTok, TikTok server detects a recent name change and enforces its 7-day cooldown: *"Bạn chỉ có thể đổi biệt danh sau 7 ngày"*.
- The runner aborts with `TikTok gioi han 7 ngay`, exits with `exit_2`, and the watchdog triggers a failure alert on Telegram:
  `⚠️ [ROLLING RENAME FAILED] May 44: @oquangduong7604 reason=exit_2`
- The operator complains: *"Ủa đổi rồi mắc gì cứ đè ra chạy?"*.

### 1.2 Root Cause Architecture
1. **Static Workbook Lag:** The candidate generator (`load_candidates()`) scans `tiktok_stats_farm.xlsx`. This Excel file is an offline snapshot that does not auto-update after individual ad-hoc or canary rename runs; the display name cell still contains the old username or stereotyped name.
2. **Uncoupled State Cache:** The watchdog's state file (`rename_natural_state.json`) only records runs dispatched directly by the watchdog process itself. Canary runs, worker runs, or manual CLI executions do not update this cache.
3. **Missing Pre-Flight Disk Gate:** The candidate selector checked `cand["machine"] in locked` and `cand["username"] in state`, but failed to inspect existing verified report files on disk (`m{M}_{user}_rename_confirmed.json`).

### 1.3 The Durable Solution (Pre-Flight Disk Gate)
In `tiktok_rename_rolling_watchdog.py`:
```python
if may and u and may in serial_map and is_stereotyped(u, d):
    rep_file = REPORT_DIR / f"m{may}_{u}_rename_confirmed.json"
    if rep_file.exists():
        try:
            if (datetime.now() - datetime.fromtimestamp(rep_file.stat().st_mtime)).days < COOLDOWN_DAYS:
                jdata = json.loads(rep_file.read_text(encoding="utf-8"))
                if jdata.get("result") in ("RENAMED", "ALREADY") or "gioi han 7 ngay" in str(jdata.get("reason", "")):
                    continue
        except Exception:
            pass
    candidates.append({"machine": may, "serial": serial_map[may], "username": u, "current_name": d})
```
- Even if the static Excel sheet has not been synced, the candidate loader detects the fresh on-disk report (< 7 days old) with status `RENAMED`, `ALREADY`, or cooldown, and prunes it from the candidate pool before scheduling.
- In our live verification, candidates immediately dropped from 196 to 57, and all recently renamed accounts vanished from the scheduling queue.

---

## 2. Topic Context Boundary & Multi-Channel Discipline ("Mày bị ngáo hả đang ở topic up ava mà")

### 2.1 The Operational Hazard
- Farm operators organize communication channels and subagent threads by operational topics:
  - **Group/Topic A:** Video rendering / Upload (`Tiktok-video`)
  - **Group/Topic B:** Nurture & Feed (`Nuôi`, `tiktok-luot nuoi acc`)
  - **Group/Topic C:** Avatar & Profile Standardization / Rename (`Up avatar / Chuẩn hoá kênh`)
  - **Group/Topic D:** Infrastructure & Logistics / Orders (`Taadaa Farm Alert`, order tracking, carriers)
- **Anti-Pattern:** When working in a thread dedicated to Avatar / Rename operations, the coordinator dredged up unrelated memories/skills from an older order tracking session (J&T carrier scraping) and attempted to write carrier pickup strategies into the library.
- This breaks operator trust and pollutes topic context.

### 2.2 Invariant Rules
1. **Topic Scope Lock:** Lock the current session scope to the active platform topic/channel. When inside the Avatar/Rename topic, all analysis, runner fixes, and skill updates MUST remain bounded to profile mutation, ADB device control, and rename watchdog operations.
2. **No Hallucinated Multi-Tasking:** Never append unrelated domain documentation (e.g. e-commerce orders, carrier logistics, tender MCPs) during a device farm debugging session.
3. **Immediate Purge on Steering:** If the user points out a context mismatch ("Mày bị ngáo hả đang ở topic X mà"), immediately acknowledge the steering, delete the out-of-scope artifact, and refocus 100% on the active domain task.
