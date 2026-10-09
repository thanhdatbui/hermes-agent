# Feed Session Watchdog Contract Divergence & Test Drift Pitfall (08/09/2026)

## 1. Bối cảnh
Khi áp dụng Patch Contract cho `test_feed_session_watchdog.py` và `sync-from-kibe.ps1` trong repo `D:\Taadaa\Hermes`:
- Patch 1: Chuẩn hoá format nhả follow (`M1`, `M2`, `X máy`).
- Patch 2: Đồng bộ `jobs.json` sang `$HermesHome\cron\jobs.json` nếu chưa tồn tại.
- Test runner: `test_feed_session_watchdog.py` được kỳ vọng pass 100%.

## 2. Hiện tượng & Phân tích nguyên nhân
Khi chạy:
```bash
D:/Taadaa/python-envs/automation/Scripts/python.exe D:/Taadaa/Hermes/deploy/hermes-home/scripts/test_feed_session_watchdog.py
```
Gặp lỗi:
```text
FAIL: test_can_report_session (__main__.TestFeedSessionWatchdogLockGuard.test_can_report_session)
AssertionError: True is not false (line 66: self.assertFalse(can_report_session(...)))
```

### Nguyên nhân gốc rễ (Semantic Divergence do commit trước đó):
Tại commit `8a9ef6a5d` (`feat(farm-guard): finalize Action-Based Zero-Bypass v2.4`), hàm `can_report_session` trong `feed_session_watchdog.py` được bổ sung shortcut:
```python
# Nếu tất cả máy dự kiến đã hoàn tất thật: chốt ngay lập tức
if completed_expected_count >= expected_count and not has_unattempted_locked:
    return True
```
Shortcut này đặt ngay trên đầu hàm, đứng TRƯỚC kiểm tra `if runner_busy: return False`.
Do đó, khi test case truyền `completed_expected_count=80` và `expected_count=80`, hàm lập tức trả về `True` mặc cho `runner_busy=True`.
Trong khi đó, test suite `test_feed_session_watchdog.py` dòng 65 vẫn giữ assertion cũ từ commit `86c6d9fae`:
```python
# 1. runner_busy is True -> always False
self.assertFalse(can_report_session(
    is_today=True,
    completed_expected_count=80,
    expected_count=80,
    now_hm="08:00",
    window_end_hm="07:30",
    runner_busy=True,
    has_unattempted_locked=False,
))
```

## 3. Kỷ luật & Bài học thực chiến
1. **Không giả mạo kết quả (Zero Hallucination):** Khi gặp test fail do contract drift đã tồn tại sẵn từ codebase/commit trước, báo cáo trung thực điểm fail và nguyên nhân gốc rễ (commit hash + logic khác biệt), KHÔNG fabricate "4 tests passed (OK)".
2. **Kỷ luật Scope Lock & Budget Gate:** Khi được giao patch 1 file test/script cụ thể, nếu phát hiện implementation và test contract không khớp:
   - Dừng ngay, không tự tiện sửa code implementation ngoài phạm vi được chỉ định.
   - Tránh rơi vào vòng lặp điều tra/sửa đổi lan man (analysis paralysis) làm cạn kiệt tool budget.
   - Báo cáo rõ để Coordinator hoặc user quyết định: sửa logic `can_report_session` (ưu tiên `runner_busy` trước) hay sửa test assertion (phù hợp với shortcut hoàn tất đủ máy).
