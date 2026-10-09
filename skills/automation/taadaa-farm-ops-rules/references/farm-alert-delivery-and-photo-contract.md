# Quy Chuẩn Gửi Farm Alert & Xử Lý Ảnh Hiện Trường (Farm Alert & Photo Delivery Contract)

## 1. Thiết Kế Banner Đỏ Số Máy Trên Ảnh (BẮT BUỘC GIỮ 100%)
- Mọi alert máy dừng phiên BẮT BUỘC phải có ảnh hiện trường chụp từ thiết bị qua ADB/ATX.
- Thiết kế chuẩn do User phê duyệt:
  - Thanh banner đỏ trên đỉnh ảnh: `draw.rectangle([(0, 0), (w, banner_h)], fill=(220, 20, 60))` với `banner_h = int(h * 0.05)`.
  - Chữ trắng in hoa to rõ: `[MAY {machine}] - HH:MM:SS DD/MM` (font Arial, căn giữa banner).
  - File ảnh được lưu tại: `D:\Taadaa\runtime\kibe\artifacts\alert_machine_{machine}.png`.
  - Tuyệt đối không thay đổi style hoặc bỏ banner đỏ này.

## 2. Giới Hạn Kỹ Thuật Telegram API & Cắt Ngắn Caption Ảnh (1,024 Ký Tự)
- **Cạm bẫy (Pitfall):** Telegram API áp dụng giới hạn cứng khác nhau cho tin nhắn:
  - `sendMessage` (chữ thuần): tối đa **4,096 ký tự**.
  - `sendPhoto` (ảnh kèm caption): tối đa **1,024 ký tự**.
- **Hậu quả khi vi phạm:** Khi template alert 5 bước recovery + chuỗi symptom lỗi dài vượt quá 1,024 ký tự, Telegram trả về HTTP `400 Bad Request: MEDIA_CAPTION_TOO_LONG` và từ chối gửi ảnh. Nếu code fallback gửi text-only thì user sẽ nhận alert bị mất ảnh.
- **Quy tắc xử lý:**
  1. Trong `_send_telegram_photo`, caption cho ảnh BẮT BUỘC được clamp $\le 1000$ ký tự (cắt an toàn và đóng thẻ HTML nếu cần).
  2. Không bao giờ để lỗi caption dài làm rớt ảnh hiện trường.
  3. Toàn bộ nội dung chi tiết 5 bước / lệnh canary dài sẽ được gửi nối tiếp bằng tin nhắn text ngay sau ảnh nếu cần.

## 3. Cơ Chế Chống Nuốt Lỗi Mạng & Tránh Khóa Vĩnh Viễn Claim File
- **Vấn đề:**
  - `send_farm_machine_alert` nếu luôn `return True` khi `_send_telegram_photo` / `_send_telegram_text` thất bại (do rớt mạng, DNS `getaddrinfo failed`, timeout) sẽ làm caller tưởng đã gửi thành công.
  - Caller (`_claim_machine_alert_once` trong `multi_machine_feed_session.py`) tạo file `machine_{N}.claimed` trước khi gửi. Nếu alert fail nhưng file claim vẫn bị giữ lại trên đĩa, các tick quét sau sẽ thấy file claim và bỏ qua vĩnh viễn $\rightarrow$ Farm Alert bị câm hoàn toàn suốt cả ca/phiên.
- **Quy tắc sửa đổi:**
  1. `send_farm_machine_alert` BẮT BUỘC trả về `False` nếu cả gửi ảnh và gửi text đều thất bại.
  2. Trong `_claim_machine_alert_once`: khi `delivered is not True`, BẮT BUỘC xóa file claim (`claimed.unlink(missing_ok=True)`) để cho phép tick kế tiếp thử lại khi mạng Telegram hồi phục. Chỉ ghi `status=delivered` khi gửi thực sự thành công.

## 4. Bắn Đúng Script Kèm Ghi Chú & Metadata Chính Xác
- Mỗi script khi bắn alert phải mapping đúng metadata trong `_SCRIPT_METADATA` (`automation-core/alerts.py`):
  - `feed`: Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`) -> Flow: `feed_swipe_smoke.py`, Log: `summary.txt`, Canary: `run-feed-session.ps1`
  - `avatar`: Upload Avatar (`Tiktok-video`) -> Flow: `run_post.py`, Canary: `run_tiktok_upload_batch.ps1 -AvatarOnly`
  - `upload`: Đăng Video (`Tiktok-video`) -> Flow: `run_post.py`, Log: `D:/CodexRuntime/tiktok-video/runs`, Canary: `run_tiktok_upload_batch.ps1`
  - `follow`: Follow TikTok (`tiktok-follow`) -> Flow: `follow_engine.py`, Canary: `run-follow.ps1`
  - `2fa`: Bật 2FA TikTok (`tiktok-add-bao-mat-f2a`) -> Flow: `run_batch_live_2fa.py`, Canary: `run_batch_live_2fa.py --live`
  - `reg_tiktok`: Đăng Ký TikTok (`Tiktok_Reg`) -> Flow: `social_reg_v1.py`, Canary: `social_reg_v1.py {m} --ss`
  - `reg_gmail`: Đăng Ký Gmail (`register gmail`) -> Flow: `run_all.ps1`, Canary: `run_all.ps1 -Machines {m}`
  - `clear_cache`: Dọn Dẹp Cache TikTok (`clear-tiktok-cache`) -> Flow: `clear-tiktok-cache.py`, Canary: `clear-tiktok-cache.py --machine {m}`
  - `night_chain`: Chuỗi Ban Đêm Reg & 2FA (`night-chain-reg-pipeline`) -> Flow: `run_night_chain_pipeline.py`
  - `checklive`: Check Live Kho Acc (`daily-manual-stock-checklive`) -> Flow: `daily_manual_stock_checklive.py`
- Lỗi cấp script/pipeline không gắn với máy lẻ dùng `send_farm_script_alert` gửi về `-5373649734` kèm đúng file flow, log path và lệnh chạy lại.
