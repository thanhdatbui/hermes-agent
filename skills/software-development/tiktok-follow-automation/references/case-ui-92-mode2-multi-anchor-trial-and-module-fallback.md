# Case UI-92: Mode 2 Multi-Anchor Full Trial (Min 3 Anchors) Before Module 1 Fallback

## 1. Bối cảnh & Hiện tượng (Incident)
- **Hiện tượng**: Trong ca nuôi acc (ví dụ Row 2 ngày 04/10/2026), báo cáo telemetry ghi nhận:
  `• Follow chéo: [Module 2 (Anchor): 2 | Module 1 (Bù): 25]`
  Module 2 gần như fail toàn tập trên các máy (M17, M18, M33) với lý do:
  `mode2_degraded_reasons: ["MANUAL_REVIEW: follower row không có nút follow semantic"]`
- **Nguyên nhân gốc rễ (Root Cause)**:
  1. Trong `run_mode2` (`mode2_follow_followers.py`), danh sách anchor seed được lấy tối đa 3 nick (`uids = uids[:3]`).
  2. Khi anchor đầu tiên gặp lỗi UI/layout (chẳng hạn `missing_button_rows` hoặc không mở được tab `open_ok == False`):
     - Runner gán `res.status = "MANUAL_REVIEW"` và đặt cờ `failed = True`.
     - Vòng lặp ngoài kiểm tra `if used >= budget or state.follow_failed or failed: break` -> ngắt sớm ngay lập tức toàn bộ vòng lặp duyệt anchor.
     - Hậu quả: Anchor 2 và Anchor 3 hoàn toàn không bao giờ được thử. Runner ngay lập tức giáng cấp Mode 2 (`mode2_degraded = True`) và đẩy 100% quota cho Module 1 chạy bù.

## 2. Quy tắc nghiệp vụ chuẩn (Business Invariant)
- **Quy tắc Duyệt Đủ Anchor**:
  1. Module 2 **BẮT BUỘC** phải duyệt lần lượt tất cả anchor trong danh sách (`uids`, tối thiểu 3 anchor Tik1/Tik2) trước khi được phép kết luận Mode 2 thất bại.
  2. Lỗi UI/layout trên 1 anchor (như `missing_button_rows`, không mở được Following tab, recycler view surface tạm thời invalid, v.v.) chỉ là lỗi cục bộ của Anchor đó, **TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP làm sập toàn bộ session Mode 2**.
  3. Khi 1 anchor lỗi:
     - Ghi nhận cảnh báo / lý do lỗi của anchor đó.
     - Điều hướng an toàn về Feed (`_back_to_feed(engine)`).
     - **Tiếp tục thử Anchor tiếp theo** trong danh sách (`continue`).
  4. Điều kiện duy nhất được phép ngắt khẩn cấp toàn bộ session Mode 2 là:
     - Tài khoản bị TikTok nhả/chặn follow (`state.follow_failed` hoặc `res.follow_failed`).
     - Đã đạt đủ ngân sách phiên (`used >= budget`).
     - Hết thời gian thực thi an toàn (`not engine.has_time_for_next_action(reserve_seconds=180.0)`).

## 3. Phân định kết quả Mode 2 & Bàn giao Module 1
- **Trường hợp 1 (Thành công trọn vẹn)**:
  Một hoặc nhiều anchor cung cấp đủ quota (`used >= budget`):
  -> Mode 2 hoàn thành với `status: "OK"`, Module 1 không cần chạy bù.
- **Trường hợp 2 (Thành công một phần)**:
  Các anchor cung cấp được một phần quota (`0 < used < budget`):
  -> Mode 2 kết thúc với `status: "OK"`. Module 1 trong `follow_engine.py` chỉ chạy tìm kiếm bổ sung phần ngân sách còn thiếu (`budget - used`).
- **Trường hợp 3 (Tất cả anchor đều fail)**:
  Tất cả các anchor trong danh sách đều đã được thử và đều thất bại (`used == 0` và có lỗi):
  -> Mode 2 báo `status: "MANUAL_REVIEW"` kèm tổng hợp lý do các anchor.
  -> `follow_engine.py` kích hoạt `mode2_degraded = True`, reset status về `OK` và bàn giao toàn bộ 100% ngân sách cho Module 1 chạy bù.

## 4. Pitfall Selector Nút Bấm Trong Follower List
- **Subtitle / Badge "Follow  " vs Nút Follow Thật**:
  - Trên layout RecyclerView của TikTok, một số hàng có thông tin phụ (như "Followed by..." / "Được follow bởi...") mang nhãn có chứa chữ "Follow" (ví dụ `id/u2q`, bounds cột bên trái `x < 600`).
  - Nút bấm quan hệ thật (Action button) luôn nằm ở cột bên phải (`x >= 600` hoặc mang resource-id trong `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS`: `tcj`, `thb`, `tvn`, `tum`, `u2f`, `u68`, `ubp`).
  - CẤM nhận diện nút bấm bằng text thuần túy mà không kiểm tra resource-id hoặc bounds toạ độ `x >= 600`, vì sẽ làm 1 hàng bị gán 2 nút bấm -> kích hoạt cờ `ambiguous_button = True` và làm mất nút của hàng đó.
