---
name: vision-evidence-and-gate6-verification
description: "Use when vision 503 fails Gate 6. Fallback Claude CLI."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [gate6, vision, visual-evidence, ocr, claude-worker, fail-closed]
---
# Vision Evidence & Gate 6 Verification SOP

Tài liệu quy trình chuẩn khi thực thi Invariant Soi Mắt & Gate 6 Visual Evidence trên Taadaa Farm.

- Chi tiết SOP đầy đủ: [`references/vision-down-fail-closed-and-claude-cli-fallback-sop.md`](references/vision-down-fail-closed-and-claude-cli-fallback-sop.md)
- Đăng ký Receipt Media Gate & xử lý chặn clarify: [`references/media-gate-receipt-registration-and-clarify-lockout.md`](references/media-gate-receipt-registration-and-clarify-lockout.md)
- Phân bậc Receipt T0/T1/T2/T3 & chống bẫy im lặng Gate 6: [`references/tiered-verifier-and-gate6-incentive-alignment.md`](references/tiered-verifier-and-gate6-incentive-alignment.md)
- Gate cơ học có chỉ dẫn (Action-Forcing Guidance) & Invariant Tiếng Việt có dấu: [`references/vietnamese-diacritics-profile-and-action-forcing-guidance-gates.md`](references/vietnamese-diacritics-profile-and-action-forcing-guidance-gates.md)
- Chống Chụp Mù Launcher & Cuộn Lưới Video Below-the-fold: [`references/pre-capture-focus-guard-and-anti-launcher-hallucination.md`](references/pre-capture-focus-guard-and-anti-launcher-hallucination.md)
- Điều Tra Sự Cố Bị Vượt Mặt Media Gate & Cơ Chế Chặn Ký Receipt Rỗng: [`references/media-gate-bypass-investigation-and-grounding-fix.md`](references/media-gate-bypass-investigation-and-grounding-fix.md)
- SOP Thẩm Định Thị Giác Đa Tầng Cơ Học (Sol -> Agy -> Claude): [`references/tiered-vision-fallback-mechanical-sop.md`](references/tiered-vision-fallback-mechanical-sop.md)
- Phân Tầng Reviewer & Chốt Chặn Cơ Học Chống Vượt Mặt Gate 6 (Verdict APPROVED): [`references/media-gate-bypass-investigation-and-grounding-fix.md`](references/media-gate-bypass-investigation-and-grounding-fix.md)
- Bài Học Thực Chiến Hardening Media Gate & Bắt Buộc Ảnh Chốt Phiên: [`references/closeout-visual-evidence-and-gate-hardening-lessons.md`](references/closeout-visual-evidence-and-gate-hardening-lessons.md)
- Xác Minh Fresh Screencap & Đối Soát Account Switcher: [`references/fresh-screencap-and-account-switcher-verification.md`](references/fresh-screencap-and-account-switcher-verification.md)
- Báo Cáo Điều Tra Bypass by Claim Omission & Chốt Chặn Task Contract Binding: [`references/bypass-by-claim-omission-and-task-contract-binding.md`](references/bypass-by-claim-omission-and-task-contract-binding.md)
- Chặn 2FA/TOTP Khi Switcher & Kỷ Luật Nghiệm Thu Profile: [`references/account-switcher-2fa-totp-interception-and-profile-standardization.md`](references/account-switcher-2fa-totp-interception-and-profile-standardization.md)
- Khôi Phục Session 2FA Ảo & Nạp Bio Bằng AdbKeyboard Broadcast: [`references/transient-2fa-recovery-and-adb-keyboard-utf8-bio-injection.md`](references/transient-2fa-recovery-and-adb-keyboard-utf8-bio-injection.md)
- Kỷ Luật Form Submit & Chống Bẫy Ảnh Chưa Nộp / Reset Rỗng: [`references/browser-form-submit-atomic-verification-and-anti-silent-reset.md`](references/browser-form-submit-atomic-verification-and-anti-silent-reset.md)

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
