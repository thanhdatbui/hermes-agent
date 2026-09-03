# AI Auto-Recovery Audit Gate, Venv Isolation & Warm-Only Mode (2026-08-20)

## 1. Cơ Chế Hoạt Động Của Cổng Kiểm Duyệt AI Auto-Recovery (Plan-Review Audit Gate)
* **Quy trình thẩm định:**
  1. Khi máy gặp lỗi dừng phiên, `vision_client` (Gemini 3.7 Flash) phân tích ảnh + UI XML để đưa ra chẩn đoán, đề xuất bản vá Python (`code_patch`) và hành động ADB gỡ kẹt tức thời (`action_type`, `action_args`).
  2. Trước khi chạm vào file hoặc chạy pytest, `code_patch` được nộp cho model Plan-Review (GPT-5.6 Terra / Opus) qua `plan_reviewer.audit_code_patch()`.
* **Hai nhánh rẽ xử lý:**
  - **Nhánh `APPROVED`:**
    - Ghi patch vào file đích (`benign_popup.py` hoặc `feed_swipe_smoke.py`).
    - Chạy test suite `pytest` tương ứng trên môi trường `_AUTOMATION_ENV`.
    - Tự động `git commit` kèm SHA và `git push` master để đồng bộ toàn farm.
    - Báo cáo kết quả thành công lên nhóm Telegram **Farm Alerts** kèm mã commit SHA và kết quả pytest.
  - **Nhánh `REJECTED` (Bị từ chối):**
    - Hệ thống **từ chối ghi file và hủy bỏ commit** để bảo vệ an toàn cho codebase (tránh đưa vào code tap mù tọa độ cứng, code sai signature `PopupDismissResult` hoặc selector có nguy cơ bấm nhầm nút nguy hiểm).
    - Vẫn thực thi lệnh ADB gỡ kẹt trực tiếp trên máy đang dừng để giải phóng màn hình.
    - Báo cáo lỗi `audit_rejected` minh bạch lên Telegram kèm chi tiết lý do từ chối của Reviewer.
    - Không tự động loop vô hạn khi chưa có chỉ đạo của người vận hành.

---

## 2. Cách Ly Môi Trường & Khắc Phục Lỗi Đường Dẫn Venv Trong `automation-core/alerts.py`
* **Vấn đề đã khắc phục:**
  - Khi chạy từ venv sản xuất (`D:\Taadaa\python-envs\automation\Lib\site-packages\...`), biểu thức `Path(__file__).resolve().parents[3]` bị trỏ sai về `D:\Taadaa\python-envs\automation` thay vì `D:\Taadaa` $\rightarrow$ không tìm thấy `agent.py`.
  - Biến môi trường `PYTHONPATH` chứa đường dẫn venv Hermes (Python 3.11) gây xung đột binary `_imaging` khi import thư viện `PIL` trên Python 3.12.
* **Giải pháp chuẩn:**
  1. Hàm `_find_agent_script()` duyệt danh sách candidate path ưu tiên đường dẫn tuyệt đối `D:\Taadaa\tiktok-luot nuoi acc\python_runner\ai_recovery\agent.py` trước khi fallback relative.
  2. Bọc import `PIL` an toàn: nếu dính `ImportError`, tự động dọn sạch `sys.modules['PIL*']` và loại bỏ các đường dẫn `hermes-agent` khỏi `sys.path` rồi import lại sạch sẽ.

---

## 3. Chế Độ Warm-Only: Tắt Cả Follow Lẫn Upload Hook Toàn Farm
* **Follow Hook:** Mặc định tắt (`ALLOW_CROSS_REPO_FOLLOW = False`).
* **Upload Hook:** Mặc định tắt (`ALLOW_CROSS_REPO_UPLOAD = False`).
  - Toàn bộ các phiên nuôi trong ngày (cả phiên cuối `session_index == 3`) chỉ thực hiện lướt feed tương tác tự nhiên, không gọi subprocess sang repo `tiktok-video` để upload.
  - Bật lại bằng cờ môi trường `ALLOW_FARM_UPLOAD=1` hoặc config `safety.allow_farm_upload: true`.

---

## 4. Nhận Diện & Tắt Popup Quyền Vị Trí TikTok (`detect_location_permission_popup`)
* **Màn hình:** *"Xem nội dung phù hợp và địa điểm lân cận"* / *"Mở cài đặt thiết bị của bạn và truy cập Vị trí > Trong khi sử dụng ứng dụng"*.
* **Xử lý:** Nhận diện cả 4 thành phần trong cùng modal container (Title, Body text, nút Cài đặt `android:id/button1`, nút Hủy `android:id/button3`) $\rightarrow$ tự động click nút **"Hủy"** để tiếp tục luồng lướt feed mà không nhảy ra ứng dụng Cài đặt của hệ điều hành.
