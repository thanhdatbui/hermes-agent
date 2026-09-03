# Offline TDD cho consumer — FakeAdapter với queue XML (proven 2026-08-11, follow_runner)

Consumer mới nên test-first với adapter giả cùng interface FollowAdapter
(dump_ui/screencap/tap/swipe/type_text/keyevent/shell/launch_app/force_stop),
trả XML uiautomator từ hàng đợi. Không cần device thật, không cần automation-core
import ở test (engine inject popup/switcher/busy_check/identity_fn).

## Design FakeAdapter

- `xml_queue: list[str]` + `_dump_index` — dump_ui trả theo thứ tự, hết queue thì
  trả LẠI phần tử cuối (mô phỏng màn đứng yên). Đây là nguồn truth của test:
  push ĐÚNG số dump cho ĐÚNG chuỗi hành động.
- `shell()` BẮT BUỘC có (ghi `shell_calls`) — thiếu nó thì engine.prepare_device
  (settings put...) fail âm thầm → status MANUAL_REVIEW thay vì expected state,
  mất thời gian debug.
- Helper `xml_node(...)` + `xml_doc(*nodes)` dựng node với bounds/index — test
  fixture đọc được.
- **Chuẩn đoán queue lệch**: test chậm bất thường (100s+) = wait_for_node timeout
  vì dump không khớp — đừng tăng timeout, sửa queue. Debug bằng wrapper trace
  `dump_ui` in `[dump#N] xml[:60]` xem từng bước tiêu thụ dump nào.

## Pitfalls đã dính (2026-08-11)

1. **`random.shuffle` phá thứ tự queue test**: run_mode1 shuffle list UID → thứ tự
   thực thi khác thứ tự fixture → test flaky/fail ngẫu nhiên. Fix:
   `monkeypatch.setattr("random.shuffle", lambda x: None)` giữ thứ tự file.
2. **Test helper trộn kwargs**: `_engine(fake, tmp_path, busy_check=...)` mà helper
   pass mọi kwargs vào config_from_dict → busy_check rơi vào config.extra, engine
   vẫn dùng logic thật → status sai khó hiểu. Tách rõ: helper nhận engine-kwargs
   (busy_check/switcher_fn/identity_fn) riêng khỏi config-overrides.
3. **Assert đúng tầng**: `follow_one_uid` trả outcome; state.mark/consume_budget
   xảy ra ở `run_mode1` — test đừng assert state sau follow_one_uid.
4. **Config validation chặn fixture chưa tồn tại**: validate `follow_list_file`
   phải là file có thật → helper phải tạo file trước (uids.txt mặc định).
5. `tap_center(None)` phải raise FollowAdapterError (không AttributeError) — engine
   catch và route MANUAL_REVIEW.
6. Suite offline chạy ~1-3 phút vì sleep/wait_for_node thật — chấp nhận cho
   pre-commit; đừng giảm timeout code để test nhanh.

## Engine injectables (giúp test mà không cần core)

```python
FollowEngine(adapter, cfg, mapping, state,
             popup_handler=None, switcher_fn=None,   # test: lambda ad: True
             busy_check=None, identity_fn=None, now=None)  # test: lambda s,m: False
```
Core (account_switcher.open_profile_root/open_switcher, detect_popup, locks) gọi
trong try/except — offline test inject hàm giả, production dùng core thật.
