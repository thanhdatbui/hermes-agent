# Google Challenge/IAP Phone Checkpoint & Anti-Spam-Loop Pattern

## 1. Hiện Trường Sự Cố (16/09/2026)
- **Hiện tượng:** Script `run_oauth_s7_pipeline.py` (hoặc các luồng OAuth GPM) gặp màn hình Google Checkpoint:
  - URL: `accounts.google.com/v3/signin/challenge/iap`
  - Tiêu đề: "Xác minh danh tính của bạn"
  - Nội dung: *"Có điều bất thường về hoạt động của bạn. Để bảo mật tài khoản của bạn, Google muốn đảm bảo rằng người đăng nhập chính là bạn. Nhập số điện thoại để nhận tin nhắn văn bản cùng mã xác minh."*
  - Trên màn hình có ô nhập SĐT (cờ US hoặc quốc tế), link "Thử cách khác" và nút "Tiếp theo".
- **Lỗi của script:**
  1. Thấy link `"Thử cách khác"`, script click rồi `continue` trong vòng lặp `while time.time() - start_t < 180`. Do Google không có phương thức khác, trang reload lại đúng màn `challenge/iap`. Script click "Thử cách khác" lặp đi lặp lại liên tục suốt 180s cho đến khi timeout.
  2. Điều kiện điền số điện thoại cá nhân (Tad `0906746624`) có match lỏng `or "nhận mã xác minh" in b_txt`, dẫn đến việc script tự ý điền số 24 vào ô nhập SĐT mới khi bị checkpoint lạ.

---

## 2. Bản Chất Kỹ Thuật
- `challenge/iap` là **Hard Phone Verification Checkpoint** của Google: Google phát hiện IP/Proxy bất thường hoặc vân tay profile khả nghi, khóa đăng nhập và bắt buộc nhập số điện thoại để giải mã.
- Với các tài khoản farm không gắn SIM thực tế, click "Thử cách khác" **hoàn toàn vô ích** và chỉ làm tăng nguy cơ tài khoản bị Google flag/khóa vĩnh viễn vì spam request.

---

## 3. Quy Tắc Bắt Buộc (Strict Invariants)

### A. Giới Hạn Thử "Thử cách khác" Tối Đa 1 Lần
- Khởi tạo biến đếm `try_another_phone_count = 0` trước vòng lặp đăng nhập.
- Nếu `try_another_phone_count >= 1` mà vẫn ở `challenge/iap` $\rightarrow$ **DỪNG NGAY LẬP TỨC (FAIL-FAST)**.

### B. Fail-Fast Checkpoint Return
- Chụp ảnh hiện trường: `oauth_{email}_hard_phone_checkpoint_{timestamp}.png`.
- Ghi log rõ ràng: `[M{mid}] 🛑 Google Hard Phone Checkpoint (challenge/iap) -> DỪNG NGAY KHÔNG SPAM!`.
- Trả về ngay: `{"mid": mid, "email": email, "status": "PHONE_CHECKPOINT", "reason": "Google Hard Phone Checkpoint (challenge/iap)"}`.

### C. Khóa An Toàn Điền SĐT Cá Nhân
- **TUYỆT ĐỐI CẤM** match lỏng `"nhận mã xác minh"`.
- **CHỈ ĐƯỢC** điền số `0906746624` khi và chỉ khi text hiển thị rõ ràng việc xác nhận số điện thoại cũ có đuôi 24:
```python
# CHUẨN:
if "24" in b_txt and ("xác nhận số điện thoại" in b_txt or "••" in b_txt or "đuôi" in b_txt or "số điện thoại bạn đã" in b_txt):
    phone_confirm_inp.fill("0906746624")
```
