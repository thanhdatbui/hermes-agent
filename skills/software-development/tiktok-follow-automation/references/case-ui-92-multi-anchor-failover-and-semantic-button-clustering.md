# Case UI-92: Multi-Anchor Failover Ladder & Semantic Text Button Clustering Trong Module 2 (TikTok Follow)

> **Mốc thời gian:** 04/10/2026  
> **Ngữ cảnh:** Ca nuôi acc Row 2 (Sáng), báo cáo watchdog ghi nhận `Module 2 (Anchor): 2 | Module 1 (Bù): 25`. Module 2 bị rớt sạch trên các máy sống sót (M17, M18, M33) do lỗi `MANUAL_REVIEW: follower row không có nút follow semantic`, dẫn đến Module 1 phải gánh 100% quota follow bù.  
> **Chỉ thị User (Hard Invariant):** *"Mà module chạy ít nhất 3 anchor đều fail ms đc qua module 1 chứ?"* — Module 2 BẮT BUỘC phải thử tối thiểu 3 anchor; chỉ khi CẢ 3 ANCHOR ĐỀU FAIL thì mới được chuyển giao cho Module 1.

---

## 1. Hiện Tượng & Nguyên Nhân Kỹ Thuật Gốc Rễ (Root Cause)

### Anti-Pattern 1: Break Vòng Lặp Sớm Khi Anchor 1 Lỗi UI (Premature Multi-Anchor Abort)
- Trong `follow_runner/flows/mode2_follow_followers.py`:
  - Hàm `run_mode2` lấy tối đa 3 anchor Tik1/Tik2: `uids = uids[:3]`.
  - Tuy nhiên, cờ `failed = False` được dùng chung trên toàn bộ hàm.
  - Khi Anchor 1 vấp phải bất kỳ lỗi UI nào (như `missing_button_rows`, `_open_following_tab` thất bại sau ladder, `surface != populated`, hoặc `scrolls >= max_scrolls`):
    ```python
    if missing_button_rows:
        res.status = "MANUAL_REVIEW"
        res.reason = "MANUAL_REVIEW: follower row không có nút follow semantic"
        failed = True
        break
    ```
  - Lệnh `break` ngắt vòng lặp lướt follower của Anchor 1. Nhưng ngay sau đó, ở vòng lặp ngoài `for uid in uids:`, điều kiện kiểm tra:
    ```python
    if used >= budget or state.follow_failed or failed:
        break
    ```
    thấy `failed == True` nên **BREAK LUÔN CẢ VÒNG LẶP NGOÀI**!
  - **Hậu quả:** Anchor 2 và Anchor 3 hoàn toàn không bao giờ được thử. Một lỗi layout nhỏ trên danh sách của Anchor 1 đã làm sập toàn bộ Module 2 trên máy, kích hoạt `mode2_degraded = True` và đẩy toàn bộ việc sang Module 1.

### Anti-Pattern 2: Nút Follow Bị Bỏ Sót Do Lọc Cứng Theo Resource-ID Trong `_cluster_follower_rows`
- Trong `_cluster_follower_rows`:
  - `button_nodes` ban đầu chỉ lọc các node có `resource_id.endswith(FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS)`.
  - Trên các phiên bản TikTok mới hoặc biến thể layout khác nhau, nếu resource-id của nút hành động bị làm mờ (obfuscated) hoặc thay đổi, hàm phân cụm không gán được nút vào hàng (`r["follow_button"] is None`).
  - Hàng người dùng nội bộ (`internal_uids`) bị rơi vào `missing_button_rows`, kích hoạt ngắt phiên `MANUAL_REVIEW: follower row không có nút follow semantic`.

---

## 2. Quy Chuẩn Vận Hành & Thiết Kế Đã Cố Định (Canonical Solution)

### A. Quy Tắc Bất Biến Duyệt Ít Nhất 3 Anchor (Multi-Anchor Failover Invariant)
1. **Duyệt Đủ Candidate Pool:**
   - Module 2 phải duyệt qua tất cả anchor trong `uids` (tối thiểu 3 anchor nếu pool có đủ).
   - Vòng lặp ngoài `for uid in uids:` **CẤM** break do cờ `failed` của anchor trước đó.
