# Lỗi failed_at_state_FAILED và Floating Context Toolbar trong Caption Fill (TikTok Video Upload)

## 1. Hiện tượng & Triệu chứng hiện trường
- **Cảnh báo Farm Alert:** `[MÁY N] Triệu chứng: failed_at_state_FAILED` trong quy trình Đăng Video (`Tiktok-video`).
- **Màn hình hiện trường máy thật:**
  + Đang ở màn hình Post Composer.
  + Ô nhập caption chứa text dính hashtag (ví dụ `#cafevietnamcafevietnamcafe`).
  + Text đang bị chọn bôi đen (Select All).
  + Xuất hiện Floating Context Toolbar của Samsung Android nổi ngay trên text: `CẮT | CHÉP | DÁN | BỘ NHỚ TẠM`.
  + Phía dưới hiển thị thanh gợi ý hashtag và bàn phím ảo Samsung đang mở.
  + Nút "Đăng" (Post button) ở góc trên bên phải hoặc góc dưới đã sẵn sàng.

---

## 2. Phân tích Nguyên nhân gốc rễ (Root Cause)

### 2.1. Tầng FSM State Tracking & Reporter Masking
- Trong `scripts/tiktok_workflow/state_machine.py`:
  Khi bất kỳ state nào (như `CAPTION_FILL`) thất bại hết số lần retry, hàm `_transition(False)` gán trực tiếp `self.current_state = fail_state` (`WorkflowState.FAILED`).
- Trong `scripts/tiktok_workflow/run_post.py`:
  Reporter ghi kết quả vào `report.json` với `"last_state": machine.current_state.value`. Do `machine.current_state` đã là `WorkflowState.FAILED`, giá trị lưu vào file là:
  ```json
  {
    "status": "FAILED",
    "device_id": "...",
    "error": null,
    "last_state": "FAILED"
  }
  ```
- Bộ giám sát farm bên ngoài đọc `report.json`: Khi `error` là `null`, nó fallback sinh chuỗi lỗi:
  `f"failed_at_state_{last_state}"` $\rightarrow$ **`failed_at_state_FAILED`**.
  Mã lỗi này làm lu mờ hoàn toàn state thực tế bị hỏng (`CAPTION_FILL`), gây khó khăn cho việc định vị sự cố.

### 2.2. Tầng UI Automation tại `CAPTION_FILL`
1. **ADB Input Text Timeout:** Trên các dòng máy Samsung cũ (S7), lệnh gõ token ASCII qua ADB shell có thể dính timeout hoặc phản hồi chậm.
2. **Kích hoạt Text Selection Mode ngoài ý muốn:** Khi token input fail, flow fallback sang long-press vào ô caption để mở menu dán. Tuy nhiên, nếu ô input **đã có sẵn text dở dang**, thao tác long-press trên Samsung Android sẽ chọn toàn bộ chữ (Select All) và bật Floating Context Toolbar (`CẮT | CHÉP | DÁN | BỘ NHỚ TẠM`).
3. **Bỏ sót selector nút Dán:** `_tap_if_found` ban đầu chỉ tìm `text_contains="Dán"` / `"Paste"`. Trên Floating Toolbar hệ thống của Samsung/Android, nút Dán thường nằm ở thuộc tính `content-desc="Dán"` hoặc chữ in hoa `"DÁN"`, dẫn đến việc không tap được nút dán dù menu đang hiển thị rõ trước mắt.
4. **Xác nhận Caption quá khắt khe (`_caption_is_visible`):** Điều kiện `all(tag in normalized_visible for tag in hashtags)` bắt buộc 100% các hashtag dài phải xuất hiện đầy đủ trong XML dump. Khi TikTok gom hashtag thành chip/pill hoặc cuộn ngang, điều kiện này fail và kích hoạt vòng lặp retry 3 lần, làm text gõ chồng lên nhau.
5. **Floating Toolbar cản trở:** Nếu Floating Toolbar không được đóng, nó tiếp tục giữ focus, che chắn các thành phần UI khác và ngăn cản chuyển tiếp sang state `POST`.

---

## 3. Giải pháp Khắc phục Triệt để (4 Lớp)

### Lớp 1: Bảo toàn State lỗi trong FSM & Reporter
- **Trong `state_machine.py` (`_transition`):**
  Lưu vết state trước khi chuyển sang `FAILED`, đồng thời gán default error nếu chưa có:
  ```python
  else:
      self.last_failed_state = self.current_state
      if not self.context.error:
          self.context.error = f"Failed at state {self.current_state.value}"
      self.current_state = fail_state
  ```
- **Trong `run_post.py`:**
  Trích xuất `failed_state_val` từ `machine.last_failed_state` thay vì ghi cứng `"FAILED"`:
  ```python
  failed_state_val = (
      getattr(machine, "last_failed_state", None) or machine.current_state
  ).value if machine.current_state == WorkflowState.FAILED else machine.current_state.value
  reporter.save_report({
      "status": "FAILED",
      "device_id": device_id,
      "error": context.error or f"Failed at state {failed_state_val}",
      "last_state": failed_state_val,
  })
  ```

### Lớp 2: Nới lỏng kiểm tra Caption & Hashtag (`_caption_is_visible`)
- Nếu `all(...)` không khớp, cho phép fallback kiểm tra `any(...)`:
  ```python
  hashtags = [part for part in normalized_caption.split() if part.startswith("#")]
  if hashtags:
      if all(tag in normalized_visible for tag in hashtags):
          return True
      if any(tag in normalized_visible for tag in hashtags) or any(
          tag.lstrip("#") in normalized_visible for tag in hashtags
      ):
          logger.info("[CAPTION] Hashtag token verified in composer")
          return True
  ```

### Lớp 3: Bắt trọn nút Dán trên Floating Context Toolbar
- Bổ sung kiểm tra cả `content_desc` và chữ hoa:
  ```python
  pasted = (
      adapter._tap_if_found(xml_text, text_contains="Dán")
      or adapter._tap_if_found(xml_text, text_contains="Paste")
      or adapter._tap_if_found(xml_text, content_desc="Dán")
      or adapter._tap_if_found(xml_text, content_desc="Paste")
      or adapter._tap_if_found(xml_text, content_desc="DÁN")
      or adapter._tap_if_found(xml_text, content_desc="PASTE")
  )
  ```

### Lớp 4: Tự động Dismiss Floating Toolbar & Hạ bàn phím
- Sau khi nhập caption và settle gợi ý hashtag, kiểm tra nếu Floating Toolbar còn hiển thị:
  ```python
  post_settle_xml = adapter.dump_ui()
  if any(m in post_settle_xml for m in ('text="CẮT"', 'text="CHÉP"', 'text="BỘ NHỚ TẠM"', 'text="CUT"', 'text="COPY"')):
      logger.info("[CAPTION] Text selection toolbar active; pressing BACK to dismiss toolbar")
      adapter.keyevent("KEYCODE_BACK")
      time.sleep(1)
  ```
  Thao tác `KEYCODE_BACK` đơn lẻ sẽ đóng Floating Toolbar và hạ bàn phím mà không thoát khỏi màn hình Composer, để lộ nút "Đăng".
