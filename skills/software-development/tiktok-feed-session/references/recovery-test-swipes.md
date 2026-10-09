# RecoveryTestSwipes (Targeted Recovery Feed Swipes)

## Quy định phạm vi (Range Rule)
- Tham số `--recovery-test-swipes` (Python) và `-RecoveryTestSwipes` (PowerShell) phục vụ chạy test phục hồi nhanh cho máy bị kẹt hoặc cần verify feed session ngắn.
- **Giới hạn hợp lệ**: `1 <= RecoveryTestSwipes <= 4` (đã nâng từ 3 lên 4 vào 2026-09-06).
- Hai file đồng bộ ràng buộc này:
  1. `scripts/run-feed-session.ps1`:
     ```powershell
     # A targeted recovery must complete after only 1-4 verified feed swipes.
     [ValidateRange(1, 4)]
     [int]$RecoveryTestSwipes,
     ```
  2. `python_runner/flows/multi_machine_feed_session.py` (hàm `_session_targets`):
     ```python
     def _session_targets(config: dict[str, Any]) -> tuple[int, int, int]:
         recovery_test_swipes = config.get("_recovery_test_swipes")
         if recovery_test_swipes is None:
             return FEED_SESSION_MIN_TOTAL_VIDEOS, FEED_SESSION_MAX_TOTAL_VIDEOS, FEED_SESSION_MAX_SWIPES
         target = int(recovery_test_swipes)
         if not 1 <= target <= 4:
             raise RuntimeError("--recovery-test-swipes requires 1 <= value <= 4")
         return target, target, target
     ```

## Kỹ thuật kiểm tra xác minh an toàn (Safe Verification Patterns)
1. **Kiểm tra cú pháp Python độc lập:**
   - Dùng `python -m py_compile <path>` để kiểm tra syntax mà không load runtime dependencies (như PIL/Pillow C-extensions có thể lỗi môi trường).
2. **Kiểm tra AST PowerShell (Parse Check):**
   - Không chạy script nhưng vẫn validate toàn bộ syntax PowerShell:
     ```powershell
     powershell -Command "$tokens = $null; $errs = $null; [System.Management.Automation.Language.Parser]::ParseFile('D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1', [ref]$tokens, [ref]$errs); if ($errs.Count -gt 0) { $errs; exit 1 } else { Write-Host 'PS1 syntax OK' }"
     ```
   - Lưu ý: trong PowerShell `[ref]` bắt buộc biến phải được khởi tạo trước (`$tokens = $null; $errs = $null;`).
3. **Chạy thử preview không tác động thiết bị:**
   - `run-feed-session.ps1` mặc định chạy preview nếu KHÔNG truyền `-Run`. Có thể test validate tham số an toàn:
     ```powershell
     powershell -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Row 1 -Machines "1" -RecoveryTestSwipes 4
     ```
