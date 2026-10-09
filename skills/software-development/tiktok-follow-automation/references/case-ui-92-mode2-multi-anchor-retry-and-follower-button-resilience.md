# Case UI-92: Module 2 Multi-Anchor Retry & Follower Button Resilience (04/10/2026)

## 1. Triệu chứng & Nguyên nhân Lệch Quota Module 2 / Module 1

### Triệu chứng ca chạy sáng (04/10/2026):
- Dashboard & Cronjob ghi nhận: Module 2 chỉ đạt 2 lượt follow, trong khi Module 1 vọt lên 25 lượt bù (M17: 7, M18: 8, M33: 10).
- 26 máy dính nhả follow ngay sau khi follow kênh Anchor và kích hoạt chốt dừng an toàn (fail-closed).
- 3 máy sống sót (M17, M18, M33) khi vào đọc danh sách Follower của Anchor thì vướng lỗi:
  `mode2_degraded_reasons: ["MANUAL_REVIEW: follower row không có nút follow semantic"]`

### Nguyên nhân gốc rễ trong `mode2_follow_followers.py`:
1. **Bug ngắt sớm Anchor 1 (Vòng lặp ngoài bị break non):**
   - Danh sách Anchor candidate vốn lấy tối đa 3 nick (`uids = uids[:3]`).
   - Nhưng khi Anchor 1 gặp lỗi UI (như `missing_button_rows` hoặc lỗi mở tab `open_ok == False`), cờ `failed = True` kích hoạt lệnh `break` làm ngắt ngay lập tức cả vòng lặp ngoài `for uid in uids:`.
   - Kết quả: Runner bỏ cuộc ngay tại Anchor 1 mà **chưa từng thử Anchor 2 và Anchor 3**.
2. **False MANUAL_REVIEW khi thiếu nút cục bộ:**
   - Khi một row trên màn hình không có nút follow hợp lệ (hoặc layout TikTok bị xô lệch), `missing_button_rows` phát hiện và ném ngay `MANUAL_REVIEW`, ngay cả khi trên cùng màn hình đó vẫn còn các row farm khác (`internal_pending`) có nút follow hợp lệ sẵn sàng bấm.

---

## 2. Quy chuẩn Thiết kế Nghiệp vụ & Kỹ thuật Chuẩn

### A. Nguyên tắc "Thử ít nhất 3 Anchor trước khi cho phép qua Module 1":
- **Sequential Anchor Traversal:**
  Runner bắt buộc duyệt qua lần lượt cả 3 Anchor trong `uids = uids[:3]`.
- **Anchor Isolation:**
  Mỗi anchor là một đơn vị thao tác độc lập:
  - Khi Anchor 1 gặp lỗi giao diện/layout: ghi nhận `anchor_fail_reason`, điều hướng an toàn về Feed (`_back_to_feed(engine)`), và **chuyển tiếp sang Anchor 2 và Anchor 3**.
  - Không được để lỗi UI của một anchor làm ô nhiễm cờ lỗi hay dừng phiên của các anchor phía sau.
- **Điều kiện Degrade sang Module 1:**
  - Nếu có bất kỳ Anchor nào kéo được follow (`used > 0`): Phiên Module 2 được xác nhận thành công (`status: "OK"`, `failed: False`). Module 1 chỉ chạy bù phần quota còn thiếu (nếu có).
  - Chỉ khi **toàn bộ 3 Anchor đều thất bại / cạn kiệt** mà không follow được nick nào (`used == 0` và có `anchor_fail_reason`): Module 2 mới được coi là thất bại và trả về `status: "MANUAL_REVIEW"` để kích hoạt cơ chế `mode2_degraded` bàn giao quota cho Module 1 chạy bù.

### B. Ưu tiên hàng có nút hợp lệ (`internal_pending`):
```python
if missing_button_rows:
    logger.warning("run_mode2: anchor @%s có %d row internal thiếu nút follow semantic",
                   uid, len(missing_button_rows))
    if not internal_pending:
        anchor_fail_reason = "MANUAL_REVIEW: follower row không có nút follow semantic"
        anchor_failed = True
        break
    # Vẫn còn row internal có nút follow hợp lệ → tiếp tục follow các row đó!
```

### C. Chốt an toàn tài khoản (Account Penalty Fail-Closed):
- Duy nhất trường hợp tài khoản bị TikTok nhả/chặn follow (`state.follow_failed` hoặc `res.follow_failed`): Runner BẮT BUỘC ngắt phiên ngay lập tức để bảo vệ tài khoản, cấm thử tiếp Anchor sau hoặc chuyển Module 1.

---

## 3. Checklist Kiểm thử & Nghiệm thu (Verification Checklist)

1. **Unit Test Coverage:**
   - Test case `test_run_mode2_tries_next_anchor_when_first_anchor_fails`: Chứng minh khi Anchor 1 mở tab fail, runner tự động lùi về Feed và thử Anchor 2, hoàn thành follow thành công (`status == "OK"`).
   - Test case `test_run_mode2_persistent_invalid_surface_fails_closed_to_manual_review`: Chứng minh khi toàn bộ anchor đều fail, runner mới trả về `MANUAL_REVIEW`.
   - Test case `test_cluster_follower_rows_supports_id_u2f` & `test_m19_following_screen_regression_uvz_and_u2f`: Bảo đảm không nhận nhầm subtitle badge thành button node.
2. **Closeout Gate Verification:**
   - Chạy `python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/tiktok-follow --base HEAD~1 --json-output`.
   - Bắt buộc đạt `Verdict: APPROVED` (Score >= 85/100) trước khi merge/commit.
