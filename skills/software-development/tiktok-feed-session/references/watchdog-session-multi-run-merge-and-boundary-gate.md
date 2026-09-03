# Watchdog Session Multi-run Merge and Boundary Trigger Gate

## 1. Bản chất sự cố Multi-Run Merge (Case 51)
Khi một phiên nuôi acc (1 ca 3 phiên) chia làm nhiều đợt quét (ví dụ: đợt chính lúc 06:00, đợt quét vét máy bận lúc 06:45, 07:15):
- **Hiện tượng nhả Follow bị ghi đè:** Máy bị `FOLLOW_FAILED` ở đợt 1 được hệ thống ghi nhận `follow_failed_date = today`. Sang đợt 2, khi script follow chạy lại, nó kiểm tra cooldown và trả về `status: "skipped", reason: "follow-released-daily-cooldown"`. Nếu watchdog gán đè trực tiếp `all_follows[m] = data`, cờ `FOLLOW_FAILED` của đợt 1 sẽ bị biến mất thành `skipped`.
- **Hiện tượng Đăng Video bị xóa thành 0 video:** Ở phiên 3, máy đã đăng video thành công ở đợt 1 (`exit_code: 0, status: "success"`). Sang đợt 2/3, máy trả về `reason: "already_uploaded_in_shift"`. Nếu gán đè trực tiếp, 100% video thành công bị ghi đè thành skipped, dẫn tới báo cáo "Đăng video: 0 video đã đăng, Bỏ qua 68".

## 2. Quy tắc Merge Kết quả Nguyên tử (Atomic Multi-run Merge)
Watchdog tổng kết phiên BẮT BUỘC dùng hàm merge chuyên biệt:
1. **`merge_follow_result(prev, new)`:**
   - Bảo toàn cờ `FOLLOW_FAILED` (`follow_failed is True`): nếu bất kỳ đợt nào trong phiên phát hiện nhả follow sạch, trạng thái cuối cùng BẮT BUỘC là `FOLLOW_FAILED`.
   - Tích lũy danh sách `followed`: gộp danh sách các tài khoản follow thành công qua `list(dict.fromkeys(prev_flist + new_flist))`.
   - Lọc an toàn kiểu dữ liệu: chỉ nhận các phần tử kiểu nguyên thủy `(str, int, float)` trong `followed`, loại bỏ list/dict để tránh `TypeError: unhashable type`.
2. **`merge_upload_result(prev, new)`:**
   - Ưu tiên trạng thái thành công (`status == 'success' and exit_code == 0`).
   - Lượt chạy sau có `already_uploaded_in_shift` hoặc `skipped` tuyệt đối không được ghi đè lượt đã đăng video thành công trước đó.
3. **`merge_machine_result(prev, new)`:**
   - Ưu tiên trạng thái `success` của phiên feed.

## 3. Điều kiện Chốt Báo cáo Phiên (`can_report_session`)
Tránh chốt sớm gây báo cáo thiếu máy (ví dụ báo 5 máy thay vì 73 máy):
- Khi runner đang chạy (`runner_busy == True`): **BẮT BUỘC trả về `False`**, kể cả khi thời gian hiện tại đã vượt qua mốc kết thúc phiên (`now_hm >= window_end_hm`).
- Chỉ khi runner đã dừng hẳn (`not runner_busy`), watchdog mới được phép kích hoạt chốt báo cáo khi:
  1. Toàn bộ máy dự kiến đã hoàn tất (`completed_expected >= expected_count`), HOẶC
  2. Đã hết khung giờ phiên (`now_hm >= window_end_hm`).
- Với ngày đã qua (`is_today == False` / rollover): chốt ngay khi runner rảnh để không làm nghẽn báo cáo ngày hôm trước.

## 4. Quy tắc Lọc ID TikTok trong Workbook Sync (`sync-tik-workbooks.py`)
- CẤM hardcode substring hoặc username thật (`ngomai.ly`, `vo.my`) vào bộ lọc rác `is_valid_tiktok_id`.
- Bộ lọc chỉ chặn link placeholder (`http://`, `https://`), khoảng trắng, rác (`none`, `null`, `ghjfghj`), số thuần túy hoặc dấu chấm ở đầu/cuối chuỗi (`s.startswith('.')` / `s.endswith('.')`).
