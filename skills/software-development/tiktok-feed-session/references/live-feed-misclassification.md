# 2026-08-15 — LIVE feed bị classify manual-needed:popup → dừng sớm

## Triệu chứng (máy 5, live pilot 9C.2)

- Feed session chạy 16/30 swipe rồi dừng; `summary.txt` = `final_status: fail`,
  message "multi-machine-feed-session completed with failed machine(s)", reason "feed not confirmed".
- Log máy con `machines/machine_5/<ts>/log.jsonl` (file 462+ dòng, KHÔNG phải root log — root log chỉ 1 dòng tổng):
  - `swipe_16_after/attempt_1 classify_screen → manual-needed`
  - `swipe_16_after → swipe → manual-needed`
  - `baseline_after_shared_popup_dismiss classify_screen → success`
  - `swipe_16_after_after_popup_dismiss → observe → failed`
  → flow tưởng popup, dismiss, xong không confirm feed → dừng session.

## Root cause

`automation_core/tiktok/benign_popup.py::detect_allowed_generic_popup` chain gọi
`detect_live_room_invite_overlay(root)` (dòng 1587). Detector này match TikTok LIVE THẬT:
- live terms ("live") có trong UI,
- ≥2 context terms,
- element `:id/long_press_layout` fullscreen bounds (0,0,1080,1920) với text "live".

→ LIVE thật (sponsored multi-guest live: "Đang LIVE", "LIVE", "Yêu cầu", tên chủ phòng) bị match
→ `BenignPopupMatch("live_room_invite", ...)` → classifier trả
`GENERIC_POPUP_SCREEN = "manual-needed:popup"` (reason "known live_room_invite popup detected").

## Chẩn đoán nhanh

Chạy classifier lên ui.xml attempt fail:
```python
from core.classifier import classify_tiktok_screen
import xml.etree.ElementTree as ET
r = classify_tiktok_screen(ET.fromstring(open(path,'r',encoding='utf-8',errors='replace').read()))
# r.screen == 'manual-needed:popup', reasons: ['known live_room_invite popup detected']
```

## Fix (consumer, KHÔNG đụng automation_core)

`python_runner/core/classifier.py`, ngay trước `known_popup = detect_allowed_generic_popup(root)`:

```python
live_values = " ".join(
    " ".join(part for part in (element.text, element.content_desc) if part)
    for element in elements
).casefold()
live_feed_tabs = ("trang chủ", "bạn bè", "đã follow", "đề xuất")
live_markers = ("đang live", "nhấn để xem live")
if any(marker in live_values for marker in live_markers) and any(
    tab in live_values for tab in live_feed_tabs
):
    return ScreenClassification(
        screen="for-you",
        confidence=0.85,
        reasons=["real TikTok LIVE feed visible"],
        manual_needed=False,
    )
```

Lý do an toàn: LIVE thật TRONG FEED giữ tab row (Trang chủ/Bạn bè/Đã follow/Đề xuất);
room-invite overlay thật xuất hiện TRÊN video thường KHÔNG có tab row → guard không nuốt popup thật.

Verify:
- `classify_tiktok_screen(ui.xml LIVE thật)` → `for-you`, manual=False.
- `classify_tiktok_screen(ui.xml feed thường)` → `following`/`for-you`, KHÔNG đổi.
- `_is_live_feed_screen` → False trên feed thường.

## Cấp độ lỗi (xác định TRƯỚC khi sửa)

- tiktok-luot nuoi acc (feed session) dùng `core/classifier.py` → dính bug → fix consumer.
- tiktok-follow dùng `core/popup.py` RIÊNG + `automation_core.dismiss_popup` (không qua
  `detect_allowed_generic_popup`) → KHÔNG dính → không cần đụng core.
- Chỉ sửa automation_core khi nhiều consumer cùng dính qua chain chung.

## EOL note khi patch classifier.py

File này baseline MIXED EOL (681 CRLF + 73 LF) + `core.autocrlf=true`:
- Patch tool LF-hoá vùng CRLF → diff toàn file + `git diff --check` báo trailing whitespace `\r`.
- Chèn dòng mới = script line-based giữ EOL từng dòng; normalize toàn file LF TRƯỚC audit.
- Commit helper: staged blob (LF) ≠ working (CRLF) → sha256 mismatch → normalize + reset + add lại.
Chi tiết đầy đủ: `references/2026-08-15-live-pilot-and-eol-lessons.md` (skill tiktok-farm-hermes-cron-migration).
