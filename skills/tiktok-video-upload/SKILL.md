---

name: tiktok-video-upload

description: "Run TikTok video upload farm batches (Tik1/Tik2/TikN): canonical launcher, video-pick thumbnail identity verification, random render pipeline, resume-not-restart, live canary, audit gate."

version: 1.1.0



# Maintenance note


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → Dừng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

# The avatar picker evidence ladder and orphan-MediaStore cleanup recipe live in

# references/avatar-mediastore-picker.md; the COMPAT-AVATAR-011 picker-ordering

# fix (push/index BEFORE opening the picker) + manual profile-verify launch

# gotchas live in references/avatar-picker-ordering.md; batch avatar

# regeneration (workbook `video gốc` mapping, both-roots rule, 4-worker

# parallel pattern) lives in references/avatar-regeneration-batch.md. Tik3

# Tik3 render pipeline (tik3_multi_batch.py flags, never-delete-output pitfall,

# parallel-1, report-per-10) + avatar rule mới (người→động vật→frame sáng, bỏ

# channel avatar) + download 480-folder recipe + incremental download từ

# sources.partial.json ("làm tới đâu down tới đó") + silent-run reporting

# preference live in references/tik3-render-avatar-20260816.md.

# of stuck machines (B1 ATX-kill per retry, ATX restart-after-kill, manual ATX +

# fresh turn, Recents escape COMPAT-RECENTS-ESCAPE-001, manifest mismatch,

# workbook scope, account==workbook-ID matching rule, account_update_required_vi

# popup at core level, automation-core version bump after editable install)

# lives in references/avatar-sweep-recovery-20260815.md. Read these before any

# avatar canary or regeneration sweep.



# CARDINAL RULE (user correction 2026-08-15, "mày biết phân biệt tik1 và tik2 k?"):

# Mỗi máy có 2 nick (Tik1 + Tik2) trên CÙNG device. report.json có field

# `account` — PHẢI so khớp account == workbook ID (Tik1.xlsx/Tik2.xlsx) mới

# biết run đó thuộc nick nào. Khi đếm "đã đăng video" / "máy nào chưa đăng",

# chỉ tính SUCCESS có account == ID của nick đang xét (ví dụ ID Tik2); run

# SUCCESS của nick Tik1 KHÔNG tính cho Tik2.

author: Hermes Agent

license: MIT

platforms: [windows]

metadata:

  hermes:

    tags: [tiktok, upload, farm, video-pick, batch, canary, audit, render]

---
# TikTok Video Upload Farm



Operate the TikTok video upload farm on the kibe PC (machines 1-80). Covers the canonical upload launcher, the video-pick thumbnail identity gate, the random render pipeline, and the resume/canary/audit discipline.



## When to use

- Running an upload batch: `run_tiktok_upload_batch.ps1 -Tik <N> ...`

- Fixing `VIDEO_PICK_TARGET_UNVERIFIED` / `POST_SUBMISSION_UNKNOWN` / `DUPLICATE_MEDIA_BLOCKED` / `POST_NEXT_SELECTOR_EXHAUSTED`

- Resuming a render or upload batch after a crash/reset

- Verifying a picker thumbnail really matches the pushed source video



## User's ground-truth preference: verify by LIVE PROFILE, one-off manual

Hard user correction (\"đánh dấu ngu rồi\") + explicit instruction (\"có hàm verify số video đã đăng mà chạy đi\", \"thao tác chụp này làm 1 lần thôi k cần ghi vào flow script\"): when deciding whether a machine already posted, the ONLY ground truth is the live phone profile — take a screenshot (or use `_count_profile_video_tiles_across_grid` / `_verify_profile_post_increment`) and look. The PC-side ledger (media-fingerprints, post-attempts receipts) can be wrong. Do this verification ONCE, manually, as a decision aid — do NOT bake a screenshot-verify step into the upload flow script. When a fact conflicts with what you assumed (e.g. profile empty despite ledger `verified_success`), the live screen wins; say plainly you were wrong rather than re-deriving a story from the ledger.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.