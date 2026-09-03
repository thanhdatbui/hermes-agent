# Feed Watchdog Multi-Run Merge, Clean Follow Release, and Gating (Case 51)

## Bối cảnh & Nguyên nhân sự cố
Khi một phiên nuôi acc TikTok (ví dụ Ca 1 Phiên 3 từ 09:30 đến 12:00) chạy nhiều đợt quét (đợt 1 chạy chính lúc 09:30, đợt 2 chạy vét lúc 10:30, đợt 3 quét máy lúc 11:30):
1. **Lỗi ghi đè kết quả Upload Video:** Đợt 1 có 53 máy upload thành công, đợt 2 có thêm 9 máy thành công (tổng 62 máy). Sang đợt 3, các máy đã đăng xong được gán nhãn `already_uploaded_in_shift` (thuộc diện skip). Nếu watchdog dùng gán đè trực tiếp `all_uploads[m] = data`, toàn bộ 62 máy `success` bị đè thành `skipped`, khiến báo cáo Telegram xuất hiện "0 video đã đăng, bỏ qua 68".
2. **Lỗi ghi đè nhả follow:** Nếu máy bị nhả follow ở đợt đầu (`FOLLOW_FAILED`), đợt sau máy dính daily cooldown (`skipped`), gán đè trực tiếp làm mất thông tin nhả follow.
3. **Lỗi nhận diện tiến trình bận:** `is_feed_runner_active()` dùng chuỗi so khớp lỏng lẻo (`run_follow`) bắt nhầm các lệnh tiện ích (`grep.exe -rn run_follow`) khiến watchdog tưởng runner đang bận và hoãn báo cáo.
4. **Lỗi treo báo cáo phiên:** Điều kiện chốt báo cáo bị chặn khi runner chạy gối đầu sang phiên tiếp theo mà không tự chốt khi hết khung giờ phiên.

## Quy tắc Merge Đa lượt chạy (Multi-Run Atomic Merge)
Mọi dữ liệu từ các lần chạy trong cùng một khung phiên phải được gộp qua hàm nguyên tử:
1. **`merge_machine_result(prev, new)`**:
   - Ưu tiên giữ trạng thái `success` nếu máy thành công ở bất kỳ đợt nào.
2. **`merge_follow_result(prev, new)`**:
   - Giữ cờ `FOLLOW_FAILED` nếu bất kỳ đợt nào phát hiện nhả follow.
   - Gộp danh sách `followed` không trùng lặp (`dict.fromkeys(prev_flist + new_flist)`), chuẩn hóa string các phần tử `(str, int, float)` để tránh `TypeError: unhashable type` nếu có object/dict lồng nhau.
   - Không để kết quả `SKIPPED` hoặc `MANUAL_REVIEW` ở đợt sau xóa mất danh sách tài khoản đã follow ở đợt trước.
3. **`merge_upload_result(prev, new)`**:
   - Giữ trạng thái `success` (`exit_code == 0`) của đợt trước, không để `already_uploaded_in_shift` hoặc `skipped` ở đợt sau ghi đè.

## Quy tắc Strict Clean Follow Release
Chỉ ghi nhận máy thuộc nhóm `Nhả follow` (`fl_released`) khi thỏa mãn đồng thời:
- `status == "FOLLOW_FAILED"`
- `follow_failed is True` (bắt buộc kiểu boolean `True`, không nhận string `"false"` hoặc integer `1`)
- `is_strict_zero_failed` (`raw_failed is False` hoặc `type(raw_failed) is int and raw_failed == 0`).
Các trường hợp `FOLLOW_FAILED` thiếu trường `failed` hoặc có lỗi kỹ thuật (`failed != 0`) BẮT BUỘC xếp vào nhóm `fl_error` và kích hoạt Farm Alert.

## Quy tắc Lọc Tiến trình & Chốt Báo cáo Phiên
1. **Process Name Filter:** `is_feed_runner_active()` chỉ kiểm tra các tiến trình bắt đầu bằng `python`, `powershell`, `pwsh`, loại bỏ toàn bộ `grep`, `findstr`, `cat`.
2. **Session Window Closure (`can_report_session`):**
   - Với ngày hiện tại (`is_today=True`): Chốt báo cáo khi `len(completed_expected) >= expected_count and not runner_busy` HOẶC khi đã qua mốc kết thúc phiên (`now_hm >= win["end"]`).
   - Với ngày đã qua (`is_today=False` / rollover): Luôn chốt báo cáo ngay lập tức (`can_report = True`) để không bị runner hôm nay chặn báo cáo hôm qua.
