# Video Sequence Gap & Automatic Next Video Fallback

## 1. Vấn đề thực tế (Root Cause)
- Khi render video từ kho nguồn hoặc gán video cho các kênh, file video trong thư mục có thể bị khuyết số hoặc nhảy cóc số thứ tự (ví dụ: `1.mp4, 2.mp4, 3.mp4, 4.mp4, 6.mp4, 7.mp4...` — khuyết `5.mp4`).
- Nếu bộ điều phối upload (`_run_upload_hook` hoặc `resolve_video_path`) chỉ kiểm tra cứng `next_video = posted_count + 1`:
  - Khi nick đã đăng video 4, hệ thống tìm cứng `5.mp4`.
  - Do `5.mp4` không tồn tại, Gate 5 kích hoạt `Safe-Skip` (`reason: "video_not_rendered"`).
  - Kết quả: Nick bị dừng đăng hoàn toàn suốt nhiều ngày/nhiều tuần dù trong kho vẫn còn hàng chục clip (`6.mp4` trở đi).

## 2. Quy tắc xử lý bắt buộc (User Policy)
> **"Nếu không tìm ra file video theo số thứ tự tiếp theo thì BẮT BUỘC tự động đăng video tiếp theo có sẵn trong thư mục."**

### Cơ chế Fallback Chuẩn:
1. **Tìm video tiếp theo có sẵn (`candidates > posted_count`):**
   - Quét các file `.mp4` trong `folder_video` có tên file là số nguyên (`item.stem.isdigit()`) và kích thước file > 0 bytes.
   - Lọc các số `num > posted_count`.
   - Lấy số nhỏ nhất trong các ứng viên khả dụng: `next_video = min(candidates)`.
2. **Cập nhật tiến trình đúng số thực tế:**
   - Khi upload thành công video số `N`, ghi nhận `Video Đã Đăng = N` vào Workbook và lịch sử upload (`shift_upload_history.json`).
   - Tuyệt đối không lùi số (`posted_count` chỉ tăng đơn điệu).
3. **Chỉ Safe-Skip khi thực sự cạn kho:**
   - Chỉ khi tập `candidates` rỗng (toàn bộ video `> posted_count` đều không còn) thì mới xác nhận nick đã hết kho video (`no_remaining_videos` / `video_not_rendered`).

## 3. Chuẩn hóa tên file (Normalizing Stale Gaps)
- Khi phát hiện một folder video bị khuyết số thứ tự do giữ nguyên số từ folder gốc:
  - Đổi tên tuần tự các file còn lại về chuỗi số liên tục (`5.mp4, 6.mp4, 7.mp4...`).
  - Đảm bảo file `avatar.jpg` không bị ảnh hưởng.

## 4. Bẫy Silent Safe-Skip & Quy Trình Điều Tra Kênh Dừng Đăng
- **Bẫy Silent Safe-Skip (`reason: "video_not_rendered"`):**
  - Gate 5 khi không tìm thấy file `{next_video}.mp4` sẽ trả về `status: "skipped", reason: "video_not_rendered"`.
  - Đây là cơ chế safe-skip để không làm crash toàn bộ session lướt nuôi acc của máy. Do đó, watchdog phân loại vào nhóm `• Bỏ qua an toàn`, **hoàn toàn KHÔNG phát cảnh báo đỏ (Red Alert)**.
  - Hậu quả: Kênh có thể bị dừng đăng âm thầm 1-2 tuần dù kho còn nhiều clip và máy vẫn chạy nuôi hàng ngày.
- **Quy trình 3 bước điều tra khi User hỏi "Sao nick lâu không đăng video":**
  1. **Bước 1 (Định danh):** Tra cứu `taikhoan_run_safe.xlsx` hoặc `Tik1..TikN.xlsx` để lấy: Số Máy, Slot, `Folder Video`, và `Video Đã Đăng` hiện tại.
  2. **Bước 2 (Lịch sử upload):** Tìm trong `C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json` các bản ghi của username hoặc `m<May>_row<Slot>` để xác định ngày và video cuối cùng đăng thành công.
  3. **Bước 3 (Kho video):** Kiểm tra thư mục `D:\TIKTOK-videonuoinick\<Folder_Video>\` xem file `{Video Đã Đăng + 1}.mp4` có tồn tại và kích thước > 0 hay không. So sánh với danh sách các file `.mp4` hiện có trong folder để phát hiện khoảng trống nhảy cóc số.

## 5. Kỹ Thuật Cầu Nối Cấp Tốc Tại Hiện Trường (Bridge File Hotfix)
- Khi phát hiện kênh bị dừng do khuyết số (ví dụ: cần `5.mp4` nhưng folder chỉ có `6.mp4` trở đi) trong khi ca chạy sắp tới:
  - **Cứu nguy tức thì (0-Downtime Hotfix):** Sao chép file kế tiếp có sẵn sang tên file đang thiếu:
    ```bash
    cp "D:/TIKTOK-videonuoinick/<Folder_ID>/6.mp4" "D:/TIKTOK-videonuoinick/<Folder_ID>/5.mp4"
    ```
    Thao tác này lập tức mở khóa Gate 5 cho ca chạy kế tiếp đăng video thành công ngay lập tức mà không cần chờ đợi deploy code.

## 6. Code Pattern Chuẩn Cho Preflight Gate 5 (`multi_machine_feed_session.py`)
Khi triển khai code xử lý Gate 5, sử dụng logic tìm video nhỏ nhất còn tồn tại $\ge next\_video$:
```python
# Gate 5: Check next video render with automatic sequence gap fallback
media_root = Path(ctx.config.get("media_source_root") or host_paths["media_source_root"])
f_dir = media_root / folder_video
rem = [
    int(f.stem) for f in f_dir.glob("*.mp4")
    if f.stem.isdigit() and f.stat().st_size > 0 and int(f.stem) >= next_video
] if f_dir.is_dir() else []
if rem:
    next_video = min(rem)
