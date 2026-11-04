# Kỷ Luật Vệ Sinh URL Báo Lỗi & Chống Rác Tin Nhắn Telegram Trong Cronjob Quét Lô

## 1. Triệu Chứng Bệnh Lý: Xả Rác URL OAuth Vào Telegram
- Khi watchdog/cron quét tài khoản theo lô (như `cron_auto_feed_chatgpt_pool.py`) gặp lỗi đăng nhập, trình duyệt CDP thường dừng lại ở các trang OAuth trung gian (Google SSO, Microsoft Login, OpenAI Callback).
- Các URL này thường mang theo query strings đồ sộ (`clientid`, `redirecturi`, `part`, `rart`, token Base64) dài từ 800 đến 2.000 ký tự.
- **Bẫy code cẩu thả:** Script ghi nhận thẳng:
  ```python
  res["error"] = f"Không tìm thấy session-token hợp lệ. URL: {page.url}"
  ```
  Và khi có 1-2 tài khoản fail, script gom chuỗi `{err}` này ném nguyên văn lên Telegram.
- **Hậu quả:** 
  - Tin nhắn bị phình to bởi hàng trăm dòng text mã hóa vô nghĩa.
  - Người dùng hoàn toàn không hiểu gửi link dài đó để làm gì, gây bực bội và ô nhiễm kênh điều phối.

## 2. Quy Chuẩn Vệ Sinh Cơ Giới Hóa (Sanitization Invariant)
1. **Bóc Tách Query Params Tuyệt Đối:** Mọi trường hợp lấy URL hiện tại từ trình duyệt để đưa vào error log / Telegram summary BẮT BUỘC phải gọt bỏ chuỗi `?query`:
   ```python
   clean_url = page.url.split('?')[0][:80] if page.url else ''
   res['error'] = f'Khong tim thay session-token hop le (URL: {clean_url})'
   ```
2. **Khống Chế Độ Dài Tối Đa:** URL mô tả lỗi không được vượt quá 80-100 ký tự. Chỉ cần phản ánh đúng trang đích mà trình duyệt đang dừng lại (ví dụ: `https://accounts.google.com/v3/signin/identifier` hoặc `https://chatgpt.com/auth/login`).

## 3. Ràng Buộc Sửa Đổi Bằng `unified_patch_pipeline.py`
- Khi sửa đổi logic thông báo lỗi trong script, hệ thống phòng hộ Farm kích hoạt `MANDATORY_TEST_DELTA_VIOLATION` nếu chỉ chỉ định sửa logic file mà không có file test tương ứng.
- **Quy chuẩn thi công:**
  - Luôn truyền đồng thời cả 2 file: `--file scripts/<name>.py --file tests/test_<name>.py`.
  - Viết test assertion kiểm chứng rằng error string kết xuất thực sự đã được loại bỏ các tham số nhạy cảm (`sensitive_token`, `?`, query parameters).
