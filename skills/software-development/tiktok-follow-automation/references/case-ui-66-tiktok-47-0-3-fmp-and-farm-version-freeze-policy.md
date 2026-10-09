# Case UI-66: TikTok 47.0.3 Selector id/fmp & Multi-Version Fragmentation Policy

## 1. Hiện trường sự cố (2026-09-20)
- **Thiết bị:** Máy 37 (Samsung S7, Android 8.0).
- **Hiện tượng:** Màn hình Profile hiển thị nút Follow đỏ (`text="Follow"`), nhưng script lại kết luận sai lệch 100% thành `"followed"`, dẫn đến báo cáo thành công giả (False Positive).
- **Nguyên nhân gốc rễ:**
  1. Google Play Store ngầm tự động cập nhật TikTok trên máy 37 lên phiên bản **47.0.3** (trong khi máy 38 vẫn ở **46.9.3**).
  2. Ở bản 47.0.3, ByteDance đổi resource-id nút Follow/Nhắn tin từ `id/fm9` sang `id/fmp`:
     - `rid="com.ss.android.ugc.trill:id/fmp" | text="Follow"` (nút đỏ)
     - `rid="com.ss.android.ugc.trill:id/fmp" | text="Nhắn tin"` (nút xám)
  3. Tuple `_ACTION_BUTTON_SUFFIXES` trong `verify_follow.py` chỉ mới có `id/fm9`, thiếu hoàn toàn `id/fmp`.
  4. Nút Follow đỏ bị coi là `is_action_node = False` và bị bỏ qua, trong khi nút "Nhắn tin" lọt qua nhờ text marker -> script tưởng chỉ có nút "Nhắn tin" nên phán đoán sai thành `followed`.

## 2. Giải pháp kỹ thuật đã triển khai (Patch Contract)
- Bổ sung ngay lập tức `:id/fmp` và `id/fmp` vào `_ACTION_BUTTON_SUFFIXES` trong `follow_runner/flows/verify_follow.py`.
- Danh sách whitelist nút action hiện tại bắt buộc phải có cả hai đời:
  ```python
  _ACTION_BUTTON_SUFFIXES = (
      ":id/fds", ":id/ff8", ":id/fij", ":id/fi6", ":id/flo", ":id/flp", ":id/fm9", ":id/fmp", ":id/follow_button",
      "id/fds", "id/ff8", "id/fij", "id/fi6", "id/flo", "id/flp", "id/fm9", "id/fmp", "id/follow_button",
  )
  ```

## 3. Bản phán quyết kiến trúc từ Cố vấn Sol (GPT-5.6 Sol High): Về việc update phiên bản toàn farm
- **Câu hỏi của User:** "Cập nhật all máy lên bản mới nhất được không chứ mỗi máy 1 kiểu lỗi hoài nữa?"
- **Phán quyết của Sol (Review Pool :20129):**
  - **❌ CẤM TUYỆT ĐỐI update đồng loạt 80 máy lên TikTok 47.0.3 ngay lập tức.**
  - **Lý do:**
    1. **Split APKs / App Bundle khổng lồ:** TikTok 47.x gồm `base.apk` + hơn 30 file `split_df_*.apk` (hàng trăm MB). Ép update đồng loạt 80 máy gây nghẽn băng thông, CPU S7 chạy 100% để `dex2oat`, nóng máy và sập nguồn.
    2. **Nguy cơ văng Session / Logout tài sản farm:** Bản 47.x tái cấu trúc DB nội bộ, update đè làm mất session token, bắt re-login / OTP / Captcha hàng loạt acc nuôi.
    3. **Gánh nặng RAM trên Samsung S7 (RAM 4GB, Android 8):** Bản 47.x nhồi thêm module AI (`gemini_nano`), camera biz, player cồng kềnh, khiến `LowMemoryKiller` liên tục bắn chết tiến trình app.
- **Chiến lược chuẩn Farm:**
  1. **Khóa chặt biến số (Tắt Auto-Update toàn dàn):** Vô hiệu hóa tính năng tự cập nhật của Google Play Store trên 80 máy (`settings put global auto_update_apps 0`).
  2. **Code Runner Resilient (Kháng đa phiên bản):** Code phải luôn hỗ trợ cả hai đời selector (`fm9` cho 46.x và `fmp` cho 47.x) để chạy mượt dù máy ở phiên bản nào.
  3. **Canary Group 5 máy:** Chỉ thử nghiệm nâng cấp trên nhóm nhỏ 5 máy trong 48h để theo dõi crash rate trước khi tính chuyện rollout toàn dàn.
