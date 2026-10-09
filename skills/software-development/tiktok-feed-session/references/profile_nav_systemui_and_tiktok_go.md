# Profile Navigation, SystemUI Focus Recovery, and TikTok GO Handling

## 1. Hiện Tượng & Root Cause: SystemUI Focus Trap khi Tap Bottom Nav

### Đặc điểm thiết bị (Samsung Galaxy S7 / màn hình 1080x1920):
- Thanh điều hướng đáy của TikTok nằm ở khoảng `bounds="[0,1794][1080,1920]"`.
- Tab Hồ sơ (Profile) nằm ở góc dưới cùng bên phải: `bounds="[864,1794][1080,1920]"`.
- Khi tap sát mép đáy (ví dụ `y=1857`), touch event dễ chạm vào vùng quản lý của `com.android.systemui` (Recent Apps / Navigation Bar).

### Cạm bẫy phục hồi (Recovery Trap):
1. `tap_navigation_target` phát hiện `post_package: com.android.systemui`.
2. Hàm gọi `recover_tiktok_focus_after_systemui_tap`, gửi phím BACK (`keyevent 4`) để kéo TikTok quay lại foreground.
3. **Cạm bẫy:** Sau khi gửi BACK, TikTok quay lại foreground nhưng lệnh tap vào tab Hồ sơ ban đầu đã bị nuốt hoặc bị phím BACK hủy mất (app vẫn đang ở Trang chủ).
4. Nếu `tap_navigation_target` trả về `NavigationResult(True, "pass")` ngay lúc này, luồng gọi (`_verify_profile_after_session`) sẽ tưởng nhầm là đã điều hướng thành công.

### Quy tắc chuẩn trong `calibrate_screens.py`:
- Sau khi khôi phục foreground TikTok từ SystemUI (`recovered_focus == True`), **bắt buộc phải retry tap target 1 lần nữa** và kiểm tra lại foreground package trước khi trả kết quả thành công.

---

## 2. Guard Đối Soát Hồ Sơ: CẤM Swipe Down ở Home Feed

### Hiện tượng lỗi:
- Khi app vẫn đang ở Trang chủ (`profile_screen_confirmed == False`), script không tìm thấy username của profile.
- Nếu script chạy fallback cuộn màn hình: `ctx.adb.shell(["input", "swipe", "540", "600", "540", "1500", "350"])` (swipe down từ trên xuống):
  - Ở màn Hồ sơ, swipe down giúp kéo header tài khoản xuống để đọc username.
  - Nhưng ở Trang chủ (Home Feed), swipe down sẽ kéo ngược feed / refresh feed, làm hiện ra thẻ quảng bá carousel như **"TikTok GO"**.
  - Sau đó script kết luận `profile account mismatch` và báo alert sai (false alarm).

### Quy tắc chuẩn trong `_verify_profile_after_session`:
1. **Nếu `not profile_screen_confirmed`:** CẤM TUYỆT ĐỐI chạy `input swipe 540 600 540 1500 350`.
2. Thay vào đó, nếu chưa xác nhận màn Hồ sơ, phải **retry điều hướng lại tab Hồ sơ (`tap_navigation_target`) tối đa 2 lần**.
3. **Chỉ khi `profile_screen_confirmed is True`** (đã chắc chắn ở màn Hồ sơ) nhưng chưa thấy username thì mới được phép swipe down kéo header xuống.

---

## 3. Thẻ Quảng Bá "TikTok GO" trong Feed

### Dấu hiệu nhận biết (XML / OCR):
- Tiêu đề / Nội dung:
  - `"TikTok GO"`
  - `"Khám phá hòn ngọc địa phương"` / `"kham pha hon ngoc dia phuong"`
  - `"Khám phá những xu hướng mới nhất từ các nhà sáng tạo gần bạn"`
- Nút hành động:
  - `"Không quan tâm"` / `"Not interested"`
  - `"Khám phá"` / `"Explore"`
  - Ký hiệu vuốt lên: `︽`

### Handler giải phóng trong `benign_popup_registry.py`:
- **Detector:** Kiểm tra sự xuất hiện của tiêu đề TikTok GO và các nút hành động tương ứng.
- **Dismisser:**
  1. Ưu tiên tìm node chứa text `"Không quan tâm"` (hoặc `"Not interested"`) và tap vào tâm bounds của nút.
  2. Fallback: Thực hiện swipe up nhẹ (`input swipe 540 1400 540 600 300`) theo ký hiệu ︽ để trượt qua thẻ về feed thông thường.
