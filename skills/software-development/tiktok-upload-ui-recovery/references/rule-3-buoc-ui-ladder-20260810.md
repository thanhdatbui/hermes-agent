# RULE 3 BƯỚC FIX LỖI UI — user-chốt 2026-08-10

User chốt thiết kế retry budget cho MỌI lỗi UI/vận hành trên farm TikTok (phủ all
repo consumer + `automation-core` docs/ui-compatibility-contract.md). Không thay đổi
nếu user chưa yêu cầu.

## Cấu trúc ladder

- **B1:** ATX-kill (uiautomator recovery, rẻ/nhanh — ưu tiên)
- **B2:** force-stop + relaunch app — **TỐI ĐA 1 lần**
- **B3:** reboot máy (soft reboot) — **TỐI ĐA 1 lần**

## Budget (điểm mấu chốt user sửa)

> "Chỉ đc relaunch + reboot lần đầu, các lần sau chỉ đc atx kill + click coordinate.
> Chứ lần nào cx relaunch reboot t nghĩ nó reboot hoài luôn" — user 2026-08-10

- Budget tính **theo máy trong 1 turn chạy**: 1 relaunch + 1 reboot/máy, KHÔNG reset
  giữa các run recovery (chạy recovery 5 lần ≠ 5 reboot).
- Lỗi lặp lại sau đó: chỉ ATX-kill → coordinate fallback có evidence → fail = MANUAL_REVIEW.
- Lỗi CÙNG CHỖ sau đủ budget = thất bại thật, giữ handoff lock + evidence.
- Lỗi KHÁC CHỖ (state/signature khác) được chạy lại chuỗi 3 bước nhưng VẪN nằm trong
  budget tổng 1 relaunch + 1 reboot của máy (chống vòng lặp xoay vòng giữa các state).
- Handler đặc thù fail vì UI/dump → route vào ladder, KHÔNG dừng sớm MANUAL_REVIEW.

## Lý do (bản chất)

- Reboot chỉ cứu trạng thái máy xấu (uiautomator treo, app treo). Đã reboot 1 lần mà
  vẫn lỗi → vấn đề là logic/verifier/UI build, reboot thêm vô ích, chỉ tốn 5-10 phút/máy.
- ATX-kill + coordinate rẻ, không đụng máy, đủ xử lý lỗi UI tạm thời lặp lại.

## Pitfall ghi nhận từ batch 20260810

1. **Launcher silently tắt ladder:** `run_tiktok_upload_batch.ps1` bản cũ (trước commit
   `14d62ec`) không truyền `--allow-device-reboot-recovery` → state machine log:
   `Soft reboot recovery disabled by config` + `allow_device_reboot_recovery=False ->
   bỏ qua coordinate fallback` → m35 chạy 2 tầng rồi MANUAL_REVIEW. Fix: normal live
   batch PHẢI truyền `--allow-device-reboot-recovery` mặc định (đã commit `14d62ec`).
2. **Recovery direct dùng template config:** KHÔNG đòi `config-machine-N.yaml`. Launcher
   dùng `config-machine-62.yaml` rồi `--machine N` bind workbook row
   (`Target binding: workbook row machine=N`). Lần đầu tôi báo sai `BLOCKED_CONFIG_MISSING`
   vì đòi file sai — đây là blocker giả, máy vẫn có mapping.
3. **Batch không tự recovery:** batch chạy 1 lượt; worker fail → giữ handoff lock + report,
   không retry. Recovery phải dispatch riêng worker với
   `--recovery-mode --allow-device-reboot-recovery`.
4. **Splash-stuck:** máy kẹt splash đen (logo TikTok, visual gate `white=0.000 dark=1.000`)
   sau ladder → coordinate fail-closed "không có evidence target" là ĐÚNG (cấm tap mù).
   Step bổ sung (đang implement): wait feed hết → close recent apps → launch lại TikTok
   (không tính là relaunch ladder) → wait lại.