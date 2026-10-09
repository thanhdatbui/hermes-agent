# Cạm Bẫy Review Scope Creep Sau Khi Canary Đã Pass & Kéo Dài Phiên 3 Tiếng (Case Máy 39)

## 1. Sự cố thực tế (Case Máy 39 - 06/09/2026)
- **Bối cảnh:** Nhận Farm Alert `[MÁY 39]` kẹt tại `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.
- **Hành trình xử lý:**
  1. Worker subagent mất nhiều lượt phân tích ảnh và layout để phát hiện TikTok mở vào tab "TẠO" (CapCut Template Hub) thay vì Camera viewfinder.
  2. Sửa xong helper `_ensure_camera_viewfinder_mode` và chạy Canary Test B4 trên máy 39: **CANARY PASS 100%** (video #5 đã đăng thực tế, Tik2.xlsx đã cập nhật, profile video tiles tăng 4 -> 5).
  3. **Sai lầm tai hại (Fatal Mistake):** Sau khi Canary đã PASS, thay vì chốt phiên ngay, Coordinator lại ném toàn bộ git diff vào Review Bot (Combo OmniRoute `:20129`).
  4. Review Bot bắt đầu soi xét các hàm/logic phụ khác ngoài phạm vi (như logic hashtag verification, draft cleanup, short-circuit boolean).
  5. Coordinator lại dispatch thêm 3 vòng subagent để đi sửa theo các góp ý phụ này, khiến worker sa lầy vào việc sửa mock test suite bị fail trong `tests/test_tiktok_workflow.py`.
  6. Tổng thời gian kéo dài hơn **3 tiếng đồng hồ**, khiến người dùng cực kỳ bức xúc (*"vkl mày làm cái đéo gì 3 tiếng k xong"*).

---

## 2. Các cạm bẫy cốt lõi (Core Anti-Patterns)

### 2.1. Vi phạm Worker Subagent Budget & Thời gian
- Quy định: Worker subagent BẮT BUỘC hoàn thành dưới **15 phút** và **<= 20 tool calls**.
- Thực tế: Coordinator để worker chạy các task phân tích layout và test full pipeline kéo dài 30–45 phút mỗi task mà không ngắt sớm hay đặt timeout chặt chẽ.

### 2.2. Review Scope Creep sau khi Canary Gate đã Pass
- Khi xử lý Farm Alert, **Canary Test trên máy thật chính là bằng chứng xác thực cao nhất (Ground Truth Evidence)**.
- Khi máy 39 đã đăng được video #5 và workbook đã ghi nhận thành công, mục tiêu của Alert đã hoàn thành 100%.
- Việc mở rộng sửa đổi sang các phần code khác (dù là clean code hay reviewer gợi ý) lúc này là **vi phạm nghiêm trọng Scope Lock**, biến 1 ca hotfix đơn giản thành đợt refactor diện rộng, dễ làm gãy các mock test cũ và kéo dài phiên vô ích.

---

## 3. Quy tắc bắt buộc khắc cốt ghi tâm (Iron Rules)

1. **CANARY PASS = FREEZE SCOPE NGAY LẬP TỨC:**
   - Ngay khi Canary Test trên máy alert pass (video đã đăng / log xác nhận / artifact hợp lệ): **CẤM TUYỆT ĐỐI** nhận thêm góp ý review mở rộng phạm vi ra ngoài hàm/lỗi ban đầu.
   - Giữ nguyên diff tối thiểu giải quyết đúng bug, chạy pytest focused test để đảm bảo không gãy test suite, và tiến hành 6 Gate chốt phiên ngay.

2. **KỶ LUẬT THỜI GIAN WORKER (HARD TIMEOUT):**
   - Mọi task delegate BẮT BUỘC ghi rõ trong prompt: `Hoàn tất trong <= 15 phút và <= 15 tool calls`.
   - Nếu worker cần phân tích ảnh hoặc XML dump, BẮT BUỘC chỉ định sẵn tọa độ nghi vấn hoặc crop khu vực hẹp, CẤM giao việc mở làm worker tự viết script OCR/CV toàn màn hình tốn 40 phút.

3. **TÁCH BIỆT HOTFIX ALERT VÀ REFACTOR ĐỊNH KỲ:**
   - Phiên xử lý Alert farm chỉ có 1 sứ mệnh duy nhất: **Đưa máy trở lại hoạt động bình thường nhanh nhất có thể (RTO tối thiểu).**
   - Mọi cải tiến thẩm mỹ, refactor kiến trúc hoặc sửa mock test ngoài lề phải đưa vào task riêng ở phiên sau, tuyệt đối không gộp vào phiên giải cứu máy live.
