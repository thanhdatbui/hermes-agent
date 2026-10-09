# Account Switcher SystemUI Prose False-Negative & Network Cold-Start Recovery (2026-10-05)

## 1. Bẫy Account Switcher Bị Nhận Diện Nhầm Do SystemUI Prose

### Triệu chứng
- Canary feed-session hoặc runner dừng ở bước:
  `[ALERT] [MÁY N] Dừng: manual-needed | Lý do: account switcher requires manual review`
  tại step `profile_preflight_switcher_1_guard/attempt_1`.
- Dump UI XML tại hiện trường cho thấy:
  - Tiêu đề `"Chuyển đổi tài khoản"` hiện diện rõ ràng.
  - Danh sách tài khoản (`huehoafi23`, clone accounts) nằm đầy đủ trên màn hình.
  - Tuy nhiên hàm `_is_profile_account_switcher_xml(xml_text)` lại trả về `False`.

### Nguyên nhân kỹ thuật (Root Cause)
1. **Roster 8 Tài Khoản Đẩy Nút "Thêm Tài Khoản" Khỏi Màn Hình (Off-Screen):**
   - Trên dàn farm chuẩn 8 nick/máy (Samsung S7), khi bung Switcher, 8 dòng tài khoản chiếm toàn bộ chiều cao sheet, đẩy nút `"Thêm tài khoản"` xuống đáy ngoài tầm nhìn (`has_add_account == False`).
2. **SystemUI & Display Name Kích Hoạt `has_profile_prose`:**
   - Trong `_is_profile_account_switcher_xml`, logic cũ có kiểm tra:
     `has_profile_prose = any(" " in value and value not in _ACCOUNT_SWITCHER_TITLES for value in values)`
   - Cây XML của thiết bị Android thường chứa các thông báo status bar / SystemUI ngầm:
     - `"thông báo của dịch vụ google play: yêu cầu đăng nhập"`
     - `"thông báo của dịch vụ google play: mới đăng nhập trên windows"`
     - `"đang sạc pin, 67 phần trăm"`
     - `"4g tín hiệu điện thoại hai vạch."`
     - Hoặc nick có khoảng trắng trong display name (`"diep lam"`).
   - Vì chứa dấu cách (`" "`), `has_profile_prose` bị đánh giá là `True`, khiến hàm từ chối công nhận đây là Switcher và kết luận sai là trang cá nhân thường có dialog lạ!

### Khắc phục chuẩn trong `feed_swipe_smoke.py`
Nếu màn hình đã có tiêu đề chuẩn thuộc `_ACCOUNT_SWITCHER_TITLES` (`"chuyển đổi tài khoản"`) VÀ có ít nhất một dòng tài khoản hợp lệ (`account_rows` không rỗng), BẮT BUỘC công nhận ngay đây là Switcher hợp lệ:
```python
has_title = bool(values.intersection(_ACCOUNT_SWITCHER_TITLES))
has_add_account = any(_is_add_account_option_text(value) for value in values)
account_rows = {
    value.lstrip("@")
    for value in values
    if _is_account_like_switcher_text(value)
}
if has_title and has_add_account:
    return True
if has_title and account_rows:
    return True
```

---

## 2. Bẫy Màn Hình Lỗi Mạng Lúc Cold-Start (`id/dd9`, `ze3`, `message_tv`)

### Triệu chứng
- TikTok vừa mở lên ở baseline hiện banner/dialog:
  - `"Không có kết nối Internet. Hãy nhấn để thử lại."` (`resource-id="com.ss.android.ugc.trill:id/ze3"`)
  - Nút `"Thử lại"` (`resource-id="com.ss.android.ugc.trill:id/dd9"`, bounds `[144,1329][936,1485]`)
  - Text `"Kết nối với internet và thử lại."` (`message_tv`)
- Script dừng với lý do: `network/error/retry marker detected; swipe recovery (2 swipes) still stuck`.

### Bản chất & Khắc phục
1. **Kiểm tra liveness Proxy trước khi kết luận:**
   - Proxy Sing-box `192.168.110.2:20000+N` và upstream MobiProxy thường hoàn toàn sống 100% (`api.ipify.org` 200, `generate_204` 204). Lỗi này là do TikTok cold-start socket timeout tạm thời trong vài giây đầu.
2. **CẤM Dùng `swipe_recovery` Cho Màn Hình Mất Mạng:**
   - Vuốt màn hình (`input swipe 540 1400 540 400`) trên overlay lỗi mạng hoàn toàn vô nghĩa và chắc chắn bị stuck.
   - Bắt buộc loại trừ `NETWORK_RETRY_SCREENS` khỏi điều kiện gọi `_swipe_recovery_on_stuck`.
3. **Kích Hoạt Force-Stop Relaunch:**
   - Bắt buộc cấu hình `allow_network_force_stop_recovery = True` trong `_network_force_stop_recovery`.
   - Nếu sau khi bấm nút `"Thử lại"` (`dd9`) mà hậu kiểm XML vẫn còn dính `NETWORK_RETRY_SCREENS`, runner tự động `force_stop_and_relaunch_tiktok` để tái thiết lập socket mạng sạch thay vì dừng máy.
