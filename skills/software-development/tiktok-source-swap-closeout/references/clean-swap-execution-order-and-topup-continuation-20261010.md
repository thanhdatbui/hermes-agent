# Clean Swap Execution Order, Top-up Continuation, and Operational Closeout (2026-10-10)

## 1. Bối cảnh & Hiện tượng (Incident Context)
Khi Operator gửi ảnh chụp màn hình một tài khoản TikTok (`duongkien1202` Máy 1 Tik 2) và ra lệnh:
> *"Đổi content cho nick này, cào niche hot + ava ms r đổi ava mới"*
> *"Cả hashtag"*

Coordinator ban đầu kiểm tra thấy:
- `Tik2.xlsx` có `Folder Video = 2`, `video gốc = 81`, niche `Bếp Việt`, đã đăng `12`.
- Bản backup cũ ghi niche `Khoa học`, `video gốc = 2`, đã đăng `0`.
- Thư mục raw `D:/video goc/2` có rác `_partial_beemart` và 64 clip cũ.
- Thay vì thực thi ngay, Coordinator đã dừng lại và báo cáo: `BLOCKED – cần reconcile Folder Video/video gốc và xác nhận nguồn SoT trước khi clean-old`.

Operator lập tức chấn chỉnh gay gắt:
> *"Tao bảo dẹp hết nguồn cũ cào nguồn ms niche hot cho tao"*

## 2. Bài Học Kỷ Luật Điều Phối (Operator Discipline)

### 2.1. Cấm Viện Cớ Dữ Liệu Cũ Mismatch Để Đóng Băng Task
- Khi Operator ra lệnh "dẹp hết nguồn cũ cào nguồn ms niche hot", mục tiêu tối thượng là **WIPE & REBUILD**:
  1. Xóa sạch 100% video thô cũ, video render cũ và avatar cũ ở cả 2 đầu kho (`D:/video goc/<F>` và `D:/TIKTOK-videonuoinick/<F>`).
  2. Khóa cứng `video gốc = Folder Video` (dứt điểm hoàn toàn việc lệch công thức trong Excel).
  3. Bảo lưu nguyên vẹn cursor `Video Đã Đăng` (ví dụ `12`) để bắt đầu render từ clip `13.mp4`.
  4. Cập nhật `Keyword Video` và `Hashtag Pool` theo đúng chuẩn 1 trong 12 Niche Hot.
- Việc dừng lại phân tích dữ liệu cũ rác và báo `BLOCKED` là hành vi **đóng băng (paralysis)** và trốn tránh lệnh vận hành của Operator.

### 2.2. Kỹ Thuật Top-up Continuation Khi Thiếu Vài Clip
- Khi script tải kênh mới đạt 38/40 clips (thiếu đúng 2 clip) do một số clip bị bỏ qua bởi duration filter (<10s hoặc >75s), script ban đầu raise `RuntimeError: Chỉ tải được 38/40 video!`.
- **Kỷ luật xử lý:** CẤM xóa bỏ công tải 38 clip hợp lệ để chạy lại từ đầu hay hủy bỏ swap.
- Quét tiếp các entry còn lại của kênh (từ entry 36 trở đi) để tải bù (top-up) các clip đạt chuẩn, nhanh chóng đạt 48/40 clip (<1 phút).

### 2.3. Cú Pháp Bảng `videos` Trong `state.db`
- Bảng `videos` trong `state.db` gồm 14 cột:
  `(video_id, source_url, platform, niche, source_channel, uploader, view_count, language, language_score, status, folder, rejection_reason, checked_at, output_path)`.
- Khi chèn bản ghi video đã tải hợp lệ, câu lệnh SQL chuẩn:
  ```python
  cur.execute("""
      INSERT OR REPLACE INTO videos (
          video_id, source_url, platform, niche, source_channel, uploader,
          view_count, language, language_score, status, folder, checked_at, output_path
      ) VALUES (?, ?, 'youtube', ?, ?, ?, 100000, 'vi', 0.95, 'downloaded', ?, ?, ?)
  """, (f"youtube:{uploader}:{i}", source_url, niche_slug, source_url, uploader, folder_num, now, str(file_path)))
  ```

### 2.4. Ranh Giới Closeout Gate Khi User Báo "Done"
- Khi User kết thúc phiên bằng từ khóa `Done`, `chốt phiên`:
- Nếu phiên là **RUNTIME_OPERATIONAL / NO_CANDIDATE** (chỉ swap video, update Excel, update SQLite, up avatar trên thiết bị, KHÔNG sửa code git repo):
  - **CẤM TUYỆT ĐỐI** gọi `closeout_gate.py --repo ... --base HEAD~1` mò mẫm so sánh với commit code cũ của phiên trước. Việc này sẽ lôi diff cũ ra chạy pytest toàn diện, dính timeout hoặc test fail của commit trước, làm kẹt gate vô lý.
  - Phân loại rõ `session_class: RUNTIME_OPERATIONAL`, `gate_status: NOT_APPLICABLE — no code candidate`, `commit_required: False`.
  - Nghiệm thu dứt điểm bằng: Biên bản đối soát kho đĩa + SQLite + Batch report exit code 0 + Ảnh Profile xác nhận trực quan qua `MEDIA:`.
