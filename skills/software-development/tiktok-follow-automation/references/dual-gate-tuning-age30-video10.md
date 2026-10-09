# Dual Gate Tuning: Nâng Ngưỡng Nick Non Lên age≥30 & video≥10

## Vấn Đề Thực Tế (Empirical Evidence, 06/10/2026)

Phân tích từ 394 state file có ghi `last_budget_decision`:

| Group | N decisions | % bị nhả |
|---|---|---|
| `age <= 30` hoặc `video < 10` (warmup / mồi) | **185** | **98.4% (182/185)** |
| `age > 30` VÀ `video >= 10` (full gate) | ~209 | ~40% (do bão siết TikTok Oct) |

**Kết luận:** Nick non đáp ứng gate cũ (`age >= 21 && video >= 6`) nhưng chưa đạt `age >= 30 && video >= 10` bị nhả **gần như chắc chắn 100%**. Cấp budget mồi 3–5 follow cho chúng là đốt vía và tăng fail_streak vô nghĩa.

---

## Video Count Distribution By Row (Từ tiktok_tracker.db)

| Row | Total | video ≥ 10 | video 6–9 | video < 6 |
|---|---|---|---|---|
| Row 1 | 78 | **73 (94%)** | 5 | 0 |
| Row 2 | 80 | **69 (86%)** | 9 | 2 |
| Row 3 | 81 | **49 (60%)** | 25 | 7 |
| Row 4 | 80 | **53 (66%)** | 23 | 4 |
| Row 5 | 78 | **1 (1%)** | 38 | 39 |
| Row 6 | 80 | **0 (0%)** | 37 | 43 |
| Row 7 | 66 | **0 (0%)** | 13 | 53 |
| Row 8 | 54 | **1 (2%)** | 29 | 24 |

**Nhận xét:**
- Row 5–8: Gần như 0% nick đạt ≥ 10 video → Nâng gate lên video ≥ 10 sẽ block toàn bộ các row này, đúng như mong muốn (tập trung chúng vào đăng video / feed trước).
- Row 3–4: Vẫn còn 60–66% nick đạt ≥ 10 video → Không bị cạn nguồn, farm vẫn có lực lượng kế thừa.

---

## Đã Áp Dụng Chính Thức (Applied on 2026-10-06 — User Approved)

**File:** `D:/Taadaa/tiktok-follow/follow_runner/core/follow_state.py`
**Hàm:** `session_budget()`
**Unit test:** `tests/test_follow_state.py` (Đã cập nhật test suite và pass 100%)

- **Strict Gate:** `account_age_days >= 30` VÀ `video_count >= 10`.
- **Nick non:** Thiếu 1 trong 2 điều kiện $\rightarrow$ `budget = 0` (hard-block, chỉ đăng video + lướt feed).
- **Post-cooldown warmup:** Nick mãn hạn cooldown được giữ warmup 3–5 follow thăm dò trước khi mở full budget.

**Anchor cụ thể (dòng 262–270):**

```python
# CURRENT:
if account_age_days is not None:
    if account_age_days < 21 or video_count is None or video_count < 6:
        budget = 0
    elif self.is_post_cooldown_warmup:
        budget = _random.randint(3, 5)
    elif account_age_days <= 30 or video_count < 10:
        budget = _random.randint(3, 5)   # "mồi" warmup
    else:
        budget = _range(1)

# PROPOSED:
if account_age_days is not None:
    if account_age_days < 30 or video_count is None or video_count < 10:
        budget = 0                       # hard block nick non
    elif self.is_post_cooldown_warmup:
        budget = _random.randint(3, 5)   # giữ warmup cho nick hồi phục cooldown
    else:
        budget = _range(1)
```

**Tác động:**
- ~200 nick Row 5–8 bị blocked (budget = 0) → không bị TikTok gắn cờ spam nữa.
- Nick Row 3–4 đủ tiêu chuẩn vẫn chạy bình thường.
- Nick già (R1/R2) không bị ảnh hưởng gì.

---

## Cơ Chế Silent Drop Của TikTok (Optimistic UI Trap)

Hiểu để không bị nhầm:
- TikTok client hiển thị nút đổi sang **"Đang follow"** ngay khi tap (Optimistic UI).
- Server TikTok **âm thầm huỷ bỏ (silent drop)** hành động follow tại server-side gate nếu account chưa đủ trust.
- Script phát hiện bằng cách re-entry profile sau tap (`verify_follow.py: _confirm_not_released()`) hoặc kiểm tra danh sách follower của anchor (`mode2_follow_followers.py: _path_b_verify()`).
- Nếu re-check thấy nút vẫn là "Follow" → `state.set_follow_failed()` → Cooldown.

**Nơi gọi `set_follow_failed()` trong codebase:**
- `verify_follow.py` line 277, 289, 335 — verify sau tap single follow
- `mode2_follow_followers.py` line 559, 675, 1729, 2165 — Path B verify
- `mode1_search_follow.py` line 88 — Mode 1 exception handler

---

## Post-Cooldown Warmup Là Đúng — Không Nên Bỏ

Cơ chế `is_post_cooldown_warmup` (budget 3–5 cho nick mãn hạn cooldown) **NÊN GIỮ NGUYÊN**:
- Nick già (R1) sau cooldown 3 ngày: phiên thăm dò 3–5 follow đầu tiên để check TikTok còn chặn không.
- Nếu ăn được → streak reset về 0 → phiên sau full budget 10–20.
- Nếu bị nhả ngay phiên thăm dò → fail_streak tăng → cooldown 5 ngày (streak=2) hoặc 7 ngày (streak=3+).
- Không nên merge "warmup cho nick non" và "warmup cho nick hồi phục cooldown" vào cùng 1 điều kiện.
