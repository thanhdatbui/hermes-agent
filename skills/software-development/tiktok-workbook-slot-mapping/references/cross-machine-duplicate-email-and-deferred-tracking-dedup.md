# Root Cause & Pattern: Cross-Machine Duplicate Email & Deferred Dedup Overwrite

## Bối cảnh & Hiện tượng (Sự cố 2026-09-08 & 2026-08-26)
- **Hiện tượng:** Tài khoản `miumiu67971` (mail `karistinelso@hotmail.com`) xuất hiện trên cả Máy 03 và Máy 05. Trên Excel (`taikhoan_dat_v2_updated .xlsx`) chỉ ghi nhận Máy 05, bỏ trống Máy 03 khiến Máy 03 bị app TikTok kịch trần 8 acc gây crash chuỗi reg ban đêm.
- **Câu hỏi của User:** "Lí do đăng nhập nhầm là gì" và "Lí do ghi nhầm excel. Wtf ghi = tool mà nhầm đc", "Lí do tại sao bốc trùng mail".

---

## Cơ chế phát sinh lỗi (3 khâu liên hoàn)

1. **Khâu 1: Nạp trùng email vào kho nguồn (`gmail_clean_v2.xlsx`)**
   - Khi chia dải mail cho 80 máy, cùng 1 email bị gán cho 2 máy khác nhau (STT 03 và STT 05).

2. **Khâu 2: Race condition giữa Deferred Write và ca chạy lại (Recovery)**
   - **07:51 AM:** Máy 03 chạy trước, bốc mail khác và bị timeout 5 phút. Trong khi đó, Máy 05 chạy song song bốc `karistinelso@hotmail.com`, đăng ký thành công nick `miumiu67971` lúc 08:02 AM.
   - Vì chạy chế độ hoãn ghi (`--defer-tracking-write`), kết quả Máy 05 chỉ lưu ra file JSON `tracking_result_stt5_...json`, **chưa ghi ngay vào Excel**.
   - **09:48 AM:** Máy 03 chạy ca recovery. Script đọc Excel thấy `karistinelso@hotmail.com` vẫn chưa có TikTok ID (do chưa merge) nên bốc mail này điền vào TikTok.
   - TikTok báo mail đã đăng ký -> Script tự động chuyển sang luồng **Đăng nhập (Login)** qua OTP Graph API -> Đăng nhập luôn nick `miumiu67971` vào Máy 03 lúc 09:56 AM!
   - Kết quả: Nick nằm trên cả 2 máy, tạo ra 2 file JSON kết quả cho cùng 1 email.

3. **Khâu 3: Khử trùng lặp trong Tool Merge (`apply_deferred_tracking_results.py`)**
   - Khi chạy merge các file JSON deferred vào Excel, tool khử trùng lặp theo email bằng logic:
     ```python
     if em not in dedup or item["written_at"] > dedup[em]["written_at"]:
         dedup[em] = item
     ```
   - File kết quả của Máy 05 sinh sau (hoặc đợt sau) có `written_at` lớn hơn file của Máy 03 -> Tool chọn ghi Máy 05 vào Row 40 và gạt bỏ file của Máy 03.
   - Hệ quả: Excel ghi nhận Máy 05, để trống Máy 03 dù Máy 03 thực tế đang lưu nick đó.

---

## Kỷ luật vận hành & Xử lý khi phát hiện
1. **Kiểm tra chéo thiết bị thực tế:** Khi nghi ngờ lệch mapping, bắt buộc mở app TikTok trên cả 2 máy và dump XML Account Switcher (node `id/lkp` hoặc `content-desc`).
2. **Nguyên tắc an toàn:**
   - Nếu máy trên Excel không chứa acc: sửa lại Excel ghi đúng máy đang chứa.
   - Nếu **CẢ 2 MÁY CÙNG CHỨA ACC**: BẮT BUỘC dừng lại và báo cáo User chỉ đạo (đăng xuất khỏi máy bị đăng nhập nhầm để giải phóng slot).
3. **Phòng ngừa:**
   - Kho mail `gmail_clean_v2.xlsx`: Tuyệt đối khử trùng lặp email khi nạp.
   - Preflight: Đọc cứng sheet `'Tài Khoản'`, kiểm tra `registered_mailboxes` bao gồm cả các file deferred chưa merge.
