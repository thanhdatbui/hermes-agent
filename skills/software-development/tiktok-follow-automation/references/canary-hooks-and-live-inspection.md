# Targeted Canary Hooks & Live Inspection (`run_follow.py`)

## Mục đích
Hỗ trợ kiểm tra, debug và nghiệm thu từng hook chức năng độc lập trên live device (<60s) mà không chạy toàn bộ flow follow (không làm bẩn account hoặc tiêu hao follow budget).

## Danh sách hook (`--canary-hook`)

1. **`open_following_tab`**
   - Mở app, hồi phục UI về Home (`engine.recover_ui()`).
   - Tìm và mở profile của target (`--canary-target <UID>`), sau đó bấm vào following tab.

2. **`nav_search`**
   - Test search box và điều hướng tìm kiếm username trên TikTok UI.

3. **`verify_profile`**
   - Test nhận diện UID, nick name, follow button trên profile của target.

4. **`single_follow`**
   - Test thực hiện follow 1 tài khoản đơn lẻ và kiểm tra trạng thái nút follow sau khi bấm.

5. **`inspect_following_rows`**
   - Điều hướng vào following tab của target UID (`--canary-target <UID>`).
   - Chụp hierarchy XML (`adapter.dump_hierarchy()`) và parse danh sách UI nodes (`parse_nodes(xml)`).
   - Thu thập danh sách rows và follow buttons qua `_collect_follower_rows(nodes)`.
   - Kết xuất chi tiết trong `details`:
     - `rows_count`: tổng số hàng tài khoản nhận diện được.
     - `rows_summary`: danh sách `{handle, has_button, button_id, button_text}`.
   - Fail-closed (`CANARY_FAILED`) nếu:
     - 0 rows được tìm thấy.
     - Tìm thấy rows nhưng 0 row nào có follow button hợp lệ.
   - Thích hợp để test thực tế nhận diện button và selector drift sau khi TikTok cập nhật layout mà không trigger click follow thật.

## Cách chạy lệnh mẫu

```bash
cd /d/Taadaa/tiktok-follow
PYTHONPATH=. D:/Taadaa/python-envs/automation/Scripts/python.exe -m follow_runner.run_follow \
  --machine <MACHINE_ID> \
  --config config/farm_follow.yaml \
  --canary-hook inspect_following_rows \
  --canary-target <TARGET_UID> \
  --canary-screencap reports/inspect_canary.png \
  --force-preempt
```
