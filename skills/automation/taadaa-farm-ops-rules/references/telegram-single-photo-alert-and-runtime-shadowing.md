# Telegram Single-Message Photo Alert & Runtime Module Shadowing Pitfalls

## 1. Telegram 1024-Character Photo Caption Limit & Single-Message Alert
- **Giới hạn kỹ thuật Telegram API:**
  - `sendMessage` (tin nhắn chữ): Tối đa 4,096 ký tự.
  - `sendPhoto` (tin nhắn kèm ảnh): Caption chỉ cho phép tối đa **1,024 ký tự**. Vượt quá 1,024 ký tự sẽ nhận HTTP 400 `MEDIA_CAPTION_TOO_LONG`.
- **Yêu cầu của người vận hành:**
  - **TRỌN GÓI 1 TIN NHẮN DUY NHẤT:** Tuyệt đối không tách thành 2 tin nhắn (1 ảnh tóm tắt + 1 text 5 bước) làm loãng chat và phân mảnh thông tin cứu hộ.
  - Phải chứa cả ảnh hiện trường đóng dấu Banner Đỏ số máy `[MAY N] - HH:MM:SS DD/MM` và nội dung 5 bước recovery tóm gọn.
  - **BẮT BUỘC TIẾNG VIỆT CÓ DẤU ĐẦY ĐỦ (User Feedback 05/09/2026):** Tuyệt đối CẤM gửi bản draft không dấu ra ngoài hoặc gõ không dấu để đếm ký tự. Chuỗi caption phải soạn thảo bằng tiếng Việt chuẩn ngữ pháp, có dấu đầy đủ và đếm ký tự trực tiếp trên bản có dấu để đảm bảo <= 1024 ký tự.
  - **CẤM DÙNG LATEX MATH KHI GỬI TIN NHẮN TELEGRAM (User Feedback 05/09/2026):** Tuyệt đối CẤM dùng cú pháp LaTeX math như `$\rightarrow$`, `$\le$`, `$ ... $` khi gửi tin nhắn cho user trên Telegram. Client Telegram không render LaTeX math mà hiển thị nguyên văn chuỗi thô rất khó đọc. BẮT BUỘC dùng ký tự Unicode thật (`→`, `<=`) hoặc ký hiệu text thuần (`->`).
- **Giải pháp chuẩn:**
  - Tối ưu chuỗi caption tổng thể $\le 1000$ ký tự.
  - Bắt buộc bọc qua hàm `_safe_truncate_html(caption, 1024)` để tự động đóng các thẻ HTML (`<b>`, `<code>`, `<pre>`) và entity `&...;`, ngăn vỡ cú pháp parse của Telegram.
  - Nếu gửi ảnh gặp sự cố mạng (upload photo thất bại), fallback gửi **đúng 1 tin nhắn text duy nhất** chứa toàn bộ nội dung.

---

## 2. Python Site-Packages Static Directory vs Editable `.pth` Shadowing
- **Hiện tượng lỗi:**
  - Sửa code trong repo `automation-core/src/automation_core/alerts.py` nhưng khi chạy farm vẫn bị dính hành vi cũ (ví dụ: vẫn bắn 2 tin nhắn cảnh báo).
- **Nguyên nhân cốt lõi:**
  1. **Thư mục tĩnh đè `.pth`:** Trong môi trường virtualenv (`python-envs/automation/Lib/site-packages/`), nếu tồn tại đồng thời thư mục vật lý tĩnh `automation_core/` (cài từ wheel/bdist trước đó) và file editable link `__editable__.automation_core-*.pth`, **Python trên Windows luôn ưu tiên nạp từ thư mục vật lý trước**.
  2. **Tiến trình chạy nền giữ code cũ trong RAM:** Các tiến trình daemon/runner dài (như `run_tiktok.py`, `scripts.tiktok_workflow`, feed sessions) nạp module vào `sys.modules` lúc khởi động. Dù file trên đĩa đã được sửa, tiến trình cũ trong bộ nhớ vẫn chạy logic cũ cho đến khi tiến trình đó kết thúc hoặc được khởi động lại.
- **Quy trình kiểm tra & xử lý bắt buộc:**
  1. Kiểm tra xuất xứ import:
     ```python
     python -c "import automation_core.alerts as a; print(a.__file__)"
     ```
     Phải trỏ về `D:\Taadaa\automation-core\src\automation_core\alerts.py`.
  2. Quét dọn sạch sẽ thư mục tĩnh trong `site-packages`: Xóa hẳn thư mục `site-packages/automation_core` và re-run `pip install -e .`.
  3. Kiểm tra mốc thời gian PID của tiến trình chạy farm:
     ```python
     import psutil, datetime
     # Đối chiếu create_time của tiến trình với thời điểm sửa code/xóa site-packages
     ```
     Nếu tiến trình start trước thời điểm fix, alert sinh ra từ tiến trình đó là do nạp code cũ trong RAM, không phải do code trên đĩa chưa fix.
