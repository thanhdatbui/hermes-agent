# Xử lý Popup USB Debugging ("Cho phép gỡ lỗi USB") trong Automation TikTok

## Hiện tượng & Nguyên nhân (2026-09-21)
- Trên các máy Android nông trại (như M20, M46, M63...), hệ điều hành hoặc service adb có thể kích hoạt dialog hệ điều hành:
  - `"Cho phép gỡ lỗi USB?"` / `"Allow USB debugging?"`
  - Checkbox `"Luôn cho phép từ máy tính này"` / `"Always allow from this computer"`
  - Nút `"OK"`.
- Khi popup này bật lên, nó chiếm foreground (nằm đè lên TikTok app), khiến hàm `wait_login_success` hoặc các bước thao tác UI khác tưởng nhầm app bị mất foreground hoặc timeout sau 30s.

## Cơ chế xử lý chuẩn (`dismiss_usb_debugging_dialog`)
1. **Phát hiện qua XML UI**:
   - Quét từ khóa không dấu / chữ thường: `cho phep go loi usb`, `allow usb debugging`, `luon cho phep tu may tinh nay`, `always allow from this computer`.
2. **Hành động tap**:
   - Bấm checkbox: `"Luôn cho phép từ máy tính này"` / `"Always allow from this computer"`. Sleep 0.5s.
   - Bấm nút `"OK"` (qua text tap, hoặc node có `prefer_clickable=True`, hoặc toạ độ fallback chuẩn máy S7 `(890, 1140)`). Sleep 1.0s.
3. **Vị trí tích hợp trong luồng code (`social_reg_v1.py` / `tiktok_login_v1.py`)**:
   - Trong `_dismiss_system_popups(device_id)`: gọi ngay sau các dialog restore config và trước/sau permission dialog.
   - Trong `wait_login_success(...)`: gọi trước và sau khi kiểm tra `APP_PACKAGE not in (xml or "")` để giải phóng màn hình ngay khi USB debugging dialog nhảy lên đè foreground.
