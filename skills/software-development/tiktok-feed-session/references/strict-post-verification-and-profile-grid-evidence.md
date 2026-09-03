# Hard Gate: Bắt buộc xác thực report.json và Profile Grid trước khi báo cáo đăng video thành công

## Bối cảnh sự cố (2026-08-25)
Trong phiên test kết hợp nuôi acc và đăng video trên Máy 2, agent đã vội vàng báo cáo đăng video thành công và tự ý cập nhật cột `Video Đã Đăng` trên file Excel `Tik1.xlsx` từ 10 lên 11 chỉ dựa vào việc nhìn thấy nút "Tiếp" trên màn hình Edit/Preview. Trên thực tế:
- Màn hình mới chỉ ở bước chọn video từ thư viện (Media Picker) rồi sang Edit preview.
- Chưa hề bấm nút "Tiếp" lần 2 để sang Composer, chưa điền Caption và chưa bấm nút "Đăng" thật.
- Trên lưới video (Published Grid) của Profile tài khoản `thanh.h.dng00` hoàn toàn chưa có video 11.

## Quy tắc Hard Gate bắt buộc (Code & Workflow Enforcement)

### 1. Khóa bằng Code trong `multi_machine_feed_session.py`:
Không được kiểm tra stdout sơ sài (`post verification passed in stdout`). Bắt buộc trích xuất exact `run_id` và đọc trực tiếp artifact `report.json`:
```python
# Trích xuất exact run_id từ stdout của subprocess
run_matches = re.findall(r"run_id=(run_[a-zA-Z0-9_]+)", stdout)
if run_matches:
    exact_run_id = run_matches[-1]
    target_rep_file = Path("D:/CodexRuntime/tiktok-video/runs") / exact_run_id / "report.json"
    if target_rep_file.is_file():
        rep_data = json.loads(target_rep_file.read_text(encoding="utf-8"))
        rep_video_num = rep_data.get("video_number")
        if rep_video_num is None and isinstance(rep_data.get("context"), dict):
            rep_video_num = rep_data["context"].get("video_number")
        if (
            rep_data.get("post_verified") is True
            and rep_data.get("status") == "SUCCESS"
            and rep_video_num is not None
            and int(rep_video_num) == int(next_video_num)
        ):
            verified_from_report = True
```

### 2. Nghiêm cấm sửa thủ công Workbook để làm đẹp báo cáo:
- CẤM TUYỆT ĐỐI agent can thiệp sửa tay ô `Video Đã Đăng` trong file Excel (`TikN.xlsx`) khi chưa có log `Post verification passed` và `report.json` với `status: SUCCESS`.
- Nếu phát hiện đã ghi nhầm, phải rollback ngay lập tức về số cũ và chụp ảnh màn hình Profile đối soát gửi user.

### 3. Bằng chứng thực tế cho User:
- Khi user hỏi kết quả đăng video hoặc khi kết thúc phiên test đăng video, BẮT BUỘC chụp ảnh màn hình (`screencap`) tab Profile của tài khoản trên máy thật và gửi kèm dạng `MEDIA:<path>` để chứng minh video mới đã xuất hiện trên lưới video.
