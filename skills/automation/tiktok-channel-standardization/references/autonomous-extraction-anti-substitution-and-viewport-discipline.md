# Anti-Substitution, Autonomous Extraction & Viewport Discipline

## 1. CẤM THAY THẾ ẢNH NGOÀI KHO (ANTI-SUBSTITUTION MANDATE)
- Khi chuẩn hóa kênh, Avatar **BẮT BUỘC** phải trích xuất từ chính video của kênh đó (hoặc file gốc của thư mục kênh đó).
- **CẤM TUYỆT ĐỐI**: Khi bị chê ảnh xấu, agent không được tự ý lôi ảnh chó/mèo/người từ các kho folder khác (như kho 385, 399, 334...) đắp vào thay thế. Việc thay thế ảnh ngoại lai làm mất bản sắc và nhận diện của tài khoản (creator mismatch).

## 2. CÔNG CỤ TRÍCH XUẤT AVATAR TỰ ĐỘNG CHUẨN TRONG CODEBASE
- Agent **CẤM** tự biên tự diễn viết script crop tọa độ cứng (`cy, cx` cố định).
- Codebase Taadaa đã có sẵn 3 công cụ tự động hóa đã được kiểm chứng:
  1. `D:/Taadaa/tools/extract_high_confidence_avatars.py`:
     - Quét video theo timeline, đo độ sắc nét qua **Laplacian Variance** (`cv2.Laplacian(roi, cv2.CV_64F).var()`).
     - Tự động loại bỏ toàn bộ các frame bị mờ do chuyển động (motion blur, threshold >= 90).
     - Chấm điểm chất lượng: `score = (w * h) * sqrt(sharpness)`.
  2. `D:/Taadaa/face_crop_candidates.py`:
     - Tự động nhận diện bounding box đối tượng (Haar Cascade / OpenCV).
     - Tính tỷ lệ crop chuẩn: `crop_size = int(max(w, h) * 2.4)` kèm khoảng thở trên đỉnh đầu `cy_crop = cy + int(crop_size * 0.05)` để không bị lẹm tai, bay trán.
  3. `D:/Taadaa/generate_avatar_candidates.py`:
     - Dùng ffmpeg `-q:v 2` và `Pillow LANCZOS` xuất ảnh 512x512 độ nét cao, cấm crop dưới 400x400 rồi phóng đại làm vỡ hạt.

## 3. VIEWPORT DISCIPLINE TRÊN TELEGRAM (CHỐNG MÀN HÌNH ĐEN)
- Kích thước ảnh gửi qua `MEDIA:` trên Telegram **BẮT BUỘC** phải tuân theo tỷ lệ vuông hoặc dọc chuẩn (1:1 hoặc 4:5, ví dụ 1000x1000, 1060x1200).
- **CẤM** tạo canvas dạng banner dài ngang (như 1760x600, tỷ lệ > 2.5:1). Telegram mobile API không thể render thumbnail cho ảnh quá dài ngang và sẽ hiển thị thành một **khối chữ nhật đen xì** trên màn hình người dùng.

## 4. INBOUND VISION GATE & NATIVE VISION CONFIG
- Khi model chính là `ag-gemini-pool-3`:
  - Trong `config.yaml` bắt buộc phải có `supports_vision: true` cho model này ở cả `providers.omni.models` và top-level `model`.
  - `agent.image_input_mode` bắt buộc là `native`.
  - Nếu thiếu, Hermes sẽ tước bỏ pixel ảnh và fallback sang nhánh text `agent.aux_accounting` (bị crash import).
- Inbound Gate tại `gateway/run.py`: Kiểm tra transcript turn hiện tại, nếu có ảnh mà chưa gọi tool Vision (`browser_vision`, `vision_analyze`) thì Gateway ghi đè response thành `BLOCK` fail-closed 100%.
