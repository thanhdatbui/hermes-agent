# Nick Trust Score & Why Some Never Drop (Drop-Rate Root Cause Analysis)

Empirical data from 405 state files + `tiktok_tracker.db`, farm Kibe 1–80, analysed 06/10/2026.
Script logging started 26/08/2026.

---

## 1. Overall Drop Rate Across History

| Metric | Value |
|---|---|
| Total state files analysed | 405 |
| Nick **never dropped** (sạch tuyệt đối) | **23 (5.7%)** |
| Nick **ever dropped** ≥ 1 time | **382 (94.3%)** |
| Date range covered by state files | 26/08/2026 → 06/10/2026 |

Note: State files are **append-only** (follows are never pruned). Total-followed counts are reliable lifetime counts, not rolling windows.

---

## 2. Drop Rate By Row (Slot)

| Row | N accounts | Ever dropped | Drop rate |
|---|---|---|---|
| Row 1 | 80 | 67 | **84%** |
| Row 2 | 78 | 74 | **95%** |
| Row 3 | 73 | 69 | **95%** |
| Row 4 | 77 | 77 | **100%** |
| Row 5 | 37 | 36 | **97%** |
| Row 6 | 39 | 39 | **100%** |
| Row 7 | 13 | 13 | **100%** |
| Row 8 | 7 | 7 | **100%** |

**Key conclusions:**
- Only Row 1 has meaningful "sạch" population (13 nick, 16% of row).
- Rows 4–8: 100% drop rate. TikTok silently rejects follow actions server-side regardless of age/video gate.
- 287 nick across Rows 3–8 have `total_followed ≤ 5` (most = 0): they hit the wall immediately.

---

## 3. Why Do 13 Row-1 Nicks Stay Clean?

Comparing Row-1 clean (15 nick) vs Row-1 ever-dropped (65 nick) from DB snapshots:

| Metric | Row 1 CLEAN | Row 1 DROPPED |
|---|---|---|
| Avg videos | 22.2 | 23.4 |
| Avg followers | 76.0 | 70.6 |
| Avg following (DB) | **198.5** | **138.5** |
| Avg total followed (script) | **141.2** | **102.4** |

**Video count and follower count are NOT discriminating factors.** Both groups are statistically identical.

The real discriminating factors:

### A. Rhythm / Cadence (không bị dồn cục vào "bão siết")
- Clean nick (e.g. M16, M4, M9, M39, M18, M17): followed steadily every eligible ca from late August onward. No forced gaps. TikTok's rolling rate-limit window never filled up in a single burst.
- Dropped nick: a large cluster of `last_failed_date` entries falls in the **01/10 – 05/10/2026 window** — a period of widespread TikTok Action Throttling. Nick that happened to hit this window during a heavy-follow session triggered the rate-limit even though their trust score was otherwise high.

### B. TikTok Rolling Window Rate-Limit (per account, not per device)
- Even old Row-1 nicks have an invisible follow quota over a 7–14 day rolling window.
- Once an account hits that ceiling in one burst session, TikTok silent-drops the next follow tap.
- Script detects this via Path B re-entry / verify_follow.py re-check and sets `follow_failed = True`.
- **Punishment is per-account trust score, NOT per device.** A Row-5 nick being dropped on M9 does NOT contaminate M9's Row-1 nick. Confirmed empirically 03/10/2026.

### C. Organic interaction depth (feed history, watch time, session fingerprint)
- Row 1–2 accounts survived not just because of video count but because they were genuinely used (TikTok sees session fingerprint breadth: scroll events, video plays, likes, etc.) before the follow script ran.
- Rows 3–8 accounts that were reg'd, given videos, then immediately pushed into follow mode lack this depth — TikTok's server-side gate catches them even if client UI flickers "Đang follow".

---

## 4. Post-Cooldown Recovery: Nick Già Sau Dưỡng Sinh Có "Ngọng" Không?

**Không.** Timeline evidence from M51 R1, M38 R1, M36 R1, M29 R1:

| Machine | Total Followed | Pattern After Cooldown |
|---|---|---|
| M51 R1 | 291 | After each 3-day rest: 12–32 follow/day, resumes full budget |
| M36 R1 | 222 | After rest: 13–24 follow/day |
| M38 R1 | 179 | After Sept rest: 8–9 follow/ca in Oct |
| M29 R1 | 188 | After rest: 5–9 follow/ca |

**Code mechanic (follow_state.py `session_budget()`):**
- When `is_post_cooldown_warmup = True` (= `fail_streak > 0` AND `follow_failed == False`): cấp **3–5 follow** cho phiên đầu thăm dò.
- If that session succeeds → `fail_streak` resets to 0 → next session gets **full budget 10–20 follow**.
- No permanent reduction. No lasting penalty on budget ceiling.

**The only real difference** between "nick sạch tuyệt đối" and "nick từng bị nhả":
- Sạch: Runs every eligible ca without hitting rolling rate-limit. No lost days.
- Từng bị nhả: Cycle of **Cày 3–4 ngày → Nghỉ 3 ngày (Cooldown) → Cày tiếp**. Sản lượng tháng thực tế thấp hơn ~30–40% do thời gian nghỉ cưỡng bức.

---

## 5. Fail-Streak Distribution (382 ever-dropped nicks)

| Streak | Count |
|---|---|
| streak=1 | 177 (46%) |
| streak=2 | 145 (38%) |
| streak=3 | 38 (10%) |
| streak=4 | 4 (1%) |
| streak=5 | 16 (4%) |

No nick accumulated streak > 5. Cooldown backoff (3 / 5 / 7 days) is working as designed.

---

## 6. Cờ `last_cooldown_decision` làm Key Phân Loại

When auditing state files, these fields conclusively identify ever-dropped nicks:
- `fail_streak > 0` — primary flag
- `last_failed_at` — ISO timestamp of most recent drop event
- `last_failed_date` or `follow_failed_date` — local date of drop
- `last_cooldown_decision` — dict with `{"streak": N, "cooldown_until_date": ..., "cooldown_until_at": ...}`

Nick with `fail_streak=0` AND none of the above fields = truly clean (never dropped in script history).
