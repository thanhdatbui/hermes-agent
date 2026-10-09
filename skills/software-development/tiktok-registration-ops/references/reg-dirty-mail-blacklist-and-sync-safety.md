# Quy Tắc Chống Sót Dữ Liệu Reg TikTok & Blacklist Email Đã Dùng

## 1. CĂN NGUYÊN LỖI EMAIL ĐÃ CÓ TIKTOK ([07] ALREADY REGISTERED)
- **Bản chất**: Bên bán Hotmail không bao giờ bán mail đã có TikTok. Khi TikTok báo email đã có tài khoản (hiện password hoặc màn hình OTP verification `registered`/`registered_otp`), nguyên nhân **100% do Farm ghi nhận sót dữ liệu** trong các đợt reg trước (do file lock OneDrive `dwShareMode=0`, crash giữa chừng, hoặc chưa sync vào sổ cái `taikhoan_dat_v2_updated .xlsx`), dẫn đến `_detect_clean.py` ngộ nhận mail là "sạch" và bốc cấp lại.
- **Hành động đối soát bắt buộc khi gặp [07]**:
  1. KHÔNG được phán mail rác hay đổ lỗi nhà cung cấp.
  2. Chụp ảnh switcher dropdown trên máy và OCR (`winrt_ocr.py`).
  3. Quét ngược run artifacts gần nhất (`D:/Taadaa/runtime/admin/artifacts/runs/social-batch-all/*/tracking_result_*.json`).
  4. Xác định username thực tế (ví dụ: máy 249 nick `@ortunvvjqoi` reg ngày 16/09 từ mail `ortunoherston37@hotmail.com`).
  5. Nạp bù ngay vào sổ cái `taikhoan_dat_v2_updated .xlsx`, file Tik tương ứng (`Tik4.xlsx`), và đồng bộ sang `taikhoan_run_safe.xlsx`.

## 2. KIẾN TRÚC BLACKLIST EMAIL BỀN VỮNG (REGISTERED_EMAILS_BLACKLIST.JSON)
- **Tệp lưu trữ**: `D:/Taadaa/Tiktok_Reg/data/registered_emails_blacklist.json` và `runtime/admin/artifacts/`.
- **Preflight Check (`tiktok_target_eligibility.py` & `_detect_clean.py`)**:
  Hàm `load_registered_mailboxes()` nạp đồng thời 3 nguồn:
  * Toàn bộ email trong sổ cái `taikhoan_dat_v2_updated .xlsx`.
  * Danh sách email trong `registered_emails_blacklist.json`.
  * Các `tracking_result_*.json` thành công trong 15 run folders gần nhất.
- **Runtime Guard (`social_reg_v1.py`)**:
  Khi `fill_email_and_next` gặp phản hồi `registered` hoặc `registered_otp`:
  * Lập tức gọi `record_registered_email_blacklist(email)` để append ngay vào `registered_emails_blacklist.json`.
  * Chặn vĩnh viễn không để bất kỳ máy nào khác trong farm bốc lại email này.

## 3. LỖI "ĐỦ 8 ACC (LỆCH EXCEL)" DO TRÀN MÀN HÌNH SWITCHER
- **Nguyên nhân**: Khi máy đã có 7 acc, danh sách tài khoản chiếm trọn chiều cao màn hình khiến nút *"Thêm tài khoản"* bị đẩy xuống dưới đáy bottom sheet. Hàm kiểm tra cũ không cuộn màn hình và đếm gộp cả layout container rỗng (`lli`), dẫn đến ngộ nhận `_acc_count >= 8` và văng lỗi sai `MACHINE_FULL_8_ACCOUNTS`.
- **Khắc phục chuẩn**:
  * Thêm `swipe(device_id, 540, 1500, 540, 800, 400)` trong `tap_add_account` để cuộn kéo nút lên trước khi kiểm tra.
  * Bộ đếm `_acc_count` chỉ đếm unique text username, loại trừ nhãn điều hướng và container rỗng.

## 4. QUY TRÌNH ĐỒNG BỘ DỮ LIỆU ĐA TẦNG (`ensure_row_accounts.py`)
- Cột Serial trong tracking là cột 10 (chú ý `deferred_tracking_writer.py` kiểm tra cột 10, tránh nhầm cột 11).
- Tự động chạy tuần tự `sync-tik-workbooks.py` (đồng bộ `Tik1..Tik8.xlsx`) và `sync-safe-workbook.py` (đồng bộ `taikhoan_run_safe.xlsx`) với token `TAADAA_ALLOW_OVERWRITE_TOKEN`.
- Trong `apply_results`, khi gặp UID đã tồn tại mà thuộc về cùng máy `m`, xác nhận `VERIFIED` và tăng `applied_count`, không reject nhầm khi runner đã auto-sync trước.

## 5. KỶ LUẬT GIAO TIẾP COORDINATOR - CHỐNG CHẠY NGẦM GÂY "TREO" PHIÊN
- **Hiện tượng**: Coordinator chạy chuỗi tool calls dài liên tục (ví dụ 132 calls trong 52 phút) mà không gửi text về Telegram, làm context phình to (280k tokens) và user tưởng hệ thống bị treo.
- **Kỷ luật bắt buộc**:
  * Tối đa sau 3-5 tool calls hoặc sau khi dispatch worker / background process, BẮT BUỘC nhả text tóm tắt tiến độ về Telegram.
  * Tuyệt đối không ôm việc chạy ngầm quá 2 phút trong im lặng.
