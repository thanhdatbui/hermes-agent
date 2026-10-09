# Post-Evening Avatar Watchdog: DB Rescan, Delta Ca Tối & Cụm Lỗi Farm Alert

## Bối Cảnh & Vấn Đề
`post_evening_avatar_watchdog.py` chạy cuốn chiếu ca tối (21:00 -> 23:45) cho các máy chưa có Avatar (`Avatar != 'OK'`).
Khi nâng cấp cơ chế báo cáo và đồng bộ cho watchdog:
1. **Thiếu Rescan DB**: Khi batch chạy xong qua `check_batch_status`, watchdog trước đây chỉ reset `state['running_batch'] = None`. Cần tự động trigger rescan các máy vừa hoàn tất để đồng bộ vào workbook / database tracker ngay lập tức thay vì đợi lần scan sau.
2. **Thiếu số liệu Delta ca tối (+X acc mới)**: Báo cáo chỉ hiển thị số lũy kế tĩnh (`Đã có 78/80`), không phản ánh phiên ca tối nay đã upload thành công thêm bao nhiêu tài khoản mới.
3. **Thiếu cụm lỗi chi tiết**: Khi các máy thất bại, Farm Alert cần gom nhóm theo mã lỗi (`Reason` từ `summary.csv` của batch run) để người vận hành biết chính xác nguyên nhân (ví dụ: `AVATAR_UPLOAD_MENU_MISSING`, `DEVICE_OFFLINE`, `ACCOUNT_SWITCHER_FAILED`) thay vì chỉ báo danh sách máy chưa xong.

## Cấu Trúc Dữ Liệu Batch Run (`summary.csv`)
Các batch upload avatar được `run_tiktok_upload_batch.ps1` tạo ra tại:
`D:\CodexRuntime\tiktok-video\batch-runs\batch_tik{Tik}_{TargetLabel}_{Timestamp}\summary.csv`
Các cột quan trọng cần đọc:
- `Machine` (hoặc `machine_id`): số thứ tự máy (int).
- `Status` (hoặc `status`): `AVATAR_SMOKE_SUCCESS`, `SUCCESS`, v.v.
- `Verified`: `True` / `False`.
- `Reason` / `Error`: chuỗi lỗi (chuẩn hóa về các signature chính).

## Quy Trình Xử Lý Chuẩn (Pattern)
1. **Thu thập kết quả batch vừa chạy (`collect_recent_batch_results`)**:
   - Quét thư mục batch run mới nhất của Tik tương ứng.
   - Parse `summary.csv`, phân tách:
     - `succeeded_machines`: máy có status thành công / verified.
     - `failed_by_reason`: map `reason -> list[int]`.
2. **Rescan DB & Cập nhật State trong `check_batch_status`**:
   - Khi batch process kết thúc:
     - Gọi rescan cho `running["machines"]` đã hoàn thành.
     - Thu thập `succeeded` và `failed_by_reason`.
     - Tích lũy vào state của session hiện tại: `state["session_uploaded_machines"]` và `state["session_failed_by_reason"]`.
3. **Hiển thị báo cáo Farm Alert (`format_report_html`)**:
   - Hiển thị dòng tổng kết ca tối:
     `• <b>Kết quả ca tối nay:</b> Thành công +{up_cnt} acc mới | Lỗi {fail_cnt} máy`
   - Hiển thị block cụm lỗi chi tiết nếu có máy lỗi:
     ```html
     📋 <b>CHI TIẾT CỤM LỖI CA TỐI NAY:</b>
       ❌ [AVATAR_UPLOAD_MENU_MISSING] (3 máy): 12, 15, 18
       ❌ [DEVICE_OFFLINE] (1 máy): 45
     ```
   - Nếu không có lỗi: `• <b>Kết quả ca tối nay:</b> Hoàn tất 100%, không ghi nhận lỗi.`
