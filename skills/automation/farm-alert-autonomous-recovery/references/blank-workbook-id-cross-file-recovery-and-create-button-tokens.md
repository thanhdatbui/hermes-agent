# Blank Workbook ID Cross-File Recovery & Create Button Tokens Triage

## 1. User Invariant: Chống Suy Đoán Ảu Về Phần Cứng / Cáp USB
- Khi nhận Farm Alert máy báo lỗi hàng loạt (ví dụ 12 máy cụm Admin văng script upload), CẤM TUYỆT ĐỐI suy đoán mò đổ lỗi cho hạ tầng, tuột cáp hay rớt máy khi chưa bóc log thực tế và chưa kiểm tra màn hình XiaoWei.
- **Hiện tượng**: XiaoWei trên máy Admin chiếm giữ luồng stream nội bộ qua loopback `127.0.0.1`. Khi ADB daemon chưa được định tuyến chia sẻ qua cổng LAN `192.168.110.119:5037`, máy Kibe chỉ nhìn thấy máy cục bộ và lầm tưởng cụm Admin bị offline hàng loạt.
- **Khắc phục**: Làm mới kết nối / khởi động lại daemon ADB trên Admin để nhận diện đầy đủ 79/80 máy.

---

## 2. Lỗi Nhận Diện Nút Tạo Clip `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`
- **Nguyên nhân**: Hàm `_find_bounded_create_button` trong `scripts/tiktok_workflow/state_machine.py` trước đây chỉ so khớp cứng 4 từ `{"+", "quay", "tạo", "create"}` và ép `clickable == "true"`. Các bản cập nhật TikTok dùng nhãn `"Đăng"`, `"Quay video"`, `"Tải lên"`, `"Post"` hoặc nút icon vector không có thuộc tính text/content-desc sẽ bị bỏ qua.
- **Giải pháp chuẩn hóa hai tầng (Two-Pass Create Button Resolution)**:
  1. **Pass 1 (Semantic Token Match)**: Mở rộng tập token `{"\+", "quay", "tạo", "create", "đăng", "post", "tải lên", "upload", "camera"}` và dùng phép thử `any(tok in label for tok in allowed_tokens)` trong dải đáy trung tâm (`0.35 * width <= center_x <= 0.65 * width` và `center_y >= 0.82 * height`).
  2. **Pass 2 (Geometric Slot Fallback)**: Bắt mọi node có thuộc tính `clickable == "true"` nằm chính xác trong khe tạo đáy (`0.40 * width <= center_x <= 0.60 * width` và `center_y >= 0.88 * height`) kể cả khi không gắn nhãn chữ.

---

## 3. Lỗi Trống Cột ID TikTok & Cơ Chế Tự Phục Hồi (Auto-Healing)
- **Bản chất lỗi**: Khi tạo khung 8 ca chạy (`Tik1.xlsx` đến `Tik8.xlsx`), thao tác kéo bảng dễ để sót cột `ID TikTok` mang giá trị `None`, dẫn đến `validate_row` crash ngay khi khởi động: `Missing required fields: ID TikTok`.
- **Cơ chế Fallback thông minh trong `account_source.py`**:
  ```python
  def _recover_missing_id_tiktok(self, row_data, row_idx):
      if row_data.get("ID TikTok"):
          return
      # 1. Quét taikhoan_run_safe.xlsx trong cùng thư mục
      # 2. Quét các file Tik*.xlsx khác (Tik1.xlsx...)
      # 3. So khớp theo self.device_id (serial) hoặc Máy
      # 4. Khi tìm thấy: gán row_data["ID TikTok"] = recovered
      # 5. Tự động ghi ngược lại ô Excel hiện tại và save (Auto-Healing)
  ```
- **Quy chuẩn**: Luôn gọi `_recover_missing_id_tiktok` TRƯỚC KHI gọi `validate_row` để ca chạy không bao giờ bị dừng vì lỗi thiếu dữ liệu.

---

## 4. Kỷ Luật Dispatch Worker & Timeout Floor
- `dispatch_worker.py` thiết lập sàn thời gian thực thi: `SOL_AGY_TIMEOUT_FLOOR = 480` giây.
- Khi Coordinator gọi `dispatch_worker.py` qua công cụ `terminal`, tham số `timeout` BẮT BUỘC đặt `>= 600` giây để tránh bị ngắt non ở 360 giây khi Sol chuyển tầng sang Agy / Haiku.
