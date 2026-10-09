# Feed Swipe Fast Loop & Tab Switching Pitfalls

## 1. Tab Decision Countdown in Fast Swipe
Inside `_feed_session_flow` in `python_runner/flows/feed_swipe_smoke.py`:
When processing the `fast_swipe` loop branch where `videos_until_deep_inspect -= 1` is decremented before `continue`:
- Ensure `videos_until_tab_decision -= 1` is also decremented right before `continue`.
- Missing this decrement causes the feed session to stall or skip tab-switching evaluation during continuous fast-swipes, as the loop repeats without advancing the tab switch countdown.

Anchor:
```python
videos_until_deep_inspect -= 1
videos_until_tab_decision -= 1

continue
```