video_file = f_dir / f"{next_video}.mp4"

if not video_file.is_file() or video_file.stat().st_size == 0:
    payload = {
        "machine": account.machine,
        "row": account.account_row_index,
        "status": "skipped",
        "reason": "video_not_rendered",
        "expected_video": str(video_file),
        "workbook": workbook_path.name,
    }
    _write_upload_result(child_ctx, payload)
    return payload
```

## 7. Hợp đồng truyền tham số `--video-number` & Đồng bộ sổ cái
- **Downstream CLI Contract:**
  Khi Gate 5 chọn `next_video` (ví dụ từ 4 nhảy lên 11), nó truyền trực tiếp tham số `--video-number <next_video>` vào lệnh gọi `scripts.tiktok_workflow`.
- **Workbook Cursor Synchronization:**
  Trong `scripts.tiktok_workflow`:
  - `run_post.py` ghi nhận: `context.config["video_number_override"] = video_number`.
  - State `RESOLVE_NEXT_VIDEO` sử dụng số override này thay cho cursor thông thường.
  - State `UPDATE_WORKBOOK` sau khi đăng thành công sẽ cập nhật cột `Video Đã Đăng` trong workbook thành đúng số video vừa đăng (`11`).
  - Ở ca chạy kế tiếp, hệ thống tìm từ `11 + 1 = 12` trở đi, bảo đảm tiến trình tăng đơn điệu và không bao giờ bị lùi số hay đăng lặp lại.
- **Lưu ý kiểm thử focused & Bẫy Organic Rest Day:**
  Khi viết test cho Gate 5 trong `test_upload_hook.py`:
  - `_make_dummy_context` không set sẵn `_is_organic_rest`, khiến `_run_upload_hook` tự động kiểm tra `_is_account_organic_rest_day` theo ngày thực tế trên máy host. Nếu chạy test trúng ngày dưỡng sinh, test sẽ bị fail sớm với lỗi `organic-rest-day-upload-disabled` trước khi chạm tới Gate 5!
  - Khắc phục trong production code: Trong `_run_upload_hook`, nếu `ctx.mode == "test"` và `_is_organic_rest` chưa khai báo thì mặc định `is_organic = False` để bảo đảm test harness chạy cô lập và độc lập với lịch dưỡng sinh vật lý.

## 8. Chuẩn Telemetry Bắt Buộc Khi Tự Động Fallback
- Khi kích hoạt fallback chọn số video tiếp theo, BẮT BUỘC phải phát structured log để quan sát và đối soát:
```python
logger.info(
    "[UPLOAD_HOOK_TELEMETRY] event=video_fallback machine=%s folder=%s missing_video=%s fallback_selected=%s",
    account.machine, folder_video, next_video, fallback_video,
)
```
- Trường dữ liệu tối thiểu: `machine`, `folder`, `missing_video`, `fallback_selected`.
- Khi viết unit test, dùng fixture `caplog` để assert chính xác log format này được phát ra.

## 9. Tiêu Chuẩn Thẩm Định Closeout Gate Cho Feature Video Fallback (Sol Rubric)
Khi đóng phiên (Closeout Gate) cho các thay đổi trong pipeline upload:
1. **Không giới hạn trần giả định:** Sử dụng `int(f.stem) >= next_video` thay vì giới hạn trần cứng như `range(next_video, 999)`.
2. **Không đánh đồng kiểm tra kích thước với chống file lỗi:** Kiểm tra `f.stat().st_size > 0` chỉ là rào chắn loại bỏ file rỗng / 0-byte, không tuyên bố là bộ giải mã kiểm tra tính toàn vẹn MP4 đầy đủ.
3. **Bằng chứng test 2 lớp:**
   - Unit test focused: Chứng minh `missing_video -> higher_video` fallback thành công và telemetry phát ra.
   - Regression suite: Đảm bảo toàn bộ suite `test_upload_hook.py` (65+ tests) pass sạch để chứng minh các cơ chế downstream (MediaFingerprintLedger, ShiftUploadLedger, idempotency) không bị ảnh hưởng.

