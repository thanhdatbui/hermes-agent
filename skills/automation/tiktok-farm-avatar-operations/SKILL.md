---
name: tiktok-farm-avatar-operations
description: Use when running avatar-only jobs on TikTok farm.
---
# TikTok Farm Avatar Operations

- Auto Video Avatar Extraction (YOLOv8 + BBox Sharpness) & Anti-Hardcoded Crop Traps (2026-11-02): [references/auto-video-avatar-extraction-yolov8-and-anti-hardcoded-crop-trap-20261102.md](references/auto-video-avatar-extraction-yolov8-and-anti-hardcoded-crop-trap-20261102.md). Cấm crop tọa độ tĩnh; dùng YOLOv8 (person/dog/cat), đo độ nét trên bbox, dynamic padding chống chém cụt mặt.
- Crop timeout & screen sleep: [references/avatar-crop-open-timeout-and-screen-sleep-trap-20261020.md](references/avatar-crop-open-timeout-and-screen-sleep-trap-20261020.md).
- Right-side avatar layout trap: [references/tiktok-profile-right-side-avatar-layout-trap.md](references/tiktok-profile-right-side-avatar-layout-trap.md). Inspect header (y: 200..600) before crop.
- Approved-avatar upload & evidence: [references/approved-avatar-immediate-upload-and-evidence.md](references/approved-avatar-immediate-upload-and-evidence.md).
- Double-lock & cross-host: [references/avatar-lock-verification-and-cross-host-upload.md](references/avatar-lock-verification-and-cross-host-upload.md). Khóa `.manual_avatar_locked` 3 kho, `Avatar = OK`, SSH máy >= 200.
- New correction-loop checklist: [avatar-change-correction-loop-20261020.md](references/avatar-change-correction-loop-20261020.md).
- Account-bound evidence and runner contradiction: [references/account-bound-avatar-evidence-and-runner-contradiction.md](references/account-bound-avatar-evidence-and-runner-contradiction.md). Require exact-account visual proof; runner success/workbook updates alone are intermediate evidence.
- Avatar Text-Banner Crop: [references/avatar-text-banner-crop-triage-and-non-empty-coordinator-response-20261016.md](references/avatar-text-banner-crop-triage-and-non-empty-coordinator-response-20261016.md)
- Cartoon & Mascot: [references/non-human-cartoon-mascot-avatar-and-empty-turn-prevention-20261016.md](references/non-human-cartoon-mascot-avatar-and-empty-turn-prevention-20261016.md) & [references/cartoon-mascot-avatar-extraction-and-mismatched-source-triage-20261016.md](references/cartoon-mascot-avatar-extraction-and-mismatched-source-triage-20261016.md)
- Haar Cascade False-Positive & Pre-Send Candidate Vision Gate (2026-10-17): [references/haar-cascade-false-positive-and-pre-send-candidate-vision-gate-20261017.md](references/haar-cascade-false-positive-and-pre-send-candidate-vision-gate-20261017.md) & [references/haar-cascade-false-positive-face-and-multi-frame-avatar-verification-20261016.md](references/haar-cascade-false-positive-face-and-multi-frame-avatar-verification-20261016.md)

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
