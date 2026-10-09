# Multi-Machine Shared Log Interleaving & Switcher True State Audit (2026-10-03)

## 1. Hiện tượng & Triệu chứng sai lệch
Khi chẩn đoán lỗi thiếu nick trên Máy 48 (account `@inhkhanhngan1295` thuộc Row 6), agent chạy `tiktok_login_v1.py 48 --email inhkhanhngan1295` và gặp timeout 300s.
Sau đó kiểm tra đuôi file log `D:\Taadaa\Tiktok_Reg\social_reg_log.txt` và thấy các dòng:
```text
[08:27:20] [init-login] device=ce0516053a16400c02 stt=48
[08:27:23] [login] STT=48 id=inhkhanhngan1295 login_email=TamieReyesperez01295@hotmail.com sheet=Tài Khoản row=383
...
[08:27:51] [04_add_account] Máy đã có 8 tài khoản ({'kieu.lam966', 'lamhien2007', 'giabich450', 'javialdzxxj', 'francesuhunt5', 'mimiiepekgq', 'llamisbrjxy', 'trinhthuyen128'}) — đạt giới hạn tối đa 8
```
Agent đã vội vã kết luận:
*"Máy 48 đang bị ngậm nguyên dàn 8 nick của Máy 20, dẫn đến kịch trần 8 nick và không thể thêm nick Row 6."*

Người dùng lập tức phản bác và chấn chỉnh:
> *"làm đéo có chuyện ngậm nguyên cả dàn? hay mày đọc series sai"*

---

## 2. Nguyên nhân gốc rễ (Root Cause)

1. **Log Sink Dùng Chung Bị Ghi Đè Đồng Thời (Shared Log Interleaving)**:
   * File `D:\Taadaa\Tiktok_Reg\social_reg_log.txt` là một file log tĩnh được dùng chung cho **toàn bộ 80 máy** của farm.
   * Khi các ca nuôi (`multi-machine-feed-session`), ca reg, hoặc các sub-processes chạy song song trên nhiều máy, hàm `log(msg)` trong `social_reg_v1.py` mở file `social_reg_log.txt` với mode `"a"` và ghi trực tiếp mà không có session lock hoặc tiền tố serial/machine trên từng dòng phụ:
     ```python
     def log(msg):
         ts = datetime.now().strftime("%H:%M:%S")
         line = f"[{ts}] {msg}"
         with open(LOG_FILE, "a", encoding="utf-8") as f:
             f.write(line + "\n")
     ```
   * Dòng `[init-login] stt=48` được ghi ở timestamp `08:27:20`, nhưng ngay sau đó tiến trình của Máy 20 (hoặc Máy 11) đang chạy kiểm tra account dropdown cũng ghi dòng `[04_add_account] Máy đã có 8 tài khoản...` vào cùng file log ở timestamp `08:27:51`.
   * **Bẫy ngộ nhận**: Đọc log đuôi (tail log) tuyến tính đã khiến agent gán nhầm danh sách tài khoản của máy khác cho Máy 48.

2. **Thực tế hiện trường trên thiết bị thật**:
   * Khi dùng ADB kết nối trực tiếp vào Serial Máy 48 (`ce0516053a16400c02`), mở TikTok -> Profile -> Account Switcher -> screencap và chạy WinRT OCR:
   * **Kết quả thực tế**: Máy 48 có đúng 7 tài khoản chuẩn của Máy 48 theo `taikhoan_run_safe.xlsx`:
     `@thanh.truc0366`, `@thaithanh1803`, `@genewhicksb99`, `@anthieiwl8g`, `@pedroaqzzbk`, **`@inhkhanhngan1295`**, `@oanphuongvy4476`.
   * Nick `@inhkhanhngan1295` **ĐÃ NẰM SẴN TRÊN MÁY TỪ TRƯỚC**! Máy không hề thiếu nick, không hề bị văng và không hề ngậm nick lạ.
   * Nguyên nhân lỗi upload ban đầu thực chất chỉ là: app đang active nick `@thanh.truc0366`, khi mở Switcher bị trượt tọa độ chọn nick nên upload timeout, hoàn toàn không phải lỗi tài khoản.
   * Tương tự trên Máy 74 (`ce061606c21e153d03`): Nick `@julesuqi6h4` cũng đã active sẵn trên máy, chỉ vướng popup.

---

## 3. Quy tắc kiểm chứng & Checklist thực thi (Invariant)

1. **CẤM suy luận danh sách tài khoản của máy từ shared log**:
   * Tuyệt đối không dùng `social_reg_log.txt` hay bất kỳ log sink chia sẻ nào để kết luận máy có bao nhiêu nick, kịch trần 8 nick hay ngậm ký sinh.

2. **BẮT BUỘC kiểm chứng trực tiếp trên thiết bị bằng Screencap + OCR (O(1))**:
   * Để xác định chính xác danh sách tài khoản trên máy, chạy chuỗi lệnh độc lập:
     ```bash
     # 1. Mở app và Profile
     adb -s <SERIAL> shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1
     adb -s <SERIAL> shell input tap 972 1857
     
     # 2. Mở Account Switcher (header nickname)
     adb -s <SERIAL> shell input tap 400 320
     
     # 3. Chụp ảnh và chạy Windows OCR
     adb -s <SERIAL> exec-out screencap -p > screen.png
     python C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py screen.png
     ```
   * Xem trực tiếp danh sách text từ OCR để biết nick mục tiêu đã có trong Switcher hay chưa.

3. **Xử lý khi nick đã có sẵn trong Switcher**:
   * Nếu nick mục tiêu đã xuất hiện trong danh sách: CẤM gọi luồng đăng nhập `tiktok_login_v1.py` hay cố tìm nút "Thêm tài khoản".
   * Chỉ cần tap trực tiếp vào dòng của nick đó trên Switcher (tọa độ Y tương ứng từ OCR) để kích hoạt phiên làm việc, sau đó tiếp tục workflow upload/feed.
