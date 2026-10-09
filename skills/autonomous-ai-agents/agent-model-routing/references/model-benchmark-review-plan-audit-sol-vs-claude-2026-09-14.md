# Benchmark Model Review & Plan Audit: ChatGPT Web 5.6 Sol vs Claude CLI (2026-09-14)

## 1. Bản chất phân định: Solver vs Plan Auditor
Khi benchmark model cho vai trò Reviewer / Plan Auditor:
- **CẤM NHẦM LẪN với Solver**: Cho model log/bug rồi bảo tìm root cause và viết code sửa là test năng lực **Troubleshooting / Engineering Solver**, KHÔNG PHẢI test năng lực **Gác cổng Thẩm định Kế hoạch (Plan Auditor)**.
- **Bài test chuẩn Plan Audit**: Đưa bản Implementation Plan do Worker subagent nộp (có gài bẫy Invariants: O(N) scan, adb tap mù, anchor monolith c!=1, over-engineering/scope creep, trộn code-surgery với batch 40 máy). Yêu cầu dòng đầu: `VERDICT: APPROVED` hoặc `VERDICT: REJECT`.

## 2. Kết quả đối đầu chéo cánh (Cross-evaluation)

### Vòng 1: Engineering Troubleshooting (Log + Code Bug)
- **Bài 1 (PR #482 Audit - Sol ra đề)**: Bẫy `pm clear`, `os.walk`, lock giả trong method.
  - Claude CLI: 62/100 (Rớt - mắc bẫy `pm clear` TikTok nuôi vì nhìn theo góc nhìn app dev thông thường).
  - Sol: 88/100 (Pass Senior - bảo vệ TikTok session, nhận diện 20x login pressure gây chết nick).
- **Bài 2 (15 Acc Ban - Claude CLI ra đề)**: Bẫy Sing-box proxy vs Session cross-contamination do device rotation.
  - Sol: 75/100 (Pass - bác bỏ proxy leak, nhưng thiếu pattern sequential device queue).
  - Claude CLI: 91/100 (Pass+ - bắt smoking gun nhanh, action plan thực dụng với awk/grep và 1-line assert).

### Vòng 2: Plan Auditor / Review Gate (Thẩm định Implementation Plan)
- Đề bài: Worker nộp plan fix kẹt captcha máy 43, gài 4 bẫy (quét đĩa 80 máy, tap tọa độ mù 540 960, vẽ 5 class factory + 250 dòng mock test, anchor monolith c!=1, batch 40 máy).
- **ChatGPT Web 5.6 Sol (Chấm bởi Claude CLI): 91/100 (Distinction)**
  - Bắt trọn vẹn 4/4 bẫy, phát hiện dependency class chưa tồn tại.
  - Tư duy kiến trúc vĩ mô, chia 4 phase bài bản (Inspect bounded -> Minimal surgery -> Focused test -> Canary máy 43).
- **Claude CLI (Chấm bởi Sol): 96/100 (Top-tier Lead Gate Auditor)**
  - Thẳng tay bác bỏ `VERDICT: REJECT`, gắn mã [BF-1]..[BF-6].
  - Bắt bẻ cực gắt Scope Creep, cấm tuyệt đối vẽ class/factory thừa.
  - Remediation cực kỳ cụ thể và executable: chỉ định lệnh grep -n, pytest focused test <30s, yêu cầu anchor >=5 dòng context.

## 3. Khuyến nghị phân vai thực tế
- **Claude CLI**: Đóng vai **Review Gate / Chốt chặn Pre-dispatch & Pre-merge**. Soi Patch Contract, siết kỷ luật Scope Lock, kiểm tra anchor uniqueness c==1 và bắt bẻ over-engineering.
- **ChatGPT Web 5.6 Sol (OmniRoute :20129)**: Đóng vai **Architectural Reviewer & Plan Consultant** cho các ca quy hoạch lớn, state machine phức tạp, concurrency tranh chấp tài nguyên và bảo vệ Farm Invariants.

## 4. Quota ChatGPT-Web (`cgpt-web`) trên OmniRoute (:20129)
- Chạy bằng session token web (`__Secure-next-auth.session-token`), hoàn toàn độc lập với quota Codex CLI (vốn hay bị 503 ~30d).
- Giới hạn: Sliding window 30-50 tin nhắn thinking sâu/3 giờ per Plus account.
- OmniRoute quản lý pool 5+ accounts active (`voha...`, `ngongan...`, `buitrang...`, `lamhien...`, `luuhuong...`) với cơ chế auto-fallback khi gặp 429, giúp mở rộng dung lượng lên 150-200 lượt thinking/buổi mà không nghẽn.
