# Device Lock Fail-Closed Rubric, Staged Scope Exactness & Pre-Push Binding (2026-10-21)

## 1. Device Lock Fail-Closed Rubric (Reviewer Scoring 78 -> 86)

### Bẫy Phổ Biến (Nullcontext Fallback Trap)
Trong các tool can thiệp thiết bị Android hoặc CLI nhận tham số `--machine <ID>`, đoạn code sau thường được viết nhằm "phòng vệ":
```python
try:
    from automation_core.device_lock import operator_device_lock
    lock_ctx = operator_device_lock(machine=args.machine, serial=serial, force_preempt=True, timeout=30.0)
except Exception:
    lock_ctx = contextlib.nullcontext()
with lock_ctx:
    run_operation()
```
**Hậu quả:** Reviewer Sol High chấm REJECT (78/100) ngay lập tức với lý do:
*"Điểm trừ lớn nhất nằm ở việc bỏ qua mọi Exception khi thiết lập device lock và tiếp tục thao tác trong nullcontext: cơ chế đồng bộ thiết bị trở thành tùy chọn đúng tại thời điểm cần bảo đảm an toàn nhất."*

### Chuẩn Mực Bắt Buộc (Fail-Closed Pattern)
Khi tham số `--machine` được chỉ định, việc lấy lock thiết bị là **bắt buộc và bất khả xâm phạm**. Bắt buộc tách bạch và xử lý fail-closed có telemetry:
1. `ImportError`: Log telemetry `{"event": "device_lock_unavailable", "serial": serial, "error": str(exc)[:200]}`, `return 1`.
2. Lỗi khởi tạo lock (`Exception` khi gọi `operator_device_lock`): Log telemetry `{"event": "device_lock_acquire_failed", ...}`, `return 1`.
3. Lỗi timeout / execution trong context manager: Bắt `TimeoutError` -> `device_lock_timeout`, `return 1`. Các lỗi khác -> `device_lock_execution_failed`, `return 1`.
4. Không bao giờ biến lock thất bại thành `nullcontext` để chạy mù khi đang vận hành thiết bị thật.

### Bộ Test Bắt Buộc Để Đạt Điểm >= 85
Để Reviewer phê duyệt, file test đi kèm bắt buộc phải bao phủ 4 kịch bản:
1. `test_main_fails_closed_when_device_lock_import_unavailable`: Monkeypatch `__import__` ném `ImportError`, assert hàm trả về mã lỗi 1 và không chạm vào device action.
2. `test_main_fails_closed_when_device_lock_acquisition_fails`: Mock `operator_device_lock` ném `RuntimeError`, assert trả về 1.
3. `test_main_device_lock_timeout_prevents_device_operation`: Mock context manager ném `TimeoutError`, assert trả về 1.
4. `test_main_device_lock_serializes_concurrent_operations`: Dùng `threading.Thread` và `threading.Lock` để chứng minh 2 luồng gọi đồng thời được tuần tự hóa (`max_active == 1`).

---

## 2. Staged Index Contamination Trap (`staged != targets`)
Khi chạy `closeout_gate.py --files <targets>`, hàm `targeted_candidate()` kiểm tra `git diff --cached`:
- Nếu Git index đang chứa bất kỳ file nào khác được staged (do lệnh `git add` trước đó hoặc hook bỏ dở), Gate sẽ dừng ngay lập tức tại Step 2 với lỗi:
  `Failed to extract diff: staged files ['other_file.py'] != --files targets ['target1.py', 'target2.py']; unstage extras or adjust --files`
- **Xử lý:** Kiểm tra `git diff --staged --name-only` trước khi chạy gate. Nếu có file ngoài scope, chạy `git restore --staged <files>` để đưa index về trạng thái sạch (`worktree_targeted`).

---

## 3. Pre-Push Hook & Committed Scope Audit Binding
- Pre-push hook (`.git/hooks/pre-push`) chặn mọi lệnh `git push` nếu không tìm thấy bản ghi `APPROVED >= 80` trong `D:/Taadaa/logs/gate_audit.jsonl` gắn đúng commit SHA hiện tại ở đỉnh `HEAD`.
- Nếu đã commit cục bộ:
  - CẤM chạy `git push` chay vì hook sẽ lập tức chặn lại (`❌ [BLOCKED - PRE-PUSH HOOK]`).
  - BẮT BUỘC chạy:
    `python D:/Taadaa/tools/closeout_gate.py --repo <path> --base HEAD~1 --files <files...> --push --json-output`
  - Gate sẽ tự động thẩm định commit `HEAD~1..HEAD`, ghi token thẩm định vào `gate_audit.jsonl`, và sau đó tự động unmask gọi `safe_push.py` đẩy commit lên remote thành công.
