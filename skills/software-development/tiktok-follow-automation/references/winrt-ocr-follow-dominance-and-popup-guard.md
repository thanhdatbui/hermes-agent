# WinRT OCR Follow Dominance & Popup Dismissal Guard

## Context & Core Problem (16/10/2026)
When transitioning from slow Android XML dump (`uiautomator dump` taking 3s - 15s) to high-speed Windows native WinRT OCR (`ocr_boxes.ps1` taking 0.3s), OCR provides flat text coordinates without hierarchy. This flat vision introduces 3 critical false-positive failure modes:

1. **Parallel Button Deception ("Follow" + "Nhắn tin"):**
   - Unfollowed accounts with public DM enabled, or accounts that follow the farm account back, display BOTH buttons: `[Follow / Follow lại]` and `[Nhắn tin]`.
   - Naive OCR classifiers checking for keyword `"nhắn tin"` will falsely mark the account as `followed`, masking unfollow/drop events and reporting false success.

2. **Stat Counter Substring Traps:**
   - Profile header counters render labels: `"127 Đã follow"`, `"10K Follower"`, `"0 Đang follow"`.
   - Naive substring checks (`"follow" in text`) falsely match `"follower"` or `"đã follow"` as follow action buttons.

3. **Feed Top Bar & Bio Interference:**
   - Top navigation tabs on Feed (`y1 < 200`) include `"Bạn bè"` and `"LIVE"`. If scanned without a vertical boundary (`y_min`), they trigger false `followed` classifications.
   - Long profile bio text containing `"Follow kênh mình nhé..."` triggers false action matches if not bounded by token length (`len(n_txt.split()) <= 3`).

---

## Architectural Rules & Hybrid Boundary (OCR vs XML)

| Task Type | Recommended Engine | Reason |
| :--- | :--- | :--- |
| **Action Buttons with Obfuscated IDs** | **WinRT OCR (First-Line / Fallback)** | Immune to TikTok ID scrambling (`id/fds` -> `id/fmp` -> `id/fo4`). |
| **Fast Benign Popup Dismissal** | **WinRT OCR (0.3s First-Line)** | Dumps benign popups ("Để sau", "Không phải bây giờ") without freezing UI loop. |
| **Account Identity (@username / UID)** | **100% XML (STRICTLY FORBIDDEN FOR OCR)** | OCR confuses `0`/`O`, `1`/`l`, risking cross-account corruption on Excel records. |
| **State Attributes (`selected`, `checked`)** | **100% XML** | OCR has no awareness of UI selection state or focused input state. |

---

## The Follow Dominance Invariant
In `automation_core.ocr` and `follow_runner.core.ocr`:

```python
def classify_profile_action_ocr(
    boxes: List[Tuple[str, Tuple[int, int, int, int]]],
    y_min: int = 200,
    y_max: int = 1200,
    allow_message_alone: bool = False
) -> str:
    # 1. Scan boxes in valid action band (y_min=200 excludes Feed top nav)
    # 2. Priority 1 (Follow Dominance): If ANY not_followed button exists -> ALWAYS "not_followed"
    if has_not_followed:
        return "not_followed"
    # 3. Priority 2: Explicit relationship confirmed ("Bạn bè", "Đang theo dõi", "Following")
    if has_explicit_relationship:
        return "followed"
    # 4. Priority 3: Message button alone -> fail-closed "unknown" unless caller explicitly allows
    if has_message_button:
        return "followed" if allow_message_alone else "unknown"
    return "unknown"
```

### Candidate Selection by Proximity
When multiple candidates match in `find_follow_button_center_ocr`:
- Rank candidates by vertical distance `abs(cy - anchor_y)` to the expected action band center (`anchor_y = 700`).
- Prefer exact single-token `"follow"` over composite `"follow lai"` on equal distance.
- Reject any box with `len(n_txt.split()) > 3` or matching stat counter regex `r"follower|followers|dang\s+follow|da\s+follow"`.

---

## Fast Popup Dismissal Safety Guard
When scanning for benign dismissal buttons (`"để sau"`, `"không phải bây giờ"`, `"hủy"`, `"not now"`):
- **Word Boundary Matching:** Always match keywords with `\b` word boundary to prevent accidental matches inside words (e.g., `prepayment` matching `payment`).
- **Safety Circuit Breaker:** If ANY box on the screen contains sensitive keywords (`"mật khẩu"`, `"dang nhap"`, `"captcha"`, `"otp"`, `"payment"`), abort dismissal immediately and return `None` to pass control to full XML challenge handlers.
