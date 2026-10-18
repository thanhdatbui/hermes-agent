# Quy Trình Chuẩn Hoá Kênh TikTok Farm (5-Point Contract) & Bẫy Story Overlay

## 1. Bản Giao Kèo Chuẩn Hoá Kênh (Account Standardization 5-Point Contract)
Khi nhận lệnh **"Chuẩn hoá kênh"** từ User, Coordinator tuyệt đối KHÔNG được làm nửa vời (chỉ đổi tên hoặc chỉ nạp avatar). Một tài khoản được nghiệm thu là "ĐÃ CHUẨN HOÁ" bắt buộc phải thỏa mãn đủ 5 điều kiện:

1. **Avatar người thật sạch / đúng ngách (Human Face & Niche Integrity):**
   - Trích xuất frame mặt nét từ video gốc của creator (`D:\TIKTOK-videonuoinick\<ID>` hoặc `D:\video goc\<ID>`).
   - Cắt cúp vuông 512x512, canh tâm tròn (preview đường kính tròn màu xanh).
   - Dùng WinRT OCR / Vision xác nhận ảnh sạch: không text, không logo/watermark, không icon/sticker.
   - Cắm marker `.manual_avatar_locked` và đăng ký ID vào `manual_avatar_protected_folders.json` để chống các script nuôi tự động tạo đè avatar rác.
2. **Ghim Video Top (Pin Top Videos $\ge 1.000$ views):**
   - Video cắn đề xuất (đặc biệt các clip chục K view) BẮT BUỘC phải ghim lên top đầu bằng canonical `python D:/Taadaa/tools/pin_top_videos.py`.
   - Không được để video viral nằm chìm dưới lưới bài.
3. **Tiểu sử (Bio tiếng Việt tự nhiên):**
   - Bắt buộc nạp tiểu sử tiếng Việt tự nhiên, phù hợp với ngách (nữ sinh, ẩm thực, cuộc sống, đời thường).
   - Nạp chuỗi tiếng Việt có dấu qua AdbKeyboard UTF-8 Base64 broadcast (`am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <BASE64>`).
   - Tuyệt đối KHÔNG để bio trống trơn như nick ảo.
4. **Biệt danh tiếng Việt (Display Name):**
   - Đổi từ username clone (ví dụ: `huynhdiem0806`) sang tên tự nhiên tiếng Việt (ví dụ: `Huỳnh Diễm`).
   - Chạy qua canonical runner `do_rename_canonical_runner.py` kèm cơ chế OCR nghiệm thu tại chỗ.
5. **Khóa & Khớp nguồn Video trong Excel (`Tik*.xlsx`):**
   - Kiểm tra đối soát giữa cột `Folder Video (Render)` và cột `Video Goc (Nguon Cao)`.
   - BẮT BUỘC 2 giá trị này phải khớp nhau (ví dụ: đều là `179`).
   - Nghiêm cấm để lệch nguồn (ví dụ: Folder 179 gái xinh nhưng Video Goc là 183 lẫn clip AI/đồ ăn), tránh tình trạng kênh bị nhồi clip hỗn tạp phá vỡ đề xuất.

---

## 2. Bẫy Giao Diện: Popup Story Overlay & Samsung Keyboard

### Triệu chứng:
Khi mở ứng dụng TikTok và tap vào tab Hồ sơ (`972, 1857`), TikTok có thể tự động kích hoạt Bottom Sheet tạo Story với tiêu đề:
`Hiển thị với follower trong 24 giờ` kèm bàn phím Samsung mở bung ra che toàn bộ nửa dưới màn hình.

### Tác hại:
- Bàn phím che mất các nút điều hướng bên dưới.
- Vùng Header trên cùng bị đẩy lệch hoặc bị modal overlay chặn click, khiến việc tap Switcher Header `(540, 150)` hoặc vuốt Switcher sheet bị fail với lỗi `AccountSwitcherError: SWITCHER_NOT_CONFIRMED`.

### Giải pháp xử lý chuẩn:
1. Nhận diện nút đóng (icon `close` hoặc bounds `[924, 198][1068, 342]`).
2. Gửi lệnh tap vào tọa độ đóng: `dev.shell("input tap 996 270")` hoặc bấm phím Back `keyevent 4`.
3. Kiểm tra lại màn hình Profile sạch trước khi gọi `open_switcher` hoặc `open_target_profile`.

---

## 3. Quản Trị Device Lock Khi Đụng Lịch Nuôi Acc (Feed Session)
- Khi thiết bị đang chạy `multi-machine-feed-session` (PID giữ file `machine_<N>.lock.json`), Coordinator KHÔNG được tự ý force-delete lock làm gián đoạn phiên feed.
- Dùng `wait_for_device_lock` hoặc theo dõi tiến trình nền qua `log.jsonl`. Sau khi feed session hoàn tất teardown và nhả lock, mới tiến hành chiếm giữ `operator_device_lock` để thực thi chuẩn hoá an toàn.
