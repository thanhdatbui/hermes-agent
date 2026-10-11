# Gemini Worker Default & Luna Fallback Mandate (2026-10-11)

## 1. Chỉ Thị Định Tuyến Worker Từ User (User Mandate 2026-10-11)
> *"Sửa là subagent chạy ag gemini pool, luna chỉ làm fallback"*

Trong phiên làm việc ngày 11/10/2026, User đã sửa đổi và chốt dứt khoát quy tắc định tuyến cho Subagent Worker (`delegate_task`):
- **Worker chính thức (Primary):** Bắt buộc chạy trên **`ag-gemini-pool-3`** (Gemini) với `reasoning_effort: medium`.
  - Tận dụng triệt để pool tài khoản Gemini miễn phí (hơn 40 accounts), tốc độ phản hồi nhanh (30-40s), không tốn quota trả phí.
- **Worker dự phòng (Fallback):** **`cx/gpt-5.6-luna-high`** (Luna High) **CHỈ ĐƯỢC PHÉP KÍCH HOẠT KHI VÀ CHỈ KHI** pool Gemini gặp sự cố (429 Rate Limit, cạn quota toàn pool, hoặc timeout/outage hệ thống).
- **Cấm tự ý đảo quyền:** Coordinator tuyệt đối không được tự ý gán Luna High làm worker mặc định cho các task thi công thường quy.

---

## 2. Phòng Ngừa Bẫy Over-engineering Trong Tác Vụ Thiết Bị Farm
> *"Là sao ngày nào t cũng đổi tên mà cứ đi viết lại code đổi tên chi v"*

### A. Triệu chứng Bệnh Over-engineering:
- Mỗi khi nhận lệnh đổi tên/thao tác trên 1 máy farm mới, Coordinator thường có xu hướng copy script ra một file mới (`do_rename_m<ID>.py`) và viết lại bộ unit test tương ứng chỉ để đối phó với tiêu chí chấm điểm Closeout Gate.
- Hậu quả: Làm loãng repo, tốn 10-15 tool calls vô ích của Worker để viết test lặp lại, tăng nguy cơ timeout và gián đoạn vận hành.

### B. Kỷ Luật Thực Thi:
1. Tái sử dụng kịch bản canonical dùng chung (`do_rename.py` hoặc kế thừa script chuẩn của các máy đã chạy thành công như `do_rename_m46.py`).
2. Nếu giao diện TikTok có biến thể (ví dụ tài khoản trống bio bị ẩn nút "Sửa hồ sơ", chỉ hiện `+ Thêm tiểu sử`), xử lý trực tiếp qua state machine chuẩn (`BIO_EDIT` -> lưu bio -> hiện nút `Sửa hồ sơ` -> đổi tên) thay vì tạo mới script cho từng máy.
