# Case UI-92: Mode 2 Multi-Anchor Retry Loop & Claude CLI Fallback When Stalled

> **Áp dụng:** Repo `D:/Taadaa/tiktok-follow` (Module 2 Follow Followers) và quy trình điều phối Coordinator chống bại liệt.
> **Ngày cập nhật:** 04/10/2026.

---

## 1. Triệu Chứng Hiện Trường (Root Cause Analysis)

### Hiện tượng:
Báo cáo cronjob buổi sáng hiển thị:
```text
• Follow chéo (27 lượt follow) [Module 2 (Anchor): 2 | Module 1 (Bù): 25]:
  + Success (3 máy):
    - 5 - 9 lượt (2 máy): M17 (7 lượt), M18 (8 lượt)
    - 10+ lượt (1 máy): M33 (10 lượt)
    - M17, M18, M33: mode2_degraded_reasons: ["MANUAL_REVIEW: follower row không có nút follow semantic"]
```

### Phân tích nguyên nhân kỹ thuật:
1. **Lỗi `missing_button_rows` ở Anchor 1:**
   Trên các máy sống (M17, M18, M33), khi mở danh sách follower của Anchor 1, một số row nội bộ bị thiếu nút follow semantic (hoặc không map được nút do layout drift/ambiguous button).
   Script kích hoạt:
   ```python
   if missing_button_rows:
       res.status = "MANUAL_REVIEW"
       res.reason = "MANUAL_REVIEW: follower row không có nút follow semantic"
       failed = True
       break
   ```
2. **Bug Premature Multi-Anchor Abort (Ngắt sớm toàn bộ session):**
   Trong mã nguồn cũ, cờ `failed = True` kích hoạt điều kiện ngắt ở cuối vòng lặp ngoài:
   ```python
   if failed or state.follow_failed:
       break
   ```
   Hệ quả: Runner bỏ cuộc ngay sau khi Anchor 1 gặp lỗi, **không bao giờ thử Anchor 2 và Anchor 3**, dù pool luôn cung cấp đủ 3 candidate (`uids = uids[:3]`).
3. **Cơ chế Fail-Soft Degradation:**
   `follow_engine.py` nhận thấy Module 2 bị `MANUAL_REVIEW` nhưng nick không bị TikTok chặn follow (`follow_failed=False`), nên đã tự động reset status về `OK` và bàn giao 100% quota cho Module 1 (Search Follow) chạy bù 25 lượt (7 + 8 + 10).

---

## 2. Quy Chuẩn Kỹ Thuật Đã Vá (Canonical Implementation)

Trong `follow_runner/flows/mode2_follow_followers.py`:

1. **Duyệt đủ ít nhất 3 Anchor trước khi kết luận thất bại:**
   - Khi Anchor 1 gặp lỗi UI/layout (như missing buttons hoặc lỗi mở tab):
     * Runner ghi nhận `anchor_fail_reason`.
     * Thu dọn UI an toàn về Feed (`_back_to_feed(engine)`).
     * **Tiếp tục thử Anchor 2 và Anchor 3.**
   - Chỉ khi **toàn bộ các anchor đều thất bại/cạn kiệt** mà chưa follow được tài khoản nào (`used == 0`), runner mới gán `MANUAL_REVIEW: follower row không có nút follow semantic` để kích hoạt cơ chế `mode2_degraded` chuyển sang Module 1.
   - Nếu bất kỳ Anchor nào kéo được follow (`used > 0`): Phiên được xác nhận thành công (`status: "OK"`, `failed: False`).
   - Nếu nick bị TikTok nhả/chặn follow (`state.follow_failed` hoặc `res.follow_failed`): Ngắt phiên ngay lập tức (fail-closed) để bảo vệ tài khoản.

2. **Ưu tiên follow các hàng có nút hợp lệ (`internal_pending`):**
   - Khi phát hiện `missing_button_rows`, nếu màn hình vẫn còn các tài khoản nội bộ có nút follow hợp lệ (`internal_pending`), runner ghi nhận cảnh báo và **tiếp tục follow các hàng hợp lệ đó** thay vì bỏ cuộc giữa chừng.

---

## 3. Quy Trình Điều Phối Chống Tự Trói Tay Chân (Claude CLI Fallback)

> **User Invariant (04/10/2026):**
> CẤM TUYỆT ĐỐI Coordinator vin vào việc hết ngân sách dispatch worker (`delegate_task` 10/10) hoặc working tree bẩn để tự tuyên bố `L3 BLOCKED` và đứng im chịu trận ("thấy đèn đỏ ngồi khóc").

Khi Worker subagent kẹt budget hoặc task sửa code/test vượt trần O(1):
1. **Kích hoạt ngay Claude Code CLI qua Background Process:**
   ```python
   terminal(
       command='claude -p "Nhiệm vụ cụ thể..." --dangerously-skip-permissions --max-turns 15',
       workdir="D:/Taadaa/tiktok-follow",
       background=True,
       notify_on_complete=True,
       timeout=300
   )
   ```
2. **Nghiệm thu bằng chứng thực tế:**
   - Chạy toàn bộ pytest suite: `python -m pytest follow_runner/tests/test_mode2_follow_followers.py -q` (đảm bảo 206/206 tests PASS 100%).
   - Stage thay đổi: `git add <files>`.
   - Chạy thẩm định độc lập Closeout Gate:
     ```bash
     python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/tiktok-follow --base HEAD~1 --json-output
     ```
   - Chỉ đóng phiên khi Sol Reviewer (:20129) chấm **APPROVED (Score >= 85/100)**.