2. **Anchor-Specific Error Recovery:**
   - Khi một anchor gặp lỗi UI/layout (không quay về được Feed, swipe fail, mở tab fail, surface invalid, missing button, scroll cap):
     * Ghi nhận lỗi chi tiết vào danh sách lỗi anchor: `anchor_errors.append(f"@{uid}: {reason}")`.
     * Thu dọn giao diện an toàn về Feed: `_back_to_feed(engine)` (hoặc `engine.recover_ui() and _back_to_feed(engine)`).
     * **`continue` chuyển sang Anchor tiếp theo trong danh sách!**
3. **Điều Kiện Ngắt Session Khẩn Cấp (Chỉ Khi Account Bị Phạt):**
   - Chỉ được break ngay lập tức khỏi toàn bộ session khi:
     * `state.follow_failed` hoặc `res.follow_failed` (Tài khoản bị TikTok nhả follow sau reload / shadow drop).
     * Đã đạt budget (`used >= budget`).
     * Hết deadline an toàn của phiên (`not engine.has_time_for_next_action(reserve_seconds=180.0)`).
4. **Phân Định Trạng Thái Kết Thúc Mode 2:**
   - **`state.follow_failed`**: Trả về `STATE_FOLLOW_FAILED`, dừng toàn bộ follow (không chạy Module 1).
   - **`used >= budget`**: Trả về `status = "OK"`, Module 2 hoàn thành 100% quota.
   - **`0 < used < budget`**: Trả về `status = "OK"`, ghi nhận `used` lượt. `follow_engine.py` tự động kích hoạt Module 1 chạy bù đúng `budget - used` lượt còn thiếu.
   - **`used == 0` và `anchor_errors`**: Cả 3 anchor đều thử và đều fail. Trả về `status = "MANUAL_REVIEW"` kèm tổng hợp lỗi: `res.reason = f"MANUAL_REVIEW: tất cả {len(uids)} anchor đều fail trong Mode 2: {'; '.join(anchor_errors)}"`. `follow_engine.py` kích hoạt `mode2_degraded = True`, reset status về `OK` và bàn giao 100% quota cho Module 1 bù.
   - **`used == 0` và không có lỗi**: Các anchor hợp lệ nhưng đã hết nick hoặc 0 following -> Trả về `status = "OK"`, bàn giao cho Module 1.

### B. Gia Cố Semantic Text Matcher Cho Nút Follow
- Bổ sung semantic text matcher vào `button_nodes` trong `_cluster_follower_rows`:
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
- Bất kể resource-id thay đổi sang giá trị nào, nếu node clickable có text quan hệ tiêu chuẩn thì vẫn được nhận diện chính xác là nút follow của row.

### C. Ưu Tiên Nick Nội Bộ Có Nút Hợp Lệ (`internal_pending` Priority)
- Trong trường hợp màn hình có một số hàng bị thiếu nút do layout mép hoặc lỗi rendering, nhưng vẫn có các hàng `internal_pending` có nút follow hợp lệ:
  * Runner không được ngắt phiên ngay, mà ưu tiên xử lý follow các nick hợp lệ trong `internal_pending` trước.
  * Chỉ khi toàn bộ các hàng nội bộ trên màn hình đều thiếu nút (`missing_button_rows` có nick nhưng `internal_pending` rỗng) mới kết luận anchor đó lỗi layout và chuyển sang anchor tiếp theo.

---

## 3. Checklist Triage Nhanh Cho Điều Phối Viên (Coordinator Checklist)

Khi thấy báo cáo Watchdog lệch `[Module 2: 0..2 | Module 1: X]`:
1. Kiểm tra số máy bị nhả follow ở Anchor (`follow_failed`): Những máy này dừng fail-closed ngay lập tức là hành vi đúng.
2. Kiểm tra số máy sống sót: Đọc `mode2_degraded_reasons` trong `follow_result.json`.
3. Nếu lý do là `follower row không có nút follow semantic` hoặc lỗi mở tab:
   - Đối soát xem runner đã thử qua đủ 3 anchor chưa.
   - Kiểm tra xem bản vá Case UI-92 (Multi-Anchor Failover + Semantic Text Matcher) đã có hiệu lực trên repo chưa.
