# Kỷ Luật Trích Xuất Avatar Thú Cưng & Khắc Phục Lỗi Mù Vision / Telegram Canvas

## 1. Bản chất sự cố trích xuất Avatar từ Video gốc
- **Bẫy Overzoom / Digital Zoom mẩu nhỏ:**
  - Không được crop các vùng quá nhỏ (< 400x400 px) từ video dọc rồi resize phóng to ngược lên 512x512 px. Việc này tạo ra một mẩu lông vỡ hạt, mờ căm và mất hoàn toàn chi tiết mắt mũi.
  - Khi chủ thể là thú cưng (chó/mèo), nếu video là góc toàn thân đứng múa hoặc nằm, phải lấy khung hình nguyên bản có bố cục cân đối (downscale từ khung 720x720 hoặc 1080x1080 về 512x512 bằng `cv2.INTER_AREA`), tuyệt đối không ép cận cảnh nếu frame gốc không có cận cảnh nét.
- **Bẫy lấy nhầm Avatar từ kho hỗn tạp:**
  - Một số thư mục `video goc` bị trộn lẫn nhiều chủ đề (video cơ khí, nấu ăn, người nói chuyện xen lẫn thú cưng).
  - Phải dùng tool quét độ sắc nét (`Laplacian Variance >= 90`) và đối soát trực tiếp với video có view cao nhất trên kênh thực tế trước khi chọn làm avatar.

## 2. Quy chuẩn kích thước Canvas gửi Telegram (Chống hiển thị hình chữ nhật đen)
- **Kích thước cấm kỵ:** CẤM gửi các canvas proposal có tỷ lệ siêu rộng dạng banner ngang (như 1760x600 px, tỷ lệ > 2.5:1).
- **Hệ quả trên Telegram Mobile:** API Telegram hoặc Telegram client sẽ không thể tạo thumbnail xem trước cho ảnh quá dẹt ngang, hiển thị thành một ô màu đen ngòm (black box).
- **Quy chuẩn bắt buộc:** Mọi Proposal Canvas gửi qua thẻ `MEDIA:` phải dùng tỷ lệ chuẩn vuông hoặc chữ nhật đứng (1060x1200 px cho lưới 2x2, hoặc 1160x700 px cho 2 options so sánh).

## 3. Lỗi Hermes Mù Ảnh & Fallback `agent.aux_accounting`
- **Nguyên nhân cốt lõi:**
  - Khi model chính (ví dụ `ag-gemini-pool-3`) trong `config.yaml` thiếu khai báo `supports_vision: true`, hàm `run_agent._prepare_messages_for_non_vision_model()` sẽ coi model là non-vision.
  - Hermes tự động tước bỏ toàn bộ mảng pixel ảnh base64 gửi từ người dùng, rồi gọi fallback sang `vision_tools.py`.
  - Trong `vision_tools.py`, nếu import module cũ đã bị xóa `agent.aux_accounting`, hệ thống văng Exception `ModuleNotFoundError: No module named 'agent.aux_accounting'` và ném dòng lỗi text rác vào context của LLM.
- **Khắc phục dứt điểm:**
  - Đảm bảo trong `%LOCALAPPDATA%\hermes\config.yaml` có:
    ```yaml
    model:
      supports_vision: true
    providers:
      omni:
        models:
          ag-gemini-pool-3:
            supports_vision: true
    agent:
      image_input_mode: native
    ```
  - Kiểm tra qua: `python D:/Taadaa/tools/manage_hermes_config.py set model.supports_vision true --type bool --force --force-regression`.

## 4. Inbound Vision Hard-Gate & DIRTY_AVATAR False Positive
- **Inbound Gate tại `gateway/run.py`:** Bắt buộc kiểm tra transcript turn hiện tại có tool-call vision thực sự trước khi gửi text ra Telegram khi user gửi ảnh.
- **Dirty Avatar Regex:** Regex lọc số view (`\d{3,}`) trong `guard_media_vision_gate.py` phải loại trừ các file proposal/canvas tổng hợp có chứa số máy (như máy `274`), chỉ áp dụng cho ảnh avatar crop thuần túy.
