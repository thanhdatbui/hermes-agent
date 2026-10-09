# Follow Hook Watchdog Race Condition & False UI/Script Alert Guard

## 1. Triệu chứng & Bối cảnh
- **Farm Alert**: Nhận cảnh báo đỏ diện rộng `🚨 [FARM ALERT] PHÁT HIỆN LỖI DIỆN RỘNG (>10 MÁY)` với nội dung: `⚠️ Follow Hook Lỗi UI/Script (22 máy): 1, 5, 6, 8, ...` hoặc `Lỗi script/xác minh (70): 2, 3, 4, 5, ...`.
- **Thực tế thiết bị**:
  - Không có máy nào bị crash UI hay exception trong script Python.
  - Cả 70-80 máy đều đã hoàn thành lướt Feed thành công (`status: "success"`).
  - Khâu Follow hook hoàn toàn **không bị lỗi 70 máy**; thực tế chỉ có 0-2 máy cần review, hàng chục máy đã follow thành công hoặc skip an toàn (daily cooldown, < 5 video).
  - Toàn bộ kết quả follow được ghi nhận đầy đủ vào `follow_result.json` tại artifact từng máy sau khi batch kết thúc.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Flaw 1: `can_report_session` ưu tiên Feed completion trước `runner_busy`**:
   - Khi đang trong giờ phiên (`now_hm < window_end_hm`):
     ```python
     if completed_expected_count >= expected_count and not has_unattempted_locked:
         return True
     if runner_busy:
         return False
     ```
   - `completed_expected_count` chỉ tính máy đã xong khâu **Feed** (`all_machines`).
   - Khi 80/80 máy lướt xong Feed (ví dụ lúc 06:56), `completed_expected_count >= 80` trở thành `True`.
   - Vì dòng kiểm tra số lượng nằm TRƯỚC `if runner_busy: return False`, Watchdog vội vàng chốt phiên ngay lập tức dù tiến trình runner vẫn đang chạy xử lý Follow hook cho các máy sau (máy 29 đến 07:00:29 mới xong).
2. **Flaw 2: Watchdog ép chốt phiên khi hết Grace Period**:
   - Khung giờ phiên kết thúc (ví dụ Ca 4 Phiên 1 kết thúc lúc `01:30`).
   - Watchdog có cơ chế `grace_end_hm = _add_minutes_to_hm(window_end_hm, 20)`. Lúc `01:50:00`, grace period hết hạn.
   - Tại tick `01:50:21`, watchdog thức dậy và ép gọi `can_report_session() -> True` mặc dù tiến trình runner vẫn đang chạy dở các máy còn lại.
3. **Flaw 3: Fallback gán nhãn sai & State Lock 1 chiều**:
   - Khi runner đang ghi file đĩa, watchdog duyệt cây thư mục nhưng chưa load kịp hoặc bị thiếu `follow_result.json`.
   - Watchdog đánh đồng việc "chưa có file follow_result trong khi Feed success" là một lỗi kịch bản (`fl_error.append(m)`).
   - Ngay sau khi in tin nhắn, session key bị ghi vào `feed_session_reported.json` (state lock), khiến các tick 5 phút sau không bao giờ tái đánh giá lại dù file trên đĩa đã ghi xong 100%.

## 3. Quy chuẩn sửa chữa (Patch Contract)
1. **Thứ tự ưu tiên trong `can_report_session()`**:
   Trong khung giờ phiên (`now_hm < window_end_hm`), nếu `runner_busy == True`, BẮT BUỘC trả về `False` (chờ runner thoát hẳn mới được chốt, bất kể số máy Feed đã xong hay chưa):
   ```python
   # Nếu đang trong giờ phiên (now_hm < window_end_hm):
   if is_today and now_hm < window_end_hm:
       # BẮT BUỘC: Nếu runner còn đang bận, tuyệt đối không chốt sớm
       if runner_busy:
           return False
       if completed_expected_count >= expected_count and not has_unattempted_locked:
           return True
   ```
2. **Phân loại an toàn khi thiếu dữ liệu follow (`feed_session_watchdog.py`)**:
   Nếu máy có `Feed == success` nhưng chưa có trong `all_follows`, kiểm tra nếu `runner_busy` đang `True` thì đưa vào `fl_skipped` thay vì `fl_error`:
   ```python
   else:
       if all_machines[m].get("status") == "success":
           if runner_busy:
               fl_skipped.append(m)
           else:
               fl_error.append(m)
   ```
3. **Đồng bộ nghiêm ngặt 3 vị trí (Tránh Sync Drift)**:
   - Script chạy thực tế của Kibe: `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
   - Git repository chuẩn: `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py`
   - Repo tiêu thụ: `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`
