# Avatar Nữ Chuẩn & AIFemaleFilter Priority trong pipeline_common.py

## Bối cảnh
Khi tự động cắt / tạo avatar đại diện từ video trong pipeline (`D:/Taadaa/Tiktok-video`), các kênh gái xinh / female creator cần ưu tiên chọn avatar nhân vật nữ rõ nét thay vì frame ngẫu nhiên hoặc nhân vật nam/vật nuôi xuất hiện thoáng qua trong video.

## Môi trường & Dependencies
- Python runtime: `D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe`
- Bắt buộc biến môi trường:
  ```bash
  export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
  ```
- Module lọc nữ bằng ViT ONNX: `from ai_channel_filter import AIFemaleFilter`
  - Model ONNX: `D:/Taadaa/Tiktok-video/models/onnx/model_quantized.onnx`
  - Khởi tạo: `filter = AIFemaleFilter()`
  - Kiểm tra sẵn sàng: `filter.is_ready()` (trả về `True` nếu model ONNX load thành công)
  - Phân loại frame / crop: `res = filter.classify_frame(crop)`
    - `res['is_female']`: `bool` (threshold >= 0.5)
    - `res['female_prob']`: `float` (xác suất nữ, 0.0 -> 1.0)
    - `res['male_prob']`: `float`

## Quy tắc tích hợp vào `pipeline_common.py`

### 1. Hàm `make_representative_avatar`
- **Graceful import**:
  ```python
  try:
      from ai_channel_filter import AIFemaleFilter
  except ImportError:
      AIFemaleFilter = None
  ```
- **Duyệt clusters & gán nhãn giới tính**:
  - Khởi tạo filter nếu có: `ai_filter = AIFemaleFilter() if AIFemaleFilter is not None else None`
  - Khi `ai_filter is not None and ai_filter.is_ready()`:
    - Duyệt qua các cluster có `kind == "person"`:
      - Phân loại: `res = ai_filter.classify_frame(cluster["crop"])`
      - Lưu metadata:
        ```python
        cluster["is_female"] = bool(res.get("is_female", False))
        cluster["female_prob"] = float(res.get("female_prob", 0.0))
        ```
- **Ưu tiên chọn cluster nữ**:
  - `female_clusters = [c for c in clusters if c.get("is_female")]`
  - Nếu `female_clusters` không rỗng:
    ```python
    best = max(female_clusters, key=lambda item: (item["count"], item.get("female_prob", 0.0), item["quality"]))
    ```
  - Nếu không có cluster nữ (hoặc filter không sẵn sàng): fallback về:
    ```python
    best = max(clusters, key=lambda item: (item["count"], item["quality"]))
    ```
- **Cập nhật diagnostics**:
  ```python
  if diagnostics is not None:
      diagnostics["selected_is_female"] = best.get("is_female", False)
  ```

### 2. Hàm `make_person_avatar`
- Khi duyệt các khuôn mặt ứng viên qua các frame trích xuất:
  - Nếu `AIFemaleFilter` sẵn sàng, phân loại crop khuôn mặt / vùng người.
  - Ghi nhận `is_female` và diện tích `area_score`.
  - Nếu có khuôn mặt nữ, ưu tiên chọn frame nữ có diện tích lớn nhất.
  - Nếu không có, fallback về khuôn mặt có diện tích lớn nhất chung.

## Kiểm thử & Verification
- Unit test mock focused (<30s) đặt tại `D:/Taadaa/Tiktok-video/tests/test_avatar_female_priority.py`:
  - Giả lập 2 cluster (1 nam, 1 nữ) trong đó cluster nam có count/quality nhỉnh hơn một chút.
  - Mock `AIFemaleFilter` trả về `is_female=True` cho cluster nữ.
  - Xác nhận `make_representative_avatar` chọn đúng cluster nữ.
  - Lệnh chạy test:
    ```bash
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe -m pytest D:/Taadaa/Tiktok-video/tests/test_avatar_female_priority.py
    ```
