# Cạm bẫy False Positive Danh bạ & Kẹt Bottom Sheet "Gửi đến" (Share Sheet)

## 1. Cạm bẫy từ khóa quá rộng trong `detect_contact_follow_suggestion`
- **Hiện tượng:** Máy lướt feed hoặc gặp phiên TikTok LIVE bán hàng (ví dụ LIVE Vinamilk trên M24) bị văng `manual-needed:popup` với lý do `unexpected popup/dialog marker detected` (classification: `known contact_follow_suggestion popup detected`).
- **Nguyên nhân gốc rễ:** 
  - Trong `automation_core/tiktok/benign_popup.py`, bộ từ khóa `contact_marker` chứa từ khóa quá rộng: `"mời bạn"`.
  - Trên LIVE stream hoặc video feed, người dùng chat / comment các câu thông thường như *"Nhà có tiệc, mời bạn chung vui!"*.
  - Từ khóa `"mời bạn"` match câu chat này ➔ đánh dấu `contact_marker`.
  - Kết hợp với nút "Follow" hoặc "Follow lại" trên header phiên LIVE / video ➔ script tưởng nhầm là popup gợi ý danh bạ/kết bạn và cố tap đóng.
  - Khi tap đóng thất bại hoặc tap nhầm vào livestream, bot rơi vào `manual-needed:popup`.
- **Giải pháp chuẩn:**
  - Tuyệt đối KHÔNG dùng các cụm từ cụt như `"mời bạn"`. Bắt buộc phải là `"mời bạn bè"`, `"đồng bộ danh bạ"`, `"người bạn có thể biết"`.

## 2. Kẹt Bottom Sheet "Gửi đến" (Share Sheet) sau khi đóng gợi ý
- **Hiện tượng (M75, M78):**
  - Sau khi bot xử lý thẻ gợi ý kết bạn hoặc profile người dùng, giao diện vô tình chạm vào nút Share / Chia sẻ khiến bảng "Gửi đến" (`com.ss.android.ugc.trill:id/tv_title`) bung lên từ đáy màn hình.
  - Màn hình bị phân loại thành `unknown`, và bot dừng với lỗi:
    `manual review required after contact_follow_suggestion dismiss: unknown`
- **Đặc điểm kỹ thuật của Bottom Sheet:**
  - Bottom Sheet (Share Sheet) có resource-id `:id/tv_title` với text `"Gửi đến"` / `"Send to"`, hoặc content-desc `"Trang tính dưới cùng"` / `"Bottom sheet"`, kèm các nút hành động như `"Sao chép liên kết"` (`:id/w61`).
  - Vuốt màn hình (`swipe`) KHÔNG thể đóng được Bottom Sheet trên Android TikTok.
- **Giải pháp chuẩn:**
  - Đăng ký `detect_share_sheet` trong `detect_allowed_generic_popup` (`automation_core/tiktok/benign_popup.py`).
  - Gán hành vi xử lý (`_dismiss_action`) cho `share_sheet` là `"press_back"` (gửi lệnh phím Android `BACK`).
  - Lệnh `BACK` sẽ hạ trang tính xuống an toàn ngay lập tức và đưa màn hình trở về feed chính.

## 3. Quy tắc kiểm thử DeviceLock khi chạy Closeout Gate
- Khi `DeviceLock` thoát context `with DeviceLock(...) as lock:`, phương thức `__exit__` sẽ tự động release và xóa file lock (`machine_XX.lock.json`).
- Lệnh `inspect_device_lock` trên một lock đã release sẽ ném `DeviceLockTransactionError: DEVICE_LOCK_INSPECT_PATH_MISSING` (đây là hành vi chuẩn bảo vệ tính nhất quán).
- Test suite kiểm tra cleanup bắt buộc dùng `with pytest.raises(DeviceLockTransactionError): inspect_device_lock(...)`.
