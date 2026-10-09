# Switcher Feed Drift & Account Switcher Tap Bounds Pattern

## 1. Sự Cố Mismatch Danh Tính Do Trôi Về Feed (Feed Drift Profile Misattribution)

### Hiện tượng lỗi thực tế
Trong các ca nuôi acc (`tiktok-luot nuoi acc`), runner bất ngờ dừng hàng loạt máy với cùng triệu chứng:
```text
[ALERT] [MÁY N] Dừng: manual-needed | Lý do: profile username still mismatched after switch
```
Trên ảnh chụp hiện trường, máy không hề mở trang Hồ sơ mà đang hiển thị video lướt feed Trang chủ (For You), có tiêu đề video và tên creator (ví dụ `@Linhnguyen1707`, `@refughbmh33`...).

### Nguyên nhân cốt lõi (Anti-Pattern)
1. Sau khi TikTok thực hiện chuyển đổi tài khoản (account switch) hoặc đóng các popup, ứng dụng thường tự động chuyển hướng màn hình về Trang chủ (Home / For You feed).
2. Khi runner gọi `_profile_guard_drifted_from_profile()`, logic cũ chỉ kiểm tra:
   ```python
   # ❌ SAI LẦM:
   if "keyboard cleanup" in reason:
       return True
   return xml_error in FEED_CONFIRMED_XML_DEGRADED_ERRORS
   ```
3. Nếu bản dump XML từ ATX/UiAutomator tải sạch hoàn chỉnh (`xml_error == ""`), hàm trả về `False` $\rightarrow$ runner tưởng nhầm là app vẫn đang đứng ở trang Profile.
4. Runner tiếp tục gọi `read_profile_identity()`, phân tích nhầm video feed như profile: bốc nhầm tên creator video For You gán vào `current_username` và đem so khớp với nick nuôi $\rightarrow$ Kích hoạt dừng an toàn `profile username still mismatched after switch` sai lệch hàng loạt máy.

### Giải pháp chuẩn (Case Fix)
Trong `feed_swipe_smoke.py` (`_profile_guard_drifted_from_profile`):
1. **Khẳng định trôi màn hình khi màn hình là Feed:**
   ```python
   if detected in {"home", FEED_TYPE_FOR_YOU, FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS}:
       return True
   ```
   Kể cả khi `xml_error == ""` hoặc XML không bị lỗi degraded, nếu màn hình đã là Home/Feed thì khẳng định ngay là **đã bị trôi khỏi Profile**.
2. **Kích hoạt Re-tap Profile Tab:**
   Khi phát hiện drift, `_read_profile_identity_with_add_phone_guard` gọi `_try_profile_retap_on_drift` để tap lại vào tab Hồ sơ đáy màn hình (`[972, 1857]`), đưa app về đúng Profile trước khi đọc username.

---

## 2. Lỗi Điểm Chạm Hàng Switcher Bị Nuốt Sự Kiện (Switcher Row Tap Dead-Zone)

### Hiện tượng lỗi thực tế
Trên một số phiên bản TikTok (như TikTok 46.2.3 trên Samsung Galaxy S7), khi mở sheet "Chuyển đổi tài khoản", tài khoản đích có hiển thị đầy đủ trong danh sách. Runner gửi lệnh `input tap` nhưng TikTok không chuyển tài khoản; dấu kiểm (`id/fdu`) vẫn nằm nguyên ở tài khoản cũ.

### Nguyên nhân cốt lõi (Anti-Pattern)
1. Cấu trúc UI của bottom sheet:
   ```xml
   <android.widget.Button rid='...:id/l9b' cdesc='target_account' bounds='[0, 816][1080, 1032]' clickable=true>
       <android.widget.TextView rid='...:id/mtx' text='target_account' bounds='[252, 894][543, 954]' clickable=false />
   </android.widget.Button>
   ```
2. Container `Button` phủ toàn màn hình (`x: 0 -> 1080`). Điểm giữa hình học là `center_x = (0 + 1080) / 2 = 540`.
3. Vùng `x = 540` nằm ở **khoảng trống màu trắng ngoài cùng bên phải** của username text (kết thúc ở 543). Cú tap tại `x=540` không kích hoạt trigger chuyển đổi trên một số build UI của TikTok.
4. Ngược lại, nếu override toàn bộ `best_bounds = inner.bounds` (chỉ lấy TextView `id/mtx`), thì:
   - Node `mtx` có `clickable="false"`.
   - Chiều cao `y` của TextView hẹp hơn (`y: 894 -> 954`), dễ trượt nếu màn hình có micro-scroll.

### Giải pháp chuẩn (Case Fix)
Trong `_find_account_switch_option`:
1. Giữ nguyên phạm vi trục Y `(y1, y2)` của Button cha (`node.bounds[1]`, `node.bounds[3]`) để đảm bảo không trượt hàng.
2. Giới hạn trục X vào vùng danh tính thực (Avatar $X \approx 100..250$ và Username text $X \approx 252..500$):
   ```python
   # Kết hợp X của inner text/avatar với Y của container cha:
   if inner.bounds and inner.center:
       inner_w = inner.bounds[2] - inner.bounds[0]
       if 0 < inner_w < 600 and node.bounds[1] <= inner.bounds[1] and inner.bounds[3] <= node.bounds[3]:
           best_bounds = (inner.bounds[0], node.bounds[1], inner.bounds[2], node.bounds[3])
           break
   ```
   Hoặc fallback:
   ```python
   best_bounds = (node.bounds[0] + 100, y1, min(node.bounds[0] + 500, node.bounds[2]), y2)
   ```
3. Sau khi tap switcher, cho phép thời gian settle từ `4.5 - 6.0s` để bottom sheet đóng lại và phiên tải hoàn tất trước khi kiểm tra lại danh tính.

---

## 3. Băng Thông Truyền Tải ADB Trên Farm Lớn (USB Hub Saturation)

1. Khi 70-80 điện thoại cắm cùng hệ thống hub USB, băng thông truyền dữ liệu ADB trên mỗi thiết bị giảm xuống chỉ còn khoảng `0.1 MB/s`.
2. Lệnh cài đặt trực tiếp qua adb (`adb install-multiple -r`) đối với bộ split APK dung lượng lớn (~200MB) sẽ mất 25–35 phút, gây timeout nếu dùng ngưỡng timeout mặc định 600s.
3. Không thực hiện cập nhật APK hàng loạt trong giờ farm đang chạy batch nặng. Nếu cần cập nhật thiết bị đơn lẻ, phải dự trù timeout tối thiểu 1800s - 2400s (30-40 phút) hoặc đẩy nền tệp tin vào bộ nhớ tạm trước khi cài đặt.
