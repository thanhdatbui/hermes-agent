---
name: gmail-account-automation
description: "Automation workflows for Gmail accounts on the Taadaa farm: Playwright + GPM Chrome, Singbox proxies, Google 2FA/OAuth, and Excel sync."
---
# Gmail Account Automation (Taadaa Farm)

- `references/playwright-gmail-navigation-timeout-and-relogin-challenge.md` — Timeout goto.
- `references/s7-gmail-result-classification-and-chatgpt-decommission.md` — Dừng reg ChatGPT S7, phân loại runner & bẫy hiểu lầm 'Lỗi script' do WebView HTTP 0/XHR 6.
- `references/s7-gmail-slot-eviction-and-gpm-cleanup-rules.md` — Giải phóng slot S7 & dọn DIE.
- `references/slot-capacity-and-eviction-policy.md` — Trần số acc vs rolling eviction.
- `references/dual-cluster-post-noon-gmail-and-watchdog-architecture.md` — Dual-cluster Reg Gmail & range(1, 75) fix.
- `references/admin-cluster-gmail-reg-corrupt-sync-and-excel-recovery-20261030.md` — Khôi phục Farm Admin khi file code bị đứt sync và Excel XML bị lỗi (mismatched tag).
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
