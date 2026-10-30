---
name: gmail-account-automation
description: "Automation workflows for Gmail accounts on the Taadaa farm: Playwright + GPM Chrome, Singbox proxies, Google 2FA/OAuth, and Excel sync."
---
# Gmail Account Automation (Taadaa Farm)

- `references/admin-disk-full-0gb-and-turn-based-stall-pitfall-20261030.md` — Bẫy đĩa D: cạn 0.00 GB làm tê liệt Admin-PC, tử huyệt kết thúc turn bằng hứa hẹn suông gây đóng băng session & giải pháp WinRT OCR / calibrated fallback tránh bẫy ATX XML nuốt node Tạo tài khoản.
- `references/google-create-account-bounce-back-and-personal-overlay-trap-20261030.md` — Tử huyệt ATX XML nuốt popup menu cá nhân [05_personal] dẫn tới phán đoán sai lầm GOOGLE_CREATE_ACCOUNT_BOUNCE_BACK & giải pháp WinRT OCR / fallback calibrated.
- `references/playwright-gmail-navigation-timeout-and-relogin-challenge.md` — Timeout goto.
- `references/gms-webview-missing-node-ocr-coord-fallback-20261030.md` — Bẫy GMS WebView nuốt node 'Tạo tài khoản' trong UI XML & fallback tọa độ (200, 1450).
- `references/admin-cluster-fresh-device-signin-only-pitfall.md` — Bẫy máy 0 account Admin farm bị ép Sign-in Only WebView (mất nút Tạo tài khoản) & hướng xử lý Intent.
- `references/s7-gmail-result-classification-and-chatgpt-decommission.md` — Dừng reg ChatGPT S7, phân loại runner & bẫy hiểu lầm 'Lỗi script' do WebView HTTP 0/XHR 6.
- `references/s7-gmail-slot-eviction-and-gpm-cleanup-rules.md` — Giải phóng slot S7 & dọn DIE.
- `references/slot-capacity-and-eviction-policy.md` — Trần số acc vs rolling eviction.
- `references/dual-cluster-post-noon-gmail-and-watchdog-architecture.md` — Dual-cluster Reg Gmail & range(1, 75) fix.
- `references/admin-fleet-fresh-device-onboarding-and-manifest-governance.md` — Bẫy máy 0 account bị ép Sign-in Only trên Admin & quy chuẩn manifest owner SSH.
- `references/admin-cluster-gmail-reg-orchestration-and-safety-runbook.md` — Quy trình khởi chạy Reg Gmail cụm Admin (Máy 201-280), workerId 'taadaa-writer-admin-farm', đồng bộ Base64 và chống phantom reporting.
- `references/dual-cluster-gmail-reg-admin-failures-and-recovery-20261030.md` — Tử huyệt đứt gãy code sync SHA256, hỏng XML Excel Admin, và giải pháp màn [05_create] mất nút Tạo tài khoản.
- `references/admin-cluster-gmail-reg-corrupt-sync-and-excel-recovery-20261030.md` — Khôi phục Farm Admin khi file code bị đứt sync và Excel XML bị lỗi (mismatched tag).
- `references/admin-gmail-reg-corruption-and-cooldown-excel-recovery-20261030.md` — Phục hồi Admin Reg Gmail: bẫy code truncate SHA256 lệch, hỏng XML Excel cooldown làm sập PowerShell parser & dispatch EncodedCommand.
- `references/night-reg-gmail-admin-ssh-allowlist-and-pipeline-separation-20261030.md` — Triage nguyên nhân Reg Gmail đêm không chạy Farm Admin: Bẫy SSH allowlist `$env:` & phân tách 2 launcher.
- `references/gpm-api-pagination-and-soak-gate-deadlock.md` — GPM API pagination & Soaking Gate.
- `references/youtube-nurture-ad-handling-and-evidence-timing.md` — YouTube ad skip & timing trap.
- `references/gpm-relogin-taxonomy-and-soak-date-typo-trap.md` — Phân loại 6 lỗi re-login GPM, bẫy soak date Excel, dò pass di chứng wrong_password & xử lý SMS checkpoint.
- `references/dual-provider-session-desync-and-gpm-login-blindspot.md` — Lệch session Antigravity vs Codex làm watchdog bỏ sót acc mất session Google.

## Critical Operational Rules & Concurrency Safety
- **Excel Concurrent Write Pitfall (Race Condition & Corruption)**:
  - Khi chạy 2FA GPM đa luồng, cấm gọi `openpyxl.save()` vào Excel master không có lock. Bắt buộc dùng `single_writer_workbook_update` hoặc rename qua `.tmp.xlsx`.
  - **Giải pháp**: Dùng filelock/single-writer queue hoặc ghi `.json` riêng rồi merge một lần.
- **CẤM Xóa Profile GPM khi Gmail DIE & Quy chuẩn Sheet Gmail_DIE_Archive**:
  - Xem chi tiết tại `references/gmail-die-recovery-and-no-delete-policy.md`. CẤM TUYỆT ĐỐI script tự động xóa profile GPM khi Gmail die (để bảo toàn tài khoản OpenAI/Codex đã ver số). Mọi tài khoản DIE tách riêng sang sheet `Gmail_DIE_Archive` trong `master_gmail_manager.xlsx`.
  - Luôn dùng `wait_until="domcontentloaded"` (cấm `networkidle` gây treo). Khi cần user nhập mã OTP, TUYỆT ĐỐI KHÔNG đóng profile/browser, giữ nguyên trên màn hình.
  - Chỉ ghi log ra file hoặc `sys.stderr`, tránh tràn thông báo Telegram.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
