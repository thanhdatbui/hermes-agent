# Add Phone Unlabeled Close X & False Positive Login Alert Recovery

## 1. Hiện tượng & Bối cảnh Cảnh báo
Khi chạy batch feed session (`tiktok-luot nuoi acc`), hệ thống giám sát hoặc `batch_aggregator.py` phát cảnh báo P0:
```text
🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG
⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện 1 máy dính lỗi login/mất phiên:
   • Máy M51: login/account screen detected
```
Quy trình canary lập tức khóa batch và yêu cầu kiểm tra hiện trường.

## 2. Phân tích Nguyên nhân Gốc rễ (False Positive Văng Account)
1. **Thực tế hiện trường:** Tài khoản **hoàn toàn không bị văng, không mất phiên**. TikTok chỉ hiển thị sheet gợi ý **"Thêm số điện thoại"** (`com.ss.android.ugc.trill:id/g1z`, `content-desc="Trang tính dưới cùng"`).
2. **Bẫy nút đóng không nhãn (Unlabeled Close Button):**
   - Trong các bản TikTok mới / Samsung S7 Trill, nút đóng (X) ở góc trên bên phải sheet không có `text` hay `content-desc`:
     ```xml
     <node NAF="true" index="1" text="" resource-id="" class="android.widget.Button" package="com.ss.android.ugc.trill" content-desc="" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" visible-to-user="true" bounds="[936,84][1056,216]" drawing-order="5" hint="" />
     ```
   - Hàm `_close_candidate()` trong `automation_core/tiktok/benign_popup.py` trước đây chỉ đối soát `label in _ADD_PHONE_CLOSE_LABELS` (`"Đóng"`, `"Close"`, `"X"`). Khi `label == ""`, hàm trả về `None`.
   - `detect_add_phone_popup(root)` yêu cầu đủ 5 markers (trong đó có `close_x`). Khi `close is None`, hàm trả về `None`.
3. **Hiệu ứng domino gây báo động giả P0:**
   - Trong `python_runner/core/classifier.py`, khi `detect_add_phone_popup()` trả về `None`, classifier tiếp tục rơi xuống kiểm tra `has_sensitive_marker(root)`.
   - Lời giải thích của popup *"Thêm số điện thoại của bạn để tăng cường bảo mật, khôi phục tài khoản dễ hơn và đăng nhập nhanh hơn."* chứa hai từ khóa nhạy cảm: **"tài khoản"** và **"đăng nhập"**, đồng thời trên màn hình có ô nhập `android.widget.EditText` ("Số điện thoại").
   - `has_sensitive_marker(root)` trả về `True` -> Classifier gán nhầm thành `screen="manual-needed:login"` với lý do `login/account/credential marker present`.
   - `feed_swipe_smoke.py` dừng session với `stop_reason: login/account screen detected`.
   - `batch_aggregator.py` phát hiện từ khóa `"account screen"` trong `SESSION_LOST_KEYWORDS` -> Kích hoạt cảnh báo P0 mất phiên!

## 3. Quy tắc Khắc phục (Patch Contract)
Trong `automation_core/tiktok/benign_popup.py`, cập nhật `_close_candidate` với cơ chế fallback 2 tầng:
1. **Tầng 1 (Ưu tiên nhãn):** Tìm các nút có `label in _ADD_PHONE_CLOSE_LABELS`.
2. **Tầng 2 (Fallback không nhãn):** Nếu không có nút có nhãn, tìm phần tử clickable (`clickable="true"` hoặc `class` là `Button`/`ImageView`) nằm trong vùng góc trên bên phải (`left >= 800 and top <= 350`), không phải nút hành động chính (`tiếp tục` / `continue`).
```python
pool = candidates or unlabeled_candidates
if not pool:
    return None
return sorted(pool, key=lambda item: (item.bounds[1], -item.bounds[0] if item.bounds else 0))[0]
```

## 4. Kiểm chứng & Invariants
- **Tự động đóng popup:** Khi `detect_add_phone_popup` trả về `BenignPopupMatch`, classifier nhận diện đúng `ADD_PHONE_SCREEN` (confidence 0.98).
- `_maybe_dismiss_add_phone_baseline()` và `_maybe_dismiss_add_phone_row()` trong `feed_swipe_smoke.py` tự động kích hoạt `dismiss_add_phone_popup()`, chạm vào tâm `(996, 150)` để đóng popup và tiếp tục feed mượt mà.
- **Unit test bắt buộc:** Thêm `test_add_phone_unlabeled_button_close_detected()` vào `automation-core/tests/test_tiktok_benign_popup.py` sử dụng đúng cấu trúc XML hiện trường.
- **Kỷ luật điều tra O(1):** Khi nhận alert `login/account screen detected`, bắt buộc kiểm tra `ui.xml` và `screen.png` trong `runtime/.../artifacts/` để loại trừ trường hợp false positive do benign bottom sheet chứa từ khóa đăng nhập.
