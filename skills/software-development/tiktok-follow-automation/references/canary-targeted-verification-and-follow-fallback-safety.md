# Canary Targeted Verification Protocol & Follow Fallback Safety

## 1. Nguyên tắc cốt lõi: Test đúng luồng đã sửa (No False Canary)
- **Sai lầm thường gặp**: Sửa logic fallback Mode 2 -> Mode 1 nhưng lại chạy canary với `--canary-hook nav_search`. `nav_search` chỉ kiểm tra điều hướng UI của Mode 1, hoàn toàn bỏ qua engine fallback, dẫn đến kết quả canary giả (false sense of verification).
- **Quy tắc bắt buộc**: Khi sửa logic điều phối engine (`follow_engine.py` / `mode2` / fallback):
  - Phải chạy canary với đúng `--mode 2` và cấu hình session budget nhỏ (ví dụ: `budget=2`) để kích hoạt chu trình follow thực tế hoặc mock runner.
  - Verification checklist bắt buộc kiểm tra 4 điều kiện:
    1. `mode2_fallback_to_mode1 = True` khi Mode 2 cạn anchor hoặc chỉ follow được một phần ($0 < k < \text{budget}$).
    2. `mode1_followed_count > 0` (Module 1 thực sự chạy bù phần thiếu).
    3. `followed_count > 0` và có account được ghi nhận.
    4. `follow_failed = False` (không bị nhả follow / cooldown).

## 2. Invariant: FOLLOW_FAILED chặn tuyệt đối mọi Fallback
- Nếu trong quá trình Mode 2 (hoặc Mode 1) gặp hiện tượng nhả follow sau vuốt (`anchor bị nhả sau vuốt` hoặc nút nhảy lại trạng thái cũ):
  - Hệ thống lập tức raise / set `FOLLOW_FAILED = True`.
  - **CẤM TUYỆT ĐỐI** fallback sang Mode 1 khi `follow_failed == True`. Việc chuyển tiếp sang Mode 1 khi tài khoản đang bị TikTok phạt/chặn action sẽ làm cháy tài khoản và kéo dài fail streak.
  - State file (`runs/state/follow_state_<machine>_row_<index>.json`) lập tức bật `follow_failed: true` và áp cooldown 3 ngày (`cooldown_until_date`).

## 3. Lựa chọn tài khoản & máy cho Live Canary
- Khi cần test live trên farm:
  1. **Kiểm tra trạng thái follow**: Chỉ chọn row có `follow_failed: false`, `fail_streak: 0` và không có `cooldown_until_date`.
  2. **Kiểm tra lịch farm (Preflight Check)**: Kiểm tra manifest nuôi (`cron-state/manifests/<date>`) và device lock (`.codex/device-locks/machine_<N>.lock.json`). CẤM force-preempt máy đang trong phiên nuôi active hoặc khoảng đệm 60 phút trước ca nuôi.
  3. Nếu không có máy nào vừa healthy vừa rảnh hoàn toàn, dừng lại và chạy test offline / mocked, không được spam làm hỏng thêm tài khoản đang nuôi.
