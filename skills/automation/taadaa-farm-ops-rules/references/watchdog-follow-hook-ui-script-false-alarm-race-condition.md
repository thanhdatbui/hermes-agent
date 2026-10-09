# Watchdog False Alarm: Follow Hook Lỗi UI/Script do Race Condition

## Hiện tượng (Symptom)
Watchdog nuôi acc (`feed_session_watchdog.py`) gửi **Farm Alert** đỏ:
`⚠️ Follow Hook Lỗi UI/Script (N máy): 1, 5, 6, 8, ...`
khiến Coordinator hoặc User lầm tưởng script Python follow bị crash hoặc app TikTok văng lỗi hàng loạt trên thiết bị.

## Bản chất nguyên nhân (Root Cause)
1. **Hard-coded Label trong Watchdog**:
   Trong logic phân loại follow của watchdog:
   ```python
   if m in all_follows:
       status = str(fd.get("status") or "").upper()
       if status == "SKIPPED":
           fl_skipped.append(m)
       ...
   else:
       # Nếu máy lướt Feed thành công (status == "success") nhưng watchdog chưa thấy / chưa đọc được kết quả follow
       if all_machines[m].get("status") == "success":
           fl_error.append(m)
   ```
   Và khi xuất chuỗi alert:
   ```python
   alert_lines.append(f"⚠️ <b>Follow Hook Lỗi UI/Script ({follow_err_cnt} máy)</b>: {e_str}")
   ```
   -> Nhãn `"Follow Hook Lỗi UI/Script"` thực chất đại diện cho **bất kỳ máy nào xong Feed mà watchdog chưa đọc được follow_result.json**, hoàn toàn **KHÔNG PHẢI** UI crash hay Script văng lỗi.

2. **Race Condition khi chốt phiên dở dang**:
   - Khi hết giờ phiên hoặc hết grace period (20 phút), watchdog buộc phải chốt báo cáo.
   - Nếu lúc đó một nhóm máy đã hoàn thành Feed và ghi `summary.txt`, nhưng runner vẫn đang chạy song song các máy còn lại (threadpool đang bận ghi đĩa hoặc parse dở), watchdog quét vội dở dang sẽ không kịp khớp `follow_result.json` của các máy đã xong.
   - Kết quả: Các máy này bị đưa thẳng vào `fl_error` vì thiếu file kết quả follow tại thời điểm quét, kích hoạt ngưỡng báo động đỏ diện rộng (>10 máy).

3. **Thực tế an toàn (Safety Gate under-5-videos)**:
   - Trong `multi_machine_feed_session.py`: Nick có `< 5` video đăng bị chặn đi follow (`under-5-videos-follow-disabled`) để tránh bị TikTok phạt nhả follow.
   - Script follow thậm chí còn **chưa bao giờ được invoke** trên thiết bị; trạng thái thực tế ghi nhận là `skipped`.

## Quy trình Triage & Giải thích cho User (Coordinator Checklist)
1. **Kiểm tra `follow_result.json` và `log.jsonl` tại artifact của máy**:
   - Xác nhận có bước `skip_follow_under_5_videos` với `result: "skipped"`.
   - Xác nhận `follow_result.json` có `status: "skipped"` và `reason: "under-5-videos-follow-disabled"`.
2. **Kiểm tra tương quan danh sách**:
   - Nếu danh sách máy báo `"Follow Hook Lỗi UI/Script"` trùng khít 100% với danh sách máy `"Lướt Feed: Success"`, đây là dấu hiệu nhận diện kinh điển của việc watchdog không đọc kịp `follow_result.json` (nhánh `else: fl_error.append(m)`).
3. **Giải thích rõ ràng cho User**:
   - Khẳng định rõ: Không có lỗi UI/Script thật nào xảy ra trên máy.
   - Chỉ rõ dòng code hard-coded label trong watchdog khiến nhãn bị gán sai bản chất.
   - Đính kèm bằng chứng ảnh screencap thực tế của máy (màn hình ngủ `Dozing`, app đóng an toàn về HOME).
