# Contract Rule: Mode 2 Anchor Video Gate & Mock Adapter Isolation

## 1. Context & Rationale
Trong luồng follow Anchor ở Mode 2 (`follow_runner/flows/mode2_follow_followers.py`), điều kiện tiên quyết theo giao thức Anti-Release là Anchor phải có video để follow qua video player (`_ensure_anchor_followed`).
Nếu profile Anchor không tìm thấy video covers:
- Runner gán `_last_anchor_follow_outcome = "no_video"`.
- Ghi nhận `res.details["mode2_skip_reason"] = f"anchor @{uid} không có video"`.
- Thực hiện safe-skip thoát về feed.

## 2. Mock Adapter Fallback vs. Live Devices
- Trong codebase có đoạn fallback tap nút Follow trực tiếp trên trang cá nhân Anchor khi `not video_covers`.
- **Tuyệt đối không mở fallback này cho Live Device** (không được thay `if is_mock_adapter:` thành `if True:`).
- Lý do: Khối fallback này chỉ dành riêng cho các mock unit tests cũ (vốn không dựng video cover nodes trong mock XML dump). Trên thiết bị thật (live android adapter), việc tap trực tiếp follow profile khi không có video vi phạm quy trình Anti-Release Video Gate và bypass sai contract.
- Mọi thay đổi code trên `mode2_follow_followers.py` cần giữ nguyên `if is_mock_adapter:` và chỉ giữ hunk contract được duyệt (`res.details["mode2_skip_reason"]`).
