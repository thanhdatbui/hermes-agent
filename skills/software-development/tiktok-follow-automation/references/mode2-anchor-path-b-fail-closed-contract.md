# Patch Contract: Mode 2 Anchor & Path B Fail-Closed Verification & Suffixes

## 1. Action Button Suffix Drift
- File: `follow_runner/flows/verify_follow.py`
- Bổ sung resource-id suffix `:id/fm9` và `id/fm9` vào `_ACTION_BUTTON_SUFFIXES` để nhận diện nút action trên các layout/build TikTok mới.

## 2. Mode 2 Anchor Follow Fail-Closed & Budget Gate
- File: `follow_runner/flows/mode2_follow_followers.py` (`_follow_anchor_profile_if_needed`)
- Kiểm tra budget: nếu `engine.state.budget_remaining() < 1`, lập tức append reason `hết budget trước khi follow anchor` và trả về `None` (không thực hiện follow).
- Sau khi pull-to-refresh reload verification, nếu `refreshed_classification != "followed"` (bao gồm cả `not_followed` lẫn `unknown`), lập tức set `engine._last_anchor_follow_outcome = "failed"`, gọi `engine.state.set_follow_failed()` và trả về `None` để dập tắt session ngay lập tức.

## 3. Mode 2 Path B Fail-Closed Verification
- File: `follow_runner/flows/mode2_follow_followers.py` (`_path_b_verify`)
- Khi profile đã mở thành công (`dump_ok and back_ok and restored`), bất kỳ phân loại nào khác `"followed"` (như `"not_followed"`, `"uncertain"`, `"unknown"`) đều được xử lý fail-closed:
  - Gọi `state.set_follow_failed()`
  - Trả về `"failed"` thay vì rơi vào nhánh `"manual"` lỏng lẻo.
