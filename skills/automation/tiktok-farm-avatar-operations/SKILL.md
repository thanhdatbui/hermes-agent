---
name: tiktok-farm-avatar-operations
description: Use when running avatar-only jobs on TikTok farm.
---
# TikTok Farm Avatar Operations

- Faceless Stationery & Studygram Avatar Extraction & Guard Discipline (2026-11-04): [references/faceless-stationery-avatar-extraction-and-terminal-guard-discipline-20261104.md](references/faceless-stationery-avatar-extraction-and-terminal-guard-discipline-20261104.md). Ngách văn phòng phẩm/sổ còng/bàn học faceless cấm dùng haar cascade tìm mặt (false positive sticker/lưới caro); tiêu chuẩn 4 PA góc bàn học/bìa sổ/take notes sạch chữ 100% (WinRT OCR == ''); kỷ luật read-only `python -c` và cấm gửi MEDIA khống khi chưa render canvas thật.
- Native Vision Avatar Candidate Extraction & Anti-Browser Hallucination (2026-11-03): [references/native-vision-avatar-candidate-extraction-and-anti-browser-hallucination-20261103.md](references/native-vision-avatar-candidate-extraction-and-anti-browser-hallucination-20261103.md). Cấm mở browser_vision đối phó gây ảo giác; dùng Canny bottom noise (< 10.0) lọc sạch viền phụ đề/caption; cấm phát ngôn hứa hẹn suông kích hoạt Tool-Use Enforcement.
- Evaluation Repo Cắt Ảnh Hiện Đại (`autocrop`/YuNet vs `YOLOv8`) & Bẫy Quy Chụp Script Cũ (2026-11-02): [references/modern-crop-repo-evaluation-vs-legacy-haar-cascade-trap-20261102.md](references/modern-crop-repo-evaluation-vs-legacy-haar-cascade-trap-20261102.md). Bắt buộc `session_search` khi User hỏi repo cũ; phân loại ngách: Người dùng `autocrop`/YuNet, Động vật dùng `YOLOv8`.
- Auto Video Avatar Extraction (YOLOv8 + BBox Sharpness) & Anti-Hardcoded Crop Traps (2026-11-02): [references/auto-video-avatar-extraction-yolov8-and-anti-hardcoded-crop-trap-20261102.md](references/auto-video-avatar-extraction-yolov8-and-anti-hardcoded-crop-trap-20261102.md). Cấm crop tọa độ tĩnh; dùng YOLOv8 (person/dog/cat), đo độ nét trên bbox, dynamic padding chống chém cụt mặt.
- Crop timeout & screen sleep: [references/avatar-crop-open-timeout-and-screen-sleep-trap-20261020.md](references/avatar-crop-open-timeout-and-screen-sleep-trap-20261020.md).
- Avatar Execution & Proof Mandate (2026-11-02): [references/avatar-execution-and-proof-mandate.md](references/avatar-execution-and-proof-mandate.md). Chuẩn hoá kênh bắt buộc cả 2 khâu: Ghim top LIFO VÀ chạy engine đổi Avatar thật (`run_upload_avatar.py`); cấm chỉ ghim video rồi báo xong bỏ quên avatar khiến User hỏi "Chuẩn hoá ava đâu?".
- Full-Pipeline Niche Source Swap & Follow-up Avatar Upload Invariant (2026-11-02): [references/source-swap-mandatory-avatar-upload-and-gate6-20261102.md](references/source-swap-mandatory-avatar-upload-and-gate6-20261102.md). Đổi nguồn video bắt buộc chạy trọn gói upload avatar mới lên app ngay trong phiên qua `run_avatar_m1.py <M> <Tik>`, cấm chỉ đổi file trên đĩa để User phải hỏi "Đổi ava chưa?".

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
