# Chuẩn hóa cấu hình tương tác nuôi Feed (Feed Session) & Xem video Profile (Follow Session) — Cập nhật 2026-10-03

## 1. Dwell time xem video Profile đối phương (Repo `tiktok-follow`)
- **Trước đây:** Dwell time xem video trước khi follow hoặc sau khi follow chỉ từ `6.0 – 10.0s`. Trừ đi 2s chụp ảnh evidence và buffer mạng qua proxy/4G, thời gian phát thực tế chỉ còn 3–5s, tạo cảm giác lướt quá nhanh và không tự nhiên.
- **Chuẩn hóa mới:** 
  - Thêm tham số `dwell_range=(12.0, 20.0)` mặc định cho hàm `_maybe_watch_profile_video`.
  - Tính toán: `dwell = round(random.uniform(*dwell_range), 1)`.
  - Thời gian sleep xem video: `time.sleep(max(1.0, dwell - 2.0))`.
  - Đảm bảo video phát trọn vẹn 10–18 giây trên máy thật.
  - Test kiểm chứng: `follow_runner/tests/test_mode1_watch_video.py` bao gồm cả `test_maybe_watch_profile_video_dwell_range_12_to_20`.

## 2. Chuẩn hóa tỷ lệ tương tác & Phân bổ Tab Feed Nuôi Acc (Repo `tiktok-luot nuoi acc`)
- **Vấn đề phát hiện qua đối soát Log:**
  - Tỷ lệ like thực tế chỉ loanh quanh 11% – 14% dù đã có bạn bè và following.
  - Nguyên nhân:
    1. Cơ chế `Fast Swipe` lướt nhanh 2–4 video xen kẽ không thả tim (like = 0%), làm loãng tỷ lệ tổng.
    2. Phân bổ tab cũ quá lệch về For You (`70% For You / 15% Following / 15% Friends`), khiến hơn 80% số máy trong phiên 18 video không hề ghé thăm tab Following hay Bạn bè lần nào.
- **Chuẩn hóa mới:**
  - **Phân bổ tab mặc định (`DEFAULT_FEED_DISTRIBUTION`):**
    - `for-you`: **`0.50`** (50%)
    - `following`: **`0.25`** (25%)
    - `friends`: **`0.25`** (25%)
  - **Giữ nguyên chu kỳ lướt:** Giữ nguyên 100% cơ chế Fast Swipe (2–4 video lướt nhanh xen kẽ 1 video xem kỹ) để máy farm không bị quá tải CPU/RAM.
  - **Nâng tỷ lệ thả tim kịch khung ở nhịp xem kỹ (Deep Inspect):**
    - `FEED_TYPE_FRIENDS`: Nâng từ 65% lên **`95%`** (Base: 85%, phân phối mềm: 75% – 95%).
    - `FEED_TYPE_FOLLOWING`: Nâng từ 35% lên **`85%`** (Base: 65%, phân phối mềm: 55% – 75%).
    - `FEED_TYPE_FOR_YOU`: Giữ nguyên 48% ở nhịp xem kỹ (Base: 15%, phân phối mềm: 12% – 16%).

## 3. Pitfall khi chạy Closeout Gate trên repo `tiktok-luot nuoi acc`
- **Pitfall 1 (Pytest Timeout do unmocked sleep):**
  - File `test_feed_swipe_smoke.py` có 101 tests, một số test case kích hoạt `_relaunch_and_poll_tiktok_focus` gọi `device_prepare.force_stop_and_relaunch_tiktok` chứa `time.sleep(after_launch_delay_seconds)`.
  - Nếu test runner không mock `flows.device_prepare.time.sleep`, tổng thời gian chạy test suite sẽ vượt quá 120 giây và bị `Closeout Gate` đánh fail do `TIMEOUT`.
  - **Giải pháp chuẩn:** Trong `FeedSwipeSmokeTests` và `FastSwipeDeepInspectTests`, bổ sung `setUp` / `tearDown` mock `flows.device_prepare.time.sleep`, giúp test suite 117 tests hoàn thành chỉ trong **2.09 giây**.
- **Pitfall 2 (Thiếu Telemetry Observability khi tăng tương tác):**
  - Sol Reviewer chấm điểm khắt khe về tiêu chí `telemetry_observability`. Khi tăng mạnh tỷ lệ like theo tab, reviewer yêu cầu phải có telemetry ghi nhận rõ ràng event thuộc tab nào để giám sát an toàn farm.
  - **Giải pháp chuẩn:** Bổ sung `"feed_type": after_attempt.get("feed_type") or "unknown"` vào metadata `extra` của tất cả các nhánh log `action="like_video"` (cả nhánh thành công lẫn các nhánh skip do `already_liked`, `button_not_found`, `ui_dump_unavailable`). Điểm Reviewer lập tức nâng từ 82 lên **86/100 (APPROVED)**.
- **Pitfall 3 (Pre-push Hook & Gate Audit Binding Synchronization):**
  - Hook `.git/hooks/pre-push` kiểm tra dòng cuối cùng trong `D:/Taadaa/logs/gate_audit.jsonl`.
  - Nếu chạy `closeout_gate.py` ở trạng thái staged đạt APPROVED, sau đó `git commit`, cần lưu ý rằng mọi lần gọi gate tiếp theo (ví dụ với `--base HEAD~1`) sẽ ghi đè dòng mới nhất vào log audit. Nếu lần gọi sau chưa đạt >= 85, pre-push hook sẽ chặn đứng `git push`.
  - Luôn đảm bảo lần chạy thẩm định cuối cùng ghi nhận trong `gate_audit.jsonl` có `verdict: APPROVED` và `score >= 85` khớp chính xác với scope và commit cần push.
