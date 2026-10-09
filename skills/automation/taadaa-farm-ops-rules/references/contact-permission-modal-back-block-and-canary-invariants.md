# Case 88: Contact/Friend Permission Modal Blocking KEYCODE_BACK & Canary Execution Invariants (2026-09-03)

## 1. Hiện Tượng Sự Cố (Farm Alert Máy 35)
- Thiết bị dừng phiên với lỗi `unexpected popup/dialog marker detected`.
- Màn hình kẹt modal: *"Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị"* với 2 nút *"Không cho phép"* (trái) và *"Mở cài đặt"* (phải).

## 2. Anti-Pattern & Nguyên Nhân Kẹt
1. **`DeviceContext` hierarchy dump gap:** Trong flow `benign_popup_registry.py`, hàm `_safe_capture_hierarchy(ctx)` chỉ kiểm tra `ctx.dump_hierarchy()` và `ctx.adb.dump_hierarchy()`, trong khi runtime thực tế sử dụng `automation_core.ui.dump_current_ui(ctx.adb)`. Do đó hàm trả về XML rỗng `""`.
2. **Modal chặn phím BACK:** Khi không tìm thấy node nút "Không cho phép", handler rơi vào nhánh fallback gửi `KEYCODE_BACK`. Tuy nhiên dialog này của TikTok **chặn hoàn toàn phím BACK** (bấm BACK dialog không đóng), khiến popup vẫn nằm nguyên trên màn hình.

## 3. Giải Pháp Chuẩn (Case 88)
1. **Chuẩn hóa Dump XML:** Cập nhật `_safe_capture_hierarchy(ctx)` trích xuất qua `dump_current_ui(getattr(ctx, "adb", ctx))` và `dump_shell_ui(getattr(ctx, "adb", ctx))`.
2. **Multi-Locale Node Text Matching:** Parse XML node text *"Không cho phép"* / *"Don't allow"* / *"Từ chối"* / *"Hủy"* để tap trực tiếp vào tọa độ node `(cx, cy)`.
3. **Fallback Tọa Độ Tỷ Lệ:** Bổ sung fallback tap theo tỷ lệ màn hình `(w * 0.305, h * 0.639)` cho nút từ chối bên trái nếu uiautomator dump bị nghẽn (thay vì chỉ gửi BACK mù).

## 4. Invariant Điều Phối Canary Test
- Khi subagent hoàn thành fix code nhưng cạn tool call budget (`max_iterations`), Coordinator **BẮT BUỘC** dispatch tiếp subagent để thực thi canary test và đọc summary log thật.
- **TUYỆT ĐỐI CẤM** in lệnh PowerShell bắt user tự chạy.
