# Chi Tiết Quy Tắc Xử Lý Màn Hình Feed & Cooldown Nhả Follow (19/08/2026)

## 1. Cơ Chế Cooldown Nhả Follow Theo Ngày (`follow_failed_date`)
- **Vấn đề**: Khi tài khoản TikTok bị nhả nút Follow sau khi vuốt kiểm tra (`FOLLOW_FAILED: follow bị nhả sau vuốt`), nếu các phiên nuôi tiếp theo trong cùng ngày vẫn cố vào bấm Follow tiếp sẽ dễ bị TikTok quét spam block / kẹt profile.
- **Quy tắc (User chốt 19/08)**: 
  - Khi phát hiện bị nhả follow -> Đánh dấu `follow_failed = True` và ghi nhận `follow_failed_date = "YYYY-MM-DD"`.
  - Trong toàn bộ các phiên nuôi kế tiếp của ngày hôm đó, hook `_run_follow_hook` tự động kiểm tra `follow_failed_date == today` -> **Tự động SKIP bước Follow**, chỉ thực hiện lướt Feed nuôi nick như bình thường.
  - Khi sang ngày mới (00:00), cờ `follow_failed_date` tự động reset để thử nghiệm lại chu kỳ follow mới.

---

## 2. Phân Tầng Xử Lý Popup Chuẩn (Core vs In-App)
| Phân tầng | Loại màn hình / Hộp thoại | Hành vi xử lý | Thời gian chờ |
|---|---|---|---|
| **Cấp Core (`automation-core`)** | Quyền vị trí, Quyền danh bạ hệ thống (`packageinstaller`) | Tick *"Không hỏi lại"* (`id/do_not_ask_checkbox`) ➔ Bấm *"TỪ CHỐI"* (`id/permission_deny_button`) | **TẮT LIỀN (< 0.5s)** |
| **Cấp Core (`automation-core`)** | Popup *"Follow bạn bè của bạn"* trong app | Bấm nút Đóng `✕` (`id/e63`) hoặc *"Không quan tâm"* | **TẮT LIỀN (< 0.5s)** |
| **Cấp Repo (`tiktok-luot nuoi acc`)** | Phòng Livestream (`live_room_exit`) | Bấm nút **✕** (`id/e6n`, `id/e63`, `id/close`) ở góc trên bên phải | Dừng xem tự nhiên **6.0 – 14.0s** |
| **Cấp Repo (`tiktok-luot nuoi acc`)** | Chi tiết sản phẩm Shop (`shop_product_detail_close`) | Bấm nút **✕** (`id/gnl`, `id/e5w`) | Dừng xem chi tiết **3.0 – 7.0s** |
| **Cấp Repo (`tiktok-luot nuoi acc`)** | Bảng "Bài đăng lại" (`repost_sheet_close`) | Bấm nút **✕** (`id/e55`) | Dừng **2.0 – 4.0s** |
| **Cấp Repo (`tiktok-luot nuoi acc`)** | Màn hình "Số lượt xem hồ sơ" (`profile_views_back`) | Bấm nút Quay lại `←` hoặc `Đóng` (`id/llm`) | Dừng **1.5 – 3.0s** |
| **Cấp Repo (`tiktok-luot nuoi acc`)** | Màn hình Tìm kiếm / Search page (`search_screen_back`) | Gửi phím `BACK` để hạ bàn phím và đóng trang | Dừng **1.0 – 2.5s** |
| **Cấp Repo (`tiktok-luot nuoi acc`)** | Lưới sản phẩm thương hiệu (`brand_product_grid_back`) | Gửi phím `BACK` để thoát về Feed | Dừng **2.0 – 4.0s** |
| **Cấp Repo (`tiktok-luot nuoi acc`)** | Khảo sát quảng cáo Pepsi (`sponsored_ad_feedback_swipe`) | Vuốt lướt dứt khoát sang video tiếp theo | Lướt ngay |
| **Cấp Repo (`tiktok-luot nuoi acc`)** | Thẻ gợi ý kết bạn trên Feed (`follow_back_suggestion`) | Bấm nút đỏ **"Follow lại"** | Dừng **1.0 – 3.0s** |

---

## 3. Quy Chuẩn Đối Soát Danh Tính & Hiện Trường
1. **Đối soát Profile (`verify_profile`)**:
   - **CHỈ so khớp với ID/Username trong Excel (`ctx.account`)** (chuỗi `@<username>`).
   - Tuyệt đối KHÔNG so sánh với Display Name vì Excel không lưu Display Name.
2. **Khi thiếu tài khoản trong Account Switcher**:
   - GIỮ NGUYÊN HIỆN TRƯỜNG bảng Switcher trên màn hình thiết bị.
   - Báo cáo rõ đích danh *"Không tìm thấy username @xyz trong danh sách Switcher"*, tuyệt đối CẤM dọn app về Home làm mất hiện trường.
3. **CẤM mẫu câu rập khuôn**:
   - Mọi phân tích và báo cáo xử lý phải trích xuất đúng lý do kỹ thuật và hành động từ ảnh chụp thực tế (`vision_analyze`) và XML của máy lỗi.
