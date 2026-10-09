# Pitfall: Tọa độ Tap Account Switcher trên Samsung & Wide Button Rows

## Hiện tượng (Symptom)
- Trong TikTok account switcher bottom sheet, script đã tìm thấy hàng tài khoản cần chuyển (ví dụ: `phamthy2004`), nhưng khi thực hiện tap thì UI không phản hồi / không chuyển sang tài khoản mới, sheet vẫn mở hoặc vẫn giữ tài khoản cũ (`selected=true` ở tài khoản ban đầu).

## Nguyên nhân gốc rễ (Root Cause)
- Node tài khoản trong switcher thường là một container `android.widget.Button` có chiều ngang toàn màn hình (`bounds=[0, y1, 1080, y2]`, `clickable=true`, `content-desc="<username>"`).
- Bên trong container Button có:
  - Avatar ở bên trái (`x ≈ 0..250`)
  - TextView chứa username ở khoảng giữa (`bounds=[252, y1_t, 596, y2_t]`, `clickable=false`)
  - Badge thông báo hoặc checkmark ở bên phải (`x ≈ 940..1032`)
- Nếu lấy tâm của Button container toàn màn hình (`center x = 540`), điểm chạm rơi vào khoảng trống giữa mép phải text và badge. Trên các thiết bị Samsung / TikTok custom sheet, sự kiện chạm vào khoảng trống này bị nuốt (swallowed) hoặc không kích hoạt click handler của row.

## Giải pháp chuẩn (Pattern)
1. **Ưu tiên bounds của TextView username con bên trong Button:**
   - Tìm child node `TextView` có text hoặc content-desc khớp username (`bounds=[252, 570, 596, 630]`, tâm `x ≈ 424, y = 600`).
   - Hoặc giới hạn bounds tap vào dải `[bounds[0] + 250, min(bounds[0] + 600, bounds[2])]` thay vì chạm vào tâm `x = 540`.
2. **Kiểm tra `is_already_selected`:**
   - Nếu node đã có `selected="true"` hoặc `checked="true"`, gửi `keyevent 4` (BACK) để đóng switcher sheet thay vì tap lại gây kẹt modal.
