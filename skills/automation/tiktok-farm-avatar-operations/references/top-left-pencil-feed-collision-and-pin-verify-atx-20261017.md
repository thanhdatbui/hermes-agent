# Lỗi Bẫy Nhận Diện Top-Left Pencil Trên Feed & Cơ Chế Pin Video ATX (17/10/2026)

## 1. Sự Cố Top-Left Pencil Nhận Nhầm Icon Live / Tìm Bạn Bè (Feed / Header Collision)
- **Triệu chứng**:
  Khi chạy `run_tiktok_upload_avatar.ps1`, runner văng lỗi:
  `[AVATAR_UPLOAD_MENU_MISSING] ENSURE_AVATAR: Không tìm thấy Tải ảnh lên`
  Đồng thời trong `execution.log` ghi nhận:
  `[PROFILE_LAYOUT] [METRIC] event=layout_resolved layout=top_left_pencil center=(75, 150) reason=top-left pencil icon above username at bounds [24,96][126,204]`
- **Nguyên nhân cốt lõi**:
  1. Module `scripts/tiktok_workflow/profile_layouts/top_left_pencil.py` có logic kiểm tra bounds quá lỏng:
     `0 <= n.l <= 45` và `50 <= n.w <= 170`, `50 <= n.h <= 170`.
  2. Thiếu điều kiện loại trừ các bề mặt video feed (`tree.has_text("đề xuất", "for you")`).
  3. Trên layout TikTok của các máy S7, icon ở góc trên cùng bên trái `[24,96][126,204]` (tâm `75, 150`) hoặc `[0,75][168,243]` thực chất là icon LIVE Stream (trên Feed) hoặc icon Thêm bạn / Find Friends (trên Profile). Icon này không có text và không có desc rõ ràng.
  4. State machine tap nhầm vào `(75, 150)` dẫn đến việc mở giao diện Thêm bạn / Live thay vì mở màn hình Sửa hồ sơ, sau đó tap mù vào `(540, 400)` trên màn hình sai và crash vì không tìm thấy menu tải ảnh.
- **Giải pháp dứt điểm**:
  1. Thêm guard loại trừ màn hình Feed:
     `if tree.has_rid("long_press_layout") or tree.has_text("đề xuất", "for you"): return False`
  2. Thắt chặt bounds của icon bút chì:
     `10 <= n.l <= 45 and 70 <= n.t <= 130` với kích thước `50 <= n.w <= 130 and 50 <= n.h <= 130`.

---

## 2. Kỹ Thuật Ghim Video Bằng `pin_top_videos.py` & Bẫy BACK Thoát Profile
- **Triệu chứng**:
  Sau khi tìm được video $\ge 1.000$ views (ví dụ video 371K), script mở action sheet và tap "Ghim lên đầu" thành công, nhưng bước kiểm chứng lại báo lỗi `PIN_NOT_VERIFIED` (`pinned_after: 0`).
- **Nguyên nhân**:
  1. Trên TikTok app, sau khi tap vào nút "Ghim lên đầu", TikTok tự động đóng action sheet và hiển thị thông báo "Đã ghim".
  2. Đoạn code cũ mặc định gửi lệnh `KEYCODE_BACK` ngay sau khi tap pin:
     `execute_adb_cmd(serial, ["shell", "input", "keyevent", "KEYCODE_BACK"])`
     Vì action sheet đã đóng, lệnh `KEYCODE_BACK` làm TikTok thoát khỏi trang Profile (về Home/Feed).
  3. Khi hàm `verify_pin_applied` dump UI đọc lại, màn hình không còn là Profile nên không thấy tile nào, dẫn đến ngộ nhận là ghim thất bại.
- **Giải pháp**:
  Kiểm tra lại action sheet trước khi bấm BACK:
  ```python
  sheet_chk = parse_action_sheet(dump_profile_ui_atx(serial))
  if sheet_chk:
      execute_adb_cmd(serial, ["shell", "input", "keyevent", "KEYCODE_BACK"])
      time.sleep(1.0)
  ```

---

## 3. Fallback ATX-agent Curl Trong `pin_top_videos.py`
- Trên Samsung Galaxy S7 (Android 7 / 8), `/system/bin/curl` không tồn tại.
- Lệnh `adb shell curl ...` sẽ trả về lỗi `curl: not found`.
- BẮT BUỘC dùng binary device-local của atx-agent:
  `adb shell /data/local/tmp/atx-agent curl -s --max-time 8 http://127.0.0.1:7912/dumpUI`
  trước khi thử fallback sang system curl.
