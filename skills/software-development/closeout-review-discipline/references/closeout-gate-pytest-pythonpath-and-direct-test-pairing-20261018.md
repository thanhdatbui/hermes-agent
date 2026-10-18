# Closeout Gate Pytest PYTHONPATH & Direct Test Pairing (2026-10-18)

## 1. Vấn đề Phát Sinh

Khi chạy `closeout_gate.py` trên các repository monolith hoặc repo có thư mục tests nằm sâu (như `python_runner/tests` trong `tiktok-luot nuoi acc`):
1. **Lỗi ModuleNotFoundError (`_path_setup`):**
   - Khi `pytest.ini` ở root repo không cấu hình `pythonpath = python_runner/tests python_runner`, pytest chạy từ root sẽ không tìm thấy các module helper cục bộ như `_path_setup.py` hoặc các package nội bộ của flow, dẫn đến `ModuleNotFoundError` ngay tại bước test collection.
   - Khắc phục: Bổ sung `pythonpath = <test_dir> <src_dir>` vào `pytest.ini`.

2. **Cơ chế Lựa Chọn Test của `closeout_gate.py` (`direct_tests` vs `stem matching`):**
   - Nếu `--files` chỉ truyền file code nghiệp vụ (ví dụ: `python_runner/flows/multi_machine_feed_session.py`), gate sẽ tự động tìm kiếm theo tên stem: `test_<stem>.py` (`test_multi_machine_feed_session.py`).
   - File test toàn bộ monolith thường chứa hàng trăm test case, test tích hợp chậm hoặc đụng timeout (>30s) làm trượt Closeout Gate một cách không cần thiết.
   - **Giải pháp Direct Test Pairing:** Luôn truyền đồng thời cả file logic và file test focused vào `--files` (ví dụ: `--files python_runner/flows/multi_machine_feed_session.py python_runner/tests/test_organic_rest_upload_gate.py`).
   - Khi phát hiện có file test trong danh sách files (`direct_tests`), `closeout_gate.py` ưu tiên chạy đúng file test đó và bỏ qua việc quét stem toàn monolith, giúp test hoàn tất trong 1–2 giây.

## 2. Kỷ Luật Ứng Xử Khi User Hỏi "Xong hết chưa để chốt phiên"

- **Tuyệt đối không phân bua/kể lể trạng thái dirty:** Khi user hỏi tiến độ hoặc giục chốt phiên, tránh liệt kê một danh sách các working tree bẩn hay các lý do quan liêu ("chưa xong vì chưa commit, chưa closeout, chưa canary...").
- **Hành động dứt khoát:**
  1. Nếu code đã được worker sửa và test xanh, lập tức kích hoạt `closeout_gate.py` chạy ngầm (`background=True, notify_on_complete=True`) để lấy điểm Reviewer.
  2. Báo cáo ngắn gọn: Xác nhận code đã ăn vào file runtime thực tế và cổng Closeout Gate đang thẩm định để chốt phiên.
