# Case UI-93: Anchor Safe-Skip Exhaustion and Mode 1 Handoff

## Contract

In hybrid Mode 2 → Mode 1:

- **Anchor 0 video** and **Anchor 0 Following** are distinct observations, but both are safe-skip outcomes. They are not `FOLLOW_FAILED` and must not stop the account session.
- After each safe-skip, continue to the next selected anchor. Exhaust the selected set (maximum 3 anchors) before handing remaining quota to Module 1.
- A real `FOLLOW_FAILED` / `follow_failed=true` is the only immediate-stop path; never degrade that case into Module 1.

## Failure pattern & Architecture Trap

- **Bẫy sửa sai tầng (Engine vs Flow Trap):**
  CẤM sửa `mode2_follow_followers.py` để ép `anchor_fail_reason` trả về `MANUAL_REVIEW` khi safe-skip! Bộ unit test hiện hữu (`test_run_mode2_skips_zero_following_anchor_and_continues` và `test_open_following_tab_detects_zero_following_on_relation_screen_and_skips_retry`) ĐÒI HỎI `status == "OK"` khi safe-skip thành công. Ép `MANUAL_REVIEW` sẽ làm gãy 2 test case này.
- **Vị trí sửa đúng (follow_engine.py):**
  Khi máy cấu hình `mode: "2"` (theo file YAML máy như machine24/74) và Mode 2 hoàn thành với `len(mode2_followed) == 0` mà KHÔNG bị nhả (`follow_failed == False`), chính `follow_engine.py` phải tự động kích hoạt fallback sang Mode 1 (`if mode == "2" and len(res.mode2_followed) == 0 and not res.follow_failed: mode = "both"` kèm structured telemetry `[METRIC] event=mode2_exhausted_fallback_mode1 mode_transition=2_to_both` và `res.details["mode2_fallback_to_mode1"] = True`).
- **Bổ sung Unit Test Hồi Quy (Test Evidence Gate):**
  Bắt buộc viết test case độc lập:
  1. `test_follow_engine_mode2_only_falls_back_to_mode1_when_anchors_exhausted` trong `test_follow_engine.py`: mock `mode2` trả về 0 follow, chứng minh `mode1` được gọi và `res.details["mode2_fallback_to_mode1"] is True`.
  2. Boundary test case `test_follow_engine_mode2_does_not_fallback_when_already_followed`: chứng minh khi Mode 2 đã follow >= 1 nick thành công thì `mode1` KHÔNG được gọi và `mode2_fallback_to_mode1` là None. Thiếu test case này Sol Reviewer sẽ trừ điểm xuống dưới 85/100.
- **Bẫy CRLF làm phình Diff trên Windows (Sol Gate Rejection Trap):**
  Khi edit file trên Windows, nếu tool hoặc editor vô tình đổi line endings sang CRLF (`\r\n`), Git sẽ coi toàn bộ file bị thay đổi (ví dụ: `880 878 lines` thay vì `2 0 lines`), khiến Sol Reviewer đánh trượt vì vi phạm ngân sách diff O(1). Bắt buộc normalize LF trước khi chạy `closeout_gate.py`.
- **Bẫy Pre-commit Selector Guard & Git Push HTTPS:**
  Pre-commit hook gọi `guard_selector_change.py --cached` yêu cầu phân giải repo root tại `Path.cwd()` để không bị `unknown option 'cached'`. Khi push qua HTTPS trên Windows, dùng token từ `gh auth token` và xóa `GIT_ALLOW_PROTOCOL` để tránh lỗi `transport 'https' not allowed`.

## Diagnosis checklist

1. Read the machine artifact and verify `status`, `followed`, `follow_failed`, `mode2_degraded`, `mode1_followed_count`, and any per-anchor details.
2. Inspect Mode 2 branches for `zero_following`, `no_video`, and `not_found`: each must record an anchor outcome before recovery/`continue`.
3. Verify the post-loop condition: safe-skip exhaustion with `used == 0` must return an explicit degradable/non-clean result; real `FOLLOW_FAILED` must remain immediate-stop.
4. Verify orchestration: Mode 2 result status, `mode` (`2` vs `both`), dual-gate budget, and the actual deployed command/config. Do not infer execution from a zero counter.
5. Require per-anchor telemetry: `anchors_attempted`, outcome/reason per anchor, exhaustion/degrade decision, and Mode 1 invocation/budget. If missing, call it an evidence gap rather than claiming all three anchors were tried.

## Pitfalls & Communication Disciplines

- **CẤM bịa biệt ngữ kỹ thuật (No Pseudo-Technical Jargon):**
  Tuyệt đối không tự chế các khái niệm/thuật ngữ gây hoang mang (như "safe-skip regression") khi chưa có bằng chứng thực nghiệm. Nếu thiếu log/telemetry chứng minh từng anchor, phải báo thẳng là "thiếu log hành trình anchor", không được dùng thuật ngữ để suy đoán mò.
- **Quy tắc phân biệt dứt khoát Safe-Skip vs Follow-Failed:**
  - `Safe-Skip` (0 video, 0 following, not found): Bỏ qua anchor hiện tại, tiếp tục thử anchor 2, anchor 3 cho đủ 3 lượt; nếu cạn cả 3 thì degrade bàn giao sang Module 1. Tuyệt đối không tính là lỗi tài khoản.
  - `Follow-Failed` (TikTok nhả/chặn follow, nút đỏ): Dừng ngay lập tức (fail-closed), bảo vệ tài khoản, cấm thử tiếp và cấm chuyển Module 1.
- **Kỷ luật hành động:**
  Tập trung xác định đúng root cause và đưa diff tối thiểu (<=30 dòng) kèm focused test offline. Không giải thích lan man, bao biện hay trì hoãn khi user yêu cầu xử lý dứt điểm.

## Verification

Use an offline mocked test proving that all selected anchors safe-skip, no follow is recorded, and the result is eligible for Mode 1 handoff; separately test that `FOLLOW_FAILED` stops immediately. Keep the patch focused and do not use a real device/ADB for this logic.
