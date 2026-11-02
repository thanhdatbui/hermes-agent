---
name: tiktok-farm-avatar-operations
description: Use when running avatar-only jobs on TikTok farm.
---
# TikTok Farm Avatar Operations

- Evaluation Repo Cắt Ảnh Hiện Đại (`autocrop`/YuNet vs `YOLOv8`) & Bẫy Quy Chụp Script Cũ (2026-11-02): [references/modern-crop-repo-evaluation-vs-legacy-haar-cascade-trap-20261102.md](references/modern-crop-repo-evaluation-vs-legacy-haar-cascade-trap-20261102.md). Bắt buộc `session_search` khi User hỏi repo cũ; phân loại ngách: Người dùng `autocrop`/YuNet, Động vật dùng `YOLOv8`.
- Auto Video Avatar Extraction (YOLOv8 + BBox Sharpness) & Anti-Hardcoded Crop Traps (2026-11-02): [references/auto-video-avatar-extraction-yolov8-and-anti-hardcoded-crop-trap-20261102.md](references/auto-video-avatar-extraction-yolov8-and-anti-hardcoded-crop-trap-20261102.md). Cấm crop tọa độ tĩnh; dùng YOLOv8 (person/dog/cat), đo độ nét trên bbox, dynamic padding chống chém cụt mặt.
- Crop timeout & screen sleep: [references/avatar-crop-open-timeout-and-screen-sleep-trap-20261020.md](references/avatar-crop-open-timeout-and-screen-sleep-trap-20261020.md).
- Avatar Execution & Proof Mandate (2026-11-02): [references/avatar-execution-and-proof-mandate.md](references/avatar-execution-and-proof-mandate.md). Chuẩn hoá kênh bắt buộc cả 2 khâu: Ghim top LIFO VÀ chạy engine đổi Avatar thật (`run_upload_avatar.py`); cấm chỉ ghim video rồi báo xong bỏ quên avatar khiến User hỏi "Chuẩn hoá ava đâu?".
- Full-Pipeline Niche Source Swap & Follow-up Avatar Upload Invariant (2026-11-02): [references/source-swap-mandatory-avatar-upload-and-gate6-20261102.md](references/source-swap-mandatory-avatar-upload-and-gate6-20261102.md). Đổi nguồn video bắt buộc chạy trọn gói upload avatar mới lên app ngay trong phiên qua `run_avatar_m1.py <M> <Tik>`, cấm chỉ đổi file trên đĩa để User phải hỏi "Đổi ava chưa?".
- Right-side avatar layout trap: [references/tiktok-profile-right-side-avatar-layout-trap.md](references/tiktok-profile-right-side-avatar-layout-trap.md). Inspect header (y: 200..600) before crop.
- Approved-avatar upload & evidence: [references/approved-avatar-immediate-upload-and-evidence.md](references/approved-avatar-immediate-upload-and-evidence.md).
- Double-lock & cross-host: [references/avatar-lock-verification-and-cross-host-upload.md](references/avatar-lock-verification-and-cross-host-upload.md). Khóa `.manual_avatar_locked` 3 kho, `Avatar = OK`, SSH máy >= 200.
- New correction-loop checklist: [avatar-change-correction-loop-20261020.md](references/avatar-change-correction-loop-20261020.md).
- Account-bound evidence and runner contradiction: [references/account-bound-avatar-evidence-and-runner-contradiction.md](references/account-bound-avatar-evidence-and-runner-contradiction.md). Require exact-account visual proof; runner success/workbook updates alone are intermediate evidence.
- Avatar Text-Banner Crop: [references/avatar-text-banner-crop-triage-and-non-empty-coordinator-response-20261016.md](references/avatar-text-banner-crop-triage-and-non-empty-coordinator-response-20261016.md)

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
