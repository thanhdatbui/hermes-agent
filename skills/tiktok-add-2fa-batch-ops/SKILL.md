---
name: tiktok-add-2fa-batch-ops
description: "Use when running batch 2FA on TikTok farm. Chạy batch 2FA repo tiktok-add-bao-mat-f2a, preflight, rotate pass, verify sau chạy."
---
# TikTok Add 2FA Batch Ops (repo tiktok-add-bao-mat-f2a)

References:
- `references/sqlite-master-ledger-and-write-through-sync-discipline-20261031.md` — **[MỚI 31/10/2026]** Chuyển đổi dứt điểm đọc Excel sang SQLite DAL `farm_db.py`, kiến trúc Write-Through ghi kép Excel + `farm_master.db`, và kỷ luật chống xin lỗi suông (cơ giới hóa ngay lập tức).
- `references/sqlite-master-migration-and-no-excuse-discipline-20261031.md` — **[MỚI 31/10/2026]** Kỷ luật cấm nhận lỗi suông (chỉ hành động cơ giới hóa), chuyển đổi dứt điểm 100% reading/writing sang DAL SQLite `farm_db.py` (write-through), và sửa lỗi Gate B planner context window + Canary CLI mismatch.
- `references/sqlite-master-dal-otp-and-planner-context-discipline-20261031.md` — **[MỚI 31/10/2026]** Kỷ luật cấm nhận lỗi suông (cơ giới hóa thay thế lời xin lỗi), cấm tuyệt đối đọc openpyxl Excel (100% qua SQLite `farm_db.py`), nạp full context $\le 1500$ dòng cho Gate B Planner Gemini Web và chuẩn cờ Canary CLI.
- `references/night-2fa-ui-ambiguous-next-and-canary-gap-20261031.md` — **[MỚI 31/10/2026]** Fix lỗi `UI_TARGET_AMBIGUOUS:Next:0` đa ngữ, chống lạm dụng `--no-canary` trên adapter thiết bị, và giải trình thang não Gate B fallback từ `gemini-web` sang `sol-worker`.
- `references/ui-target-ambiguous-next-and-unified-patch-pipeline-20261031.md` — **[MỚI 31/10/2026]** Khắc phục lỗi `UI_TARGET_AMBIGUOUS:Next:0` bằng fallback đa ngữ (Tiếp/Tiếp tục/Next/Continue), kỷ luật chạy pipeline lệnh đơn dòng chống dính Coordinator Guard.
- `references/live-test-telegram-spam-prevention-and-dry-run-contract-20261030.md` — **[MỚI 30/10/2026]** Kỷ luật cấm test live watchdog thiếu `--dry-run`, chống bão spam Telegram báo cáo mã thoát 5 vào nhóm nghiệp vụ.
- `references/night-2fa-watchdog-trace-observability-and-no-vichanger-invariants-20261030.md` — **[MỚI 30/10/2026]** Lưu Trace đĩa `D:/Taadaa/reports/night_2fa_trace_{date}.log` cho Watchdog 2FA, bóc tách `failure_breakdown`, cấm tuyệt đối nhắc ViChanger hoặc app Outlook S7 (100% Graph API & GPM PC).
- `references/night-2fa-forwarded-report-triage-and-feed-interlock-20261030.md` — Quy trình giải mã báo cáo 2FA forward, đối soát luỹ kế O(1) và kỷ luật cấm xâm lấn Ca Nuôi.
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
- `scripts/flush_dpapi_journal_to_workbook.py` — **[MỚI 21/09/2026]** Script tự động flush các Secret Key 2FA từ DPAPI journal vào Cột E file Excel `taikhoan_dat_v2_updated .xlsx`, đối chiếu readback và cập nhật state WRITTEN.
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

## Đổi Email liên kết TikTok sang Hotmail mới (Bỏ qua OTP mail cũ & chống dính recovery)
- **Bản chất phát hiện TikTok UI (18/09/2026):** Tài khoản TikTok no-phone đã bật 2FA TOTP và đăng nhập lâu ngày trên thiết bị: khi vào `Hồ sơ -> Cài đặt và quyền riêng tư -> Tài khoản -> Thông tin tài khoản -> Email -> Thay đổi email`, TikTok **MỞ THẲNG MÀN HÌNH "NHẬP EMAIL MỚI"** mà **hoàn toàn KHÔNG bắt OTP từ mail cũ**.
- **Quy trình đổi email tự động:**
  1. Mua Hotmail mới qua API shop: `python D:/Taadaa/tools/buy_hotmail.py --buy 1 --target-file <path>` lấy `email|pass|refresh_token|client_id`.
  2. Vào TikTok `Thay đổi email` -> Gõ Hotmail mới -> Bấm "Tiếp tục".
  3. Polling mã OTP 6 số từ Microsoft Graph API (`https://graph.microsoft.com/v1.0/me/messages`) qua `refresh_token` & `client_id`.
  4. Nhập 6 số OTP vào TikTok để hoàn tất liên kết email mới.
  5. Cập nhật Hotmail mới vào Cột F và Pass Hotmail vào Cột G file Excel `taikhoan_dat_v2_updated .xlsx`.
- **Quy tắc bảo mật bàn giao:** Hotmail bán kèm nick CẤM add email khôi phục cá nhân. Luồng chuẩn: Đổi pass Chrome -> Bấm Sign out everywhere -> Lưu Cột G Excel -> Đăng nhập App Outlook bằng pass mới.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
