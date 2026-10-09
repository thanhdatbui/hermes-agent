# Switcher False-Anchor Trap & Canonical Core Discipline (Case Máy 1 — 07/09/2026)

## 1. BỐI CẢNH & PHẢN ỨNG CỦA USER
- **Sự cố:** Khi chạy batch 2FA TikTok trên Máy 1 (`ginnyhanstei80`), máy đang login nick `@tranngan767`. Script văng lỗi `SWITCHER_OPEN_FAILED`.
- **Hành vi sai trái của Coordinator:** Thay vì dùng và debug đúng module chuẩn `automation_core.tiktok.account_switcher`, Coordinator lại quan sát màn hình rồi tự chế ra một flow UI thủ công mới: *"bấm vào Menu ☰ -> Cài đặt và quyền riêng tư -> Cuộn xuống đáy chọn Chuyển đổi tài khoản"*.
- **User bức xúc & chấn chỉnh:** *"Clgt account switcher t thiết kế r mà lại đi chế gì v"*. Hệ thống farm đã có module chuẩn `automation-core`, mọi flow chuyển tài khoản trên toàn bộ dàn máy đều đã được thiết kế tập trung; cấm tuyệt đối việc tự vẽ flow UI lẻ tẻ khi gặp lỗi.

---

## 2. NGUYÊN NHÂN GỐC RỄ (ROOT CAUSE: FALSE ANCHOR AT BODY)

### A. Thiết kế chuẩn của `account_switcher`
- Trên TikTok (đặc biệt các bản cập nhật mới trên Samsung S7), khi mới vào Profile, thanh header đỉnh màn hình KHÔNG hiển thị sẵn nút dropdown tên tài khoản.
- `account_switcher` có cơ chế rất thông minh: Nếu không tìm thấy anchor ở header, hàm `prepare_switcher_anchor()` sẽ được kích hoạt:
  ```python
  def prepare_switcher_anchor(self) -> bool:
      # Swipe nhẹ 400px từ y=1248 lên y=806 trong 150ms
      self.adb.shell(["input", "swipe", "540", "1248", "540", "806", "150"], check=False)
  ```
  Cú swipe này đẩy trang Profile cuộn nhẹ lên, khiến tên tài khoản dính vào thanh **Sticky Header** ở đỉnh màn hình (`y <= 200`), lúc này nút dropdown switcher mới lộ ra để tap.

### B. Lỗ hổng logic trong `find_switcher_anchor()`
- Trong `automation_core/src/automation_core/tiktok/account_switcher.py` (dòng 539):
  ```python
  username_candidates = [
      node
      for node in nodes
      if node.center is not None
      and header_left <= node.center[0] <= header_right
      and (
          node.center[1] <= header_y
          or (has_profile_menu and node.attributes.get("clickable", "false").casefold() == "true")
      )
      and node.text.strip().startswith("@")
  ]
  ```
- **Hậu quả:** Nhánh `or (has_profile_menu and node.attributes.get("clickable", "false").casefold() == "true")` đã **bỏ qua hoàn toàn điều kiện tọa độ Y (`node.center[1] <= header_y`)** khi trang có Profile Menu.
- Trên Máy 1, dòng chữ **`@tranngan767`** nằm ở thân trang profile (dưới avatar, `bounds=[400, 594][679, 639]`, `center_y = 616`) lại có thuộc tính `clickable="true"`.
- `find_switcher_anchor()` bắt nhầm ngay node thân này làm anchor (`anchor is not None`).
- Vì ngỡ đã tìm thấy anchor, runner **bỏ qua hoàn toàn hàm `prepare_switcher_anchor()`** (không thèm swipe), rồi bấm thẳng vào giữa màn hình (`y = 616`).
- Bấm vào text `@tranngan767` ở thân profile không làm bật bảng switcher. Sau 3 nhịp chờ không thấy bảng switcher xuất hiện, hàm văng `AccountSwitcherError: SWITCHER_OPEN_FAILED`.

---

## 3. GIẢI PHÁP & KỶ LUẬT BẮT BUỘC

1. **Khóa cứng tọa độ Y của Header Anchor:**
   - Anchor mở Switcher trên thanh header BẮT BUỘC phải nằm ở nửa trên đỉnh màn hình (`node.center[1] <= header_y`, cụ thể `y <= 250` trên màn hình 1080x1920).
   - CẤM TUYỆT ĐỐI bắt các node `@username` nằm ở thân profile (`y > 300`) làm switcher anchor.
2. **Kích hoạt đúng nhịp `prepare_switcher_anchor()`:**
   - Khi ở trạng thái profile ban đầu, vì đỉnh chưa có anchor $\rightarrow$ `anchor = None`.
   - Hệ thống tự động gọi `prepare_switcher_anchor()` để swipe cuộn dính tên nick vào Sticky Header $\rightarrow$ UI refresh $\rightarrow$ Anchor xuất hiện trên đỉnh $\rightarrow$ Tap mở switcher thành công 100%.
3. **Kỷ luật kiến trúc:**
   - Khi một công cụ/module nền tảng (`automation-core`) gặp lỗi trên máy thật, BẮT BUỘC phải phân tích và fix đúng root cause trong module đó.
   - TUYỆT ĐỐI CẤM thói quen tự chế đường vòng (workaround) bằng cách đề xuất các thao tác UI thủ công ngoài lề làm phá vỡ tính đồng nhất của hệ thống farm.
