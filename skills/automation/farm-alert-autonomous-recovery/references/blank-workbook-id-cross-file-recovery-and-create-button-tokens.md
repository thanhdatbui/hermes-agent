# Blank Workbook ID Cross-File Recovery & Create Button Tokens Triage

## 1. User Invariant: Chống Suy Đoán Ảu Về Phần Cứng / Cáp USB
- Khi nhận Farm Alert máy báo lỗi hàng loạt (ví dụ 12 máy cụm Admin văng script upload), CẤM TUYỆT ĐỐI suy đoán mò đổ lỗi cho hạ tầng, tuột cáp hay rớt máy khi chưa bóc log thực tế và chưa kiểm tra màn hình XiaoWei.
- **Hiện tượng**: XiaoWei trên máy Admin chiếm giữ luồng stream nội bộ qua loopback `127.0.0.1`. Khi ADB daemon chưa được định tuyến chia sẻ qua cổng LAN `192.168.110.119:5037`, máy Kibe chỉ nhìn thấy máy cục bộ và lầm tưởng cụm Admin bị offline hàng loạt.
- **Khắc phục**: Làm mới kết nối / khởi động lại daemon ADB trên Admin để nhận diện đầy đủ 79/80 máy.

---

## 2. Lỗi Nhận Diện Nút Tạo Clip `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`
- **Nguyên nhân**: Hàm `_find_bounded_create_button` trong `scripts/tiktok_workflow/state_machine.py` trước đây chỉ so khớp cứng 4 từ `{"+", "quay", "tạo", "create"}` và ép `clickable == "true"`. Các bản cập nhật TikTok dùng nhãn `"Đăng"`, `"Quay video"`, `"Tải lên"`, `"Post"` hoặc nút icon vector không có thuộc tính text/content-desc sẽ bị bỏ qua.
- **Giải pháp chuẩn hóa hai tầng (Two-Pass Create Button Resolution)**:
  1. **Step 1 (Semantic Token Match)**: Mở rộng tập token `{"\+", "quay", "tạo", "create", "đăng", "post", "tải lên", "upload", "camera"}` và dùng phép thử `any(tok in label for tok in allowed_tokens)` trong dải đáy trung tâm (`0.35 * width <= center_x <= 0.65 * width` và `center_y >= 0.82 * height`).
  2. **Step 2 (Geometric Slot Fallback)**: Bắt mọi node có thuộc tính `clickable == "true"` nằm chính xác trong khe tạo đáy (`0.40 * width <= center_x <= 0.60 * width` và `center_y >= 0.88 * height`) kể cả khi không gắn nhãn chữ.

---

## 3. Lỗi Trống Cột ID TikTok & Cơ Chế Tự Phục Hồi (Auto-Healing & Fail-Closed Safety)
- **Bản chất lỗi**: Khi tạo khung 8 ca chạy (`Tik1.xlsx` đến `Tik8.xlsx`), thao tác kéo bảng dễ để sót cột `ID TikTok` mang giá trị `None`, dẫn đến `validate_row` crash ngay khi khởi động: `Missing required fields: ID TikTok`.
- **Cơ chế Fallback thông minh trong `account_source.py`**:
  ```python
  def _recover_missing_id_tiktok(self, row_data, row_idx):
      if row_data.get("ID TikTok"):
          return
      # Step 1: Quét nguồn ID thay thế từ taikhoan_run_safe và các file Tik khác
      # Ưu tiên đối chiếu serial khớp 100%, chỉ fallback machine khi serial rỗng.
      ...
      # Step 2: Đối soát tính nhất quán và ghi bù ID vào workbook hiện tại
      unique_ids = set(found_ids.values())
      if len(unique_ids) > 1:
          # Fail-Closed: Xung đột dữ liệu giữa các file -> CẤM ghi bừa
          logger.error("[ACCOUNT_SOURCE] Xung đột ID TikTok cho Máy %s: %s; hủy phục hồi", row_data.get("Máy"), found_ids)
          return
      if len(unique_ids) == 1:
          # Duy nhất 1 ID hợp lệ -> ghi bù an toàn vào workbook hiện tại (Auto-Healing)
          ...
  ```
- **Quy chuẩn An Toàn Dữ Liệu**:
  1. **Strict Identity**: Bắt buộc đối chiếu `device ID` (serial) trước; chỉ fallback sang `Máy` khi cả 2 phía không có serial để tránh gán nhầm nick khi thay máy.
  2. **Fail-Closed on Conflict**: Khi quét nhiều workbook (`taikhoan_run_safe.xlsx`, `Tik1.xlsx`, v.v.), nếu phát hiện các nguồn trả về ID khác nhau, hệ thống bắt buộc dừng phục hồi, ghi log lỗi để `validate_row` ném ngoại lệ fail an toàn, tuyệt đối không tự ý lấy kết quả đầu tiên.
  3. **Auto-Healing**: Chỉ khi duy nhất 1 ID được xác nhận đồng thuận mới ghi bù vào file Excel hiện tại để tự động chữa lành vĩnh viễn cho các ca sau.

---

## 4. Kỷ Luật Dispatch Worker & Timeout Floor
- `dispatch_worker.py` thiết lập sàn thời gian thực thi: `SOL_AGY_TIMEOUT_FLOOR = 480` giây.
- Khi Coordinator gọi `dispatch_worker.py` qua công cụ `terminal`, tham số `timeout` BẮT BUỘC đặt `>= 600` giây để tránh bị ngắt non ở 360 giây khi Sol chuyển tầng sang Agy / Haiku.

---

## 5. Kỷ Luật Closeout Gate Trên Repo Có Dirty Legacy Code
- **Bẫy Monolith Truncation**: Khi repository đang có các thay đổi cũ chưa commit ở những file lớn (như `state_machine.py` với hàng trăm dòng dirty từ phiên trước), việc đưa cả file này vào review sẽ làm tràn diff (`TRUNCATION_MANIFEST`), khiến Sol Auditor đánh rớt điểm an toàn (Overall Score < 85).
- **Giải Pháp Định Danh Scoping**: Coordinator BẮT BUỘC sử dụng cờ `--files <target_files>` (chỉ gồm file thực sự can thiệp trong phiên và file test mới độc lập) để cô lập phạm vi đánh giá, giúp reviewer chấm điểm chuẩn xác logic vừa thi công.
- **Step-by-Step Structure Guard**: Mọi hàm/phương thức logic mới có >= 15 dòng code BẮT BUỘC phải chứa comment định danh bước rõ ràng (`# Step 1: ...`, `# Step 2: ...` khớp regex `_STEP_COMMENT_RE`) để thỏa mãn `case_invariant_require_step_by_step_structure`.
