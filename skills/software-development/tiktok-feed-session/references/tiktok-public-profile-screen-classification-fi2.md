# TikTok Public Profile Screen Classification & Action Row (:id/fi2)

## Context & Motivation

In `tiktok-luot nuoi acc/python_runner/core/classifier.py`, `_is_public_profile_screen` distinguishes between:
1. True public user profiles visited during feed/follow/profile flows.
2. Feed suggestion cards, startup ads, or feed overlays that display follow buttons and profile-like stats.

A naive heuristic checking for any arbitrary clickable action controls (`action_controls` with `clickable="true"`) in the action row is prone to false positives or brittle behavior across different TikTok versions and themes.

## The Canonical Profile Action Row Heuristic

In TikTok's public profile UI:
- When visiting a profile, the action row below stats (Followers / Following / Likes) displays either:
  1. Two or more distinct text action buttons: e.g. `Follow` + `Nhắn tin` (`Message`), or `Đang follow` / `Đã follow` + `Nhắn tin`.
  2. A direct `Nhắn tin` / `Message` button paired with the profile suggestion chevron button.

### Canonical Suggestion Chevron (`:id/fi2`)
The dropdown chevron next to the Message button (which expands/collapses account suggestions / gợi ý tài khoản) has the canonical resource ID:
- Resource ID ending with `:id/fi2`
- Located vertically within `[stat_bottom, stat_bottom + 180]`

### Rule Implementation in `_is_public_profile_screen`
```python
# Profile text actions with exact label matching
actions = {
    label(element)
    for element in elements
    if element.center is not None
    and element.bounds is not None
    and stat_bottom <= element.center[1] <= stat_bottom + 180
    and stat_left - 100 <= element.center[0] <= stat_right + 100
    and (not username_package or element.attrib.get("package") in {"", username_package})
    and label(element) in {"follow", "nhắn tin", "message", "đang follow", "đã follow"}
}

# Canonical TikTok profile suggestion chevron control (:id/fi2) next to message button
has_profile_chevron = any(
    (e.resource_id or "").endswith(":id/fi2")
    and e.center is not None
    and stat_bottom <= e.center[1] <= stat_bottom + 180
    for e in elements
)

# Profile requires either 2 distinct text actions (Follow + Message) or
# a direct Message action paired with the canonical profile action chevron (:id/fi2)
if len(actions) >= 2 or (("nhắn tin" in actions or "message" in actions) and has_profile_chevron):
    return True
```

## Running Unit Tests in `tiktok-luot nuoi acc`
Always run pytest with `PYTHONPATH=` cleared to prevent Python interpreter / venv contamination from the Hermes agent environment:
```bash
PYTHONPATH= python -m pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_classifier.py" -q
```
