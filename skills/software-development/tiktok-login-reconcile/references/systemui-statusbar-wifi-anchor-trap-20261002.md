# Bẫy Status Bar Wi-Fi / SystemUI Intercept Switcher Anchor & SWITCHER_NOT_CONFIRMED (2026-10-02)

## 1. Hiện Tượng & Triệu Chứng
- **Hiện tượng lỗi**: UploadHook hoặc Feed swipe dừng ca trên máy (ví dụ Máy 76, serial `9885b64d56305a3731`) với lỗi:
  `UploadHook: [ACCOUNT_SWITCHER_FAILED] open_switcher failed: SWITCHER_NOT_CONFIRMED: switcher markers were not confirmed. Cần MANUAL_REVIEW...`
- **Ảnh hiện trường**: Màn hình vẫn ở nguyên trang Profile cá nhân của nick hiện tại (`ucloan77901`), không mở được drawer bottom-sheet danh sách tài khoản.

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause)

1. **Vùng Tọa Độ Header (`_profile_header_region`)**:
   - `account_switcher.py` trong `automation-core` định nghĩa vùng header để tìm anchor mở switcher:
     `bounds: x1 >= 0.35 * width, x2 <= 0.75 * width, y2 <= 0.1667 * height` (trên màn 1080x1920: `300 <= x <= 780, y <= 320`).
2. **SystemUI Status Bar Node Lọt Vào Vùng Header**:
   - Trên thanh trạng thái Android (`com.android.systemui`), icon Wi-Fi combo:
     `com.android.systemui:id/wifi_combo`, content-desc: `"Tín hiệu Wi-Fi đủ."`, bounds: `[733, 14][783, 56]`, center: `(758, 35)`.
   - Tọa độ này thỏa mãn `300 <= 758 <= 780` và `35 <= 320`.
3. **Anchor Selection Bị Đánh Lừa**:
   - `find_switcher_anchor` không lọc bỏ package hệ thống `com.android.systemui`.
   - Kết quả: Core chọn nhầm icon Wi-Fi làm `generic_candidates` mở switcher thay vì tap vào display name `ucloan77901` (`bounds [267, 304][569, 340]`).
   - Script tap lên icon Wi-Fi trên thanh status bar $\rightarrow$ Menu switcher không mở $\rightarrow$ Văng lỗi `SWITCHER_NOT_CONFIRMED`.

---

## 3. Bản Vá & Quy Tắc Khắc Phục (Core Fix & Test)

1. **Lọc Sạch SystemUI Trong `find_switcher_anchor`**:
   Tại `src/automation_core/tiktok/account_switcher.py`:
   ```python
   nodes = [
       node
       for node in _nodes(xml_text)
       if node.attributes.get("package") != "com.android.systemui"
       and not (node.resource_id and node.resource_id.startswith("com.android.systemui"))
   ]
   ```
2. **Unit Test Phòng Chống Hồi Quy (Regression Test)**:
   Trong `tests/test_account_switcher_preconfirmed.py`:
   ```python
   def test_find_switcher_anchor_ignores_systemui_status_bar() -> None:
       xml = """<hierarchy bounds="[0,0][1080,1920]">
         <node bounds="[733,14][783,56]" package="com.android.systemui" resource-id="com.android.systemui:id/wifi_combo" text="" />
         <node bounds="[267,304][569,340]" package="com.ss.android.ugc.trill" resource-id="com.ss.android.ugc.trill:id/tv_title" text="ucloan77901" clickable="true" />
       </hierarchy>"""
       anchor = find_switcher_anchor(xml, allow_generic_header=True)
       assert anchor is not None
       assert anchor.text == "ucloan77901"
   ```
3. **Xác Minh Sau Sửa**:
   - Chạy `pytest D:/Taadaa/automation-core/tests/test_account_switcher_preconfirmed.py` PASS 100%.
   - Chạy `closeout_gate.py` đảm bảo Sol Reviewer chấm Score >= 85 (Approved).
