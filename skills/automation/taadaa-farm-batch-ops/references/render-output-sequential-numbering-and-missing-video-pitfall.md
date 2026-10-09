# Pitfall & Quy trình: Lỗi "Render Báo Xong Nhưng Upload Báo Chưa Render / Thiếu Video"

## 1. Triệu chứng & Hiện tượng
- Watchdog render (`farm_render_download_watchdog.py`) thông báo:
  `✅ Tik6: 80/80 folder (≥30 clip) [100.0%] | 3,397 clip`
- Khi tiến trình nuôi nick hoặc batch upload chạy (`feed_session_watchdog.py` / `tiktok_workflow`), hệ thống lại văng cảnh báo:
  `• Đăng Video: Bỏ qua: Chưa render/thiếu video (5 máy)`

## 2. Nguyên nhân gốc rễ
1. **Lệch tiêu chí kiểm tra (Watchdog vs Workflow)**:
   - Render Watchdog chỉ đếm tổng số lượng file `.mp4` trong thư mục: `if count >= 30: done`.
   - Workflow Upload (`tiktok_workflow/path_resolver.py`) tìm video theo công thức tuần tự:
     $$\text{video\_number} = \text{Video Đã Đăng} + 1$$
     Nick chưa đăng (`posted = 0`) bắt buộc phải có file `1.mp4`. Nick đã đăng 1 clip (`posted = 1`) bắt buộc phải có file `2.mp4`.
2. **Lỗi đánh số khi Render (`random_batch_render.py`)**:
   - Khi chọn một tập con video (ví dụ 45 clip) từ folder video gốc `D:\video goc` theo tiêu chí thời lượng/ngẫu nhiên, renderer từng gán:
     `relative_output = relative_source.with_suffix(".mp4")`
   - Điều này làm file output giữ nguyên số thứ tự gốc từ nguồn (ví dụ: bốc các file từ `18.mp4 .. 64.mp4`), dẫn đến folder output hoàn toàn thiếu file `1.mp4` hoặc bị nhảy cóc số.

## 3. Quy tắc Bất Biến (Invariant)
1. **Mã nguồn Render (`random_batch_render.py`)**:
   - BẮT BUỘC luôn ép tên file output tuần tự theo thứ tự task (`seq`):
     ```python
     relative_output = relative_source.parent / f"{seq}.mp4"
     ```
   - Đảm bảo mọi folder render thành phẩm luôn có đủ dãy file liên tục `1.mp4 .. N.mp4`.

2. **Quy trình Renumber an toàn khi chuẩn hóa dữ liệu kho**:
   - **Bảo vệ video đã đăng**: Đọc `posted = int(ws.cell(row, posted_col).value or 0)` từ workbook. Tuyệt đối KHÔNG di chuyển hay đổi tên các file từ `1.mp4` đến `posted.mp4`.
   - **Rename 2 pha chống đè chéo**:
     - Pha 1: Đổi các file chưa đăng sang file tạm `.tmp_ren_{folder}_{target}.mp4`.
     - Pha 2: Đổi từ file tạm sang số đích `(posted + 1).mp4 .. N.mp4`.
   - **Cập nhật Atomic vào Workbook (`TikX.xlsx`)**:
     - Tạo bản sao lưu `.bak`.
     - Cập nhật `Render Status = 'OK'`, `Render MP4 = count`.
     - Ghi qua file tạm `.tmp` rồi `os.replace`.
