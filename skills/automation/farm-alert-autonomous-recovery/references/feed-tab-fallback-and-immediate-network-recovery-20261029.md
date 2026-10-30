# Feed Tab Fallback & Immediate Network Error Recovery (2026-10-29)

## 1. Triệu chứng & Bẫy Kỹ Thuật (The Premature Stop Trap)
- Trong các đợt chạy nuôi nick hàng loạt (`multi_machine_feed_session`), TikTok thường xuyên gặp lỗi mạng ở các tab con (như tab Bạn bè hoặc tab Đang follow):
  `step: switch_friends_<N>_navigation_network_recheck`, `detected: manual-needed:network`, `stop_reason: network/error/retry marker detected`.
- **Cơ chế lỗi cũ:** Logic fallback chuyển tab (`_need_tab_fallback`) bị đặt dưới điều kiện `_manual_guard_triggered` (yêu cầu consecutive count $\ge 2$). Do đó, khi tab Friends/Following gặp lỗi mạng ngay lần đầu tiên, session bị hủy ngang (`manual-needed`) dù tài khoản mới chỉ lướt được một vài video For You, gây lãng phí slot và tăng tỷ lệ fail ảo trên toàn farm.

## 2. Giải Pháp Chuẩn Hóa Cơ Chế Tự Phục Hồi (Auto-Healing Fallback)
1. **Helper chuyên trách `_tab_fallback_reason(confirm, next_feed_type)`:**
   - Độc lập hoàn toàn với `_manual_guard_triggered`.
   - Nếu `next_feed_type` thuộc `{FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS}` và phát hiện một trong các marker sự cố:
     - `manual-needed:network`
     - `manual-needed:empty`
     - `manual-needed:retry`
     - `manual-needed:popup`
     - Hoặc có nội dung lệch feed (`friends_feed_content_mismatch`).
   - Hàm trả về trực tiếp `trigger_reason`.
2. **Graceful Degradation & State Synchronization:**
   - Tự động tap quay lại tab Đề xuất (`FEED_TYPE_FOR_YOU`).
   - Đặt `confirm["status"] = ExitStatus.DEGRADED.value` và `confirm["safety_status"] = "ok"`.
   - **BẮT BUỘC đồng bộ bộ 3 biến trạng thái:**
     * `confirm["detected"] = FEED_TYPE_FOR_YOU`
     * `confirm["feed_type"] = FEED_TYPE_FOR_YOU`
     * `expected_label = _expected_feed_label(FEED_TYPE_FOR_YOU)`
   - *Hệ quả nếu thiếu:* `_is_navigation_mismatch_row` sẽ so sánh `detected` cũ (following/friends) với `next_feed_type` mới (for-you) -> false mismatch -> rơi vào `retry_navigation` với `expected_label` cũ -> `feed not confirmed` gây sập hàng loạt máy (34/78 máy).
   - Giữ tài khoản tiếp tục lướt feed Đề xuất cho đến khi hoàn thành đủ hạn ngạch video được giao.

## 3. Kỷ Luật Closeout Gate & Sol Auditor
- Khi refactor điều kiện fallback tab trong monolith `feed_swipe_smoke.py`, Sol Reviewer sẽ trừ điểm nặng nếu chỉ viết test độc lập với biến cục bộ.
- Bắt buộc trích xuất logic quyết định thành production helper (`_tab_fallback_reason`), và viết unit test trực tiếp gọi helper này với các ca biên (Following, Friends, For You, valid content) để đạt điểm review $\ge 85/100$.

## 4. GuardGate Invariant Rule & Khóa Regression Tuyệt Đối (Anti-Agent-Amnesia)
- **Vấn đề chống agent sau phá:** Sau khi sửa xong, agent ở các phiên sau rất dễ vô tình gói lại điều kiện `_manual_guard_triggered and ... friends` khi tái cấu trúc code.
- **Rule khóa cứng:** Bổ sung rule bất biến vào `rules.json` của repo `tiktok-luot nuoi acc`:
  - `id`: `case_invariant_prohibit_guarded_friends_feed_fallback`
  - `pattern`: `(?i)if\s+_manual_guard_triggered\s+and\s+.*(?:friends|following)`
  - `require_all`: `["prohibit_case_invariant_prohibit_guarded_friends_feed_fallback"]`
- **Unit test xác thực:** Bắt buộc có test trong `tests/test_tiktok_runner_healing.py` (`test_guardgate_rule_prohibits_guarded_friends_feed_fallback`) đọc trực tiếp pattern từ `rules.json`, kiểm tra 2 chiều:
  - DENY các chuỗi vi phạm (`if _manual_guard_triggered and next_feed_type in ...`).
  - ALLOW các chuỗi an toàn (`_tab_fallback_reason(...)`).
- Khi GuardGate được cấu hình, mọi commit vi phạm sẽ bị chặn đứng ngay từ tầng pre-commit của Git và pre-push Closeout Gate.
