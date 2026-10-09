# Case UI-92: Mode 2 Multi-Anchor Exhaustion Gate & Follower Button Semantic Recovery

## Ngữ cảnh & Triệu chứng lỗi (Incident Report 2026-10-04)
- **Hiện trường:** Ca 1 Row 2 báo cáo thống kê Follow chéo lệch nghiêm trọng: `[Module 2 (Anchor): 2 | Module 1 (Bù): 25]`.
- **Triệu chứng:** Hàng loạt máy (M17, M18, M33...) chỉ ăn 0 lượt ở Module 2 và phải chuyển giao toàn bộ quota sang Module 1 để search follow bù.
- **Log telemetry:** `mode2_degraded_reasons: ["MANUAL_REVIEW: follower row không có nút follow semantic"]`.

## Nguyên nhân cốt lõi (Root Cause)
1. **Premature Loop Break (Lỗi ngắt sớm vòng lặp Anchor):**
   - Trong `run_mode2` (`mode2_follow_followers.py`), danh sách anchor seed được lấy tối đa 3 nick (`uids = uids[:3]`).
   - Khi anchor đầu tiên gặp lỗi UI/layout (như `missing_button_rows` hoặc lỗi mở tab `open_ok == False` sau retry ladder):
     Runner đánh dấu `res.status = "MANUAL_REVIEW"`, `failed = True`, và gọi lệnh `break`.
   - Lệnh `break` này nằm trực tiếp trong vòng lặp `for uid in uids:`, khiến runner thoát toàn bộ Module 2 ngay sau Anchor 1 mà **hoàn toàn không thử Anchor 2 và Anchor 3**.
2. **Resource-ID Obfuscation trên Follower List:**
   - Hàm `_cluster_follower_rows` chỉ lọc các node có `resource_id` kết thúc bằng `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`.
   - Khi TikTok đổi/làm mờ ID nút bấm, các hàng không gán được nút follow (`follow_button is None`), kích hoạt bộ lọc `missing_button_rows` fail-closed.

## Giải pháp chuẩn hóa (Case Fix)
1. **Multi-Anchor Exhaustion Rule (Thử tối thiểu 3 Anchor trước khi fallback):**
   - Module 2 **BẮT BUỘC** phải thử lần lượt tất cả anchor trong danh sách (`uids`, tối thiểu 3 anchor nếu có) trước khi kết luận thất bại.
   - Khi một anchor gặp lỗi UI/mở tab:
     - Ghi nhận cảnh báo cho anchor đó.
     - Điều hướng an toàn về Feed (`_back_to_feed(engine)`).
     - Sử dụng `continue` (thay vì `break`) để thử tiếp anchor kế tiếp.
   - **Chốt chặn fail-closed duy nhất ngắt session ngay lập tức:** Chỉ khi dính `state.follow_failed` hoặc `res.follow_failed` (TikTok nhả follow / shadow drop) thì mới `break` dừng session để bảo vệ nick.
   - Sau khi duyệt hết danh sách anchors:
     - Nếu `used > 0`: `res.status = "OK"`, `res.failed = False` (phần budget còn lại nếu có sẽ do Module 1 chạy bù).
     - Nếu `used == 0` và tất cả anchor đều fail: `res.status = "MANUAL_REVIEW"`, `res.failed = True` -> kích hoạt fail-soft degradation sang Module 1.
2. **Semantic Text Fallback cho Nút Follow:**
   - Trong `_cluster_follower_rows`: Bổ sung semantic text matcher cho node clickable:
     ```python
     button_nodes = [
         n for n in nodes
         if (
             (n.get("resource_id") or "").rstrip("/").endswith(FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS)
             or (n.get("text") or "").strip() in ("Follow", "Follow lại", "Đã follow", "Bạn bè", "Following")
         )
         and n.get("clickable") is True and n.get("bounds")
     ]
     ```
   - Đảm bảo nhận diện chính xác nút bấm quan hệ bất kể resource-id thay đổi.

## Unit Test Hồi Quy
- `test_run_mode2_tries_next_anchor_when_first_anchor_fails`: Kiểm chứng anchor 1 fail mở tab thì runner tự động thử anchor 2 và follow thành công (`opened == ["anchor1", "anchor2"]`, `status == "OK"`).
- `test_cluster_follower_rows_supports_id_u2f` & text matcher.
