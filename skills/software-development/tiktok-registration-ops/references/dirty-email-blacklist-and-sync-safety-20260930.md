# Chống tái sử dụng email đã reg TikTok, Blacklist tập trung & Đồng bộ an toàn (2026-09-30)

## 1. NGUYÊN NHÂN GỐC RỄ LỖI [07] "EMAIL ĐÃ CÓ TIKTOK"
- **Quy tắc bất biến:** Bên bán mail MMO (dongvanfb, boxtaikhoan) **KHÔNG BAO GIỜ** giao hotmail đã đăng ký TikTok.
- **Nguyên nhân 100% từ phía hệ thống farm:**
  - Ở các phiên chạy trước, acc reg thành công hoặc đang dở dang nhưng bị rớt lại không ghi được vào sổ cái `taikhoan_dat_v2_updated .xlsx` (do OneDrive lock file `dwShareMode=0`, crash giữa chừng, hoặc permission error).
  - Khi chạy phiên mới, `_detect_clean.py` đọc workbook thấy ô trống nên coi email này là "mail sạch" và tiếp tục cấp cho máy.
  - Khi máy nhập email vào app TikTok -> TikTok phát hiện email đã tồn tại -> nhảy sang màn hình nhập password hoặc xác minh OTP đăng nhập -> script văng lỗi `[07] email_already_registered`.

---

## 2. KIẾN TRÚC PHÒNG VỆ 2 ĐẦU: BLACKLIST TẬP TRUNG
Để triệt tiêu vĩnh viễn lỗi cấp trùng email, hệ thống thiết lập file blacklist bền vững:
`D:/Taadaa/Tiktok_Reg/data/registered_emails_blacklist.json` (được git track và đồng bộ sang remote host `admin-farm`).

### A. Đầu Chặn Trước (Preflight Eligibility)
- Trong `D:/Taadaa/Tiktok_Reg/scripts/tiktok_target_eligibility.py`:
  Hàm `load_registered_mailboxes()` nạp tập hợp email đã dùng từ 3 nguồn:
  1. Toàn bộ email trong sổ cái `taikhoan_dat_v2_updated .xlsx` (kể cả các bản backup gần nhất).
  2. Toàn bộ email trong `registered_emails_blacklist.json`.
  3. Quét nhanh 15 thư mục run gần nhất (`tracking_result_*.json`) từ `RUNS_DIR` và `SOCIAL_BATCH_RUNS_DIR`.
  -> Không một email nào từng dính dáng đến TikTok lọt qua được bộ lọc để cấp cho máy reg.

### B. Đầu Ghi Nhận Thời Gian Thực (Runtime Dynamic Blacklist)
- Trong `D:/Taadaa/Tiktok_Reg/social_reg_v1.py`:
  - Hàm `record_registered_email_blacklist(email: str)` tự động chuẩn hóa lowercase, loại bỏ khoảng trắng, ghi và de-duplicate vào `registered_emails_blacklist.json`.
  - Trong luồng `fill_email_and_next`:
    Khi kết quả trả về `registered` hoặc `registered_otp`, script **LẬP TỨC** gọi `record_registered_email_blacklist(em)` để khóa email đó ngay trong tích tắc, chặn toàn bộ các máy khác trong farm bốc lại.

---

## 3. QUY TẮC SCHEMA MAPPING & VERIFY TRACKING
- **Sổ cái chính `taikhoan_dat_v2_updated .xlsx` (Sheet: 'Tài Khoản')**:
  - Cột 1: STT máy
  - Cột 2: Tik (Slot folder)
  - Cột 3: TikTok ID / username
  - Cột 4: Password TikTok
  - Cột 5: 2FA secret
  - Cột 6: Email / GMAIL
  - Cột 7: Pass Email
  - Cột 8: SDT
  - Cột 9: DOB
  - **Cột 10: SERIAL ADB THIẾT BỊ** (Tuyệt đối KHÔNG đọc cột 11).
- Trong `scripts/deferred_tracking_writer.py::verify_written_result`:
  Bắt buộc verify `"serial": ws.cell(row, 10).value`.

---

## 4. TỰ ĐỘNG ĐỒNG BỘ 1-CHIỀU SAU KHI REG (`ensure_row_accounts.py`)
Khi batch kết thúc và merge kết quả, bắt buộc chạy tự động theo thứ tự:
1. **Merge tracking**: Phải kiểm tra trùng UID, nhưng nếu `clean_uid` trùng mà cùng số máy `STT` thì đánh dấu `VERIFIED` và chấp nhận (do runner đã auto-sync), không báo `REJECT DUPLICATE UID` sai.
2. **Sync Tik workbooks**: Gọi `sync-tik-workbooks.py --source ... --tik-dir ...` để cập nhật `Tik1.xlsx` .. `Tik8.xlsx`.
3. **Sync Safe workbook**: Gọi `sync-safe-workbook.py --source ... --output taikhoan_run_safe.xlsx` kèm token `TAADAA_ALLOW_OVERWRITE_TOKEN`.

---

## 5. KỶ LUẬT ĐIỀU PHỐI (COORDINATOR CADENCE VỚI USER KIBE)
- **User Preference:** User Kibe không quan tâm quá trình thực thi lê thê, chỉ quan tâm kết quả thực tế cuối cùng và bằng chứng trực quan (`MEDIA:<path>`).
- **Chống câm lặng:** CẤM TUYỆT ĐỐI Coordinator ôm hàng chục tool calls chạy ngầm liên tục > 2-3 phút mà không yield text Telegram.
- **Quy tắc thông báo nền:** Khi dispatch background subagent (`delegate_task`) hoặc chạy batch nền, BẮT BUỘC nhả 1 tin nhắn ngắn gọn (1-2 câu) báo rõ task đang chạy nền để user biết hệ thống không bị treo.
