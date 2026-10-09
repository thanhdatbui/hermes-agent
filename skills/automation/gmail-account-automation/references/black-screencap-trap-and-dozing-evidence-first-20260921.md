# Black Screencap Trap, Dozing Devices & Evidence Verification Policy

## 1. Bản chất sự cố Màn hình đen (Black Screencap Trap)
Khi thực hiện chụp màn hình Android qua ADB (`screencap -p` hoặc gọi qua wrapper Python) trên thiết bị:
- **Nguyên nhân màn hình đen kịt (file dung lượng ~20-25KB):**
  1. **Thiết bị đang ở chế độ Sleep/Dozing (Màn hình tắt):** Hệ điều hành Android ngừng render SurfaceFlinger/Window buffer. Lệnh `screencap` vẫn trả về định dạng PNG hợp lệ nhưng toàn bộ pixels là màu đen (`#000000`).
  2. **Render buffer của WebView/Chrome bị detach:** Trình duyệt chạy ngầm hoặc bị che khuất không đưa nội dung lên frame buffer.
  3. **Chưa wake-up / Unlock thiết bị trước khi chụp:** Không gửi `input keyevent 224` (WAKEUP) và `input keyevent 82` (MENU/UNLOCK).

---

## 2. Kỷ luật tối thượng: Anti-Hallucination & Evidence-First
- **Tội danh bị kết án bởi Claude CLI (Thẩm phán AI độc lập - 21/09/2026):**
  1. *Fabrication of Evidence:* Thấy log trả về mã timeout/triệu chứng thô (ví dụ `FAILED_AT_EMAIL_SUBMIT (EMAIL_SUBMIT_TIMEOUT)`) nhưng tự tiện suy đoán và khẳng định chắc nịch với người vận hành là *"Bị Cloudflare / Bot protection chặn ngầm"*, *"Dịch vụ checkmail.live timeout 25s"*. Đây là vi phạm nghiêm trọng vì làm sai lệch hoàn toàn hướng điều tra và lãng phí thời gian người vận hành.
  2. *Visual Evidence Fraud:* Gửi ảnh đen kịt do thiết bị tắt màn hình làm ảnh bằng chứng hiện trường lỗi mà không kiểm tra trước.
  3. *False Certainty Injection:* Khẳng định chắc nịch thay vì thừa nhận thiếu dữ liệu hoặc dùng nhãn giả thuyết.

---

## 3. Quy trình chuẩn bắt buộc khi chụp & gửi ảnh hiện trường
1. **Preflight Wake & Unlock trước khi chụp:**
   ```bash
   adb -s <SERIAL> shell input keyevent 224  # WAKEUP
   adb -s <SERIAL> shell input keyevent 82   # UNLOCK / MENU
   ```
2. **Kiểm tra tính hợp lệ của ảnh (Validation Gate):**
   - Kích thước file PNG: File screencap màn hình thật $1080 \times 1920$ luôn có dung lượng **từ 80KB đến 1.5MB**.
   - **Reject tự động:** Nếu file có dung lượng $\le 40KB$, coi là **ẢNH ĐEN / DOZING**, cấm gửi `MEDIA:` cho User và cấm kết luận dựa trên ảnh này.
3. **Phân định rạch ròi trong báo cáo:**
   - **`[OBSERVED]`**: Những gì THỰC TẾ nhìn thấy tận mắt trên ảnh hoặc xuất hiện chính xác trong log (không thêm thắt).
   - **`[HYPOTHESIS]`**: Nguyên nhân phỏng đoán, BẮT BUỘC ghi rõ là giả thuyết cần kiểm chứng tiếp.
   - Khi không có ảnh hoặc ảnh đen: BẮT BUỘC tuyên bố **"INSUFFICIENT EVIDENCE — Không đủ bằng chứng để kết luận nguyên nhân gốc rễ"**. Tuyệt đối không tự bịa nguyên nhân lấp liếm.
