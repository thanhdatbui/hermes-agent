# Photo Picker 3-Col Geometry, Isolated LLM Vision Judge & Anti-Ad-hoc Script Discipline (17/10/2026)

## 1. Bản chất Sự cố Thực tế (Incident Post-Mortem)

Trong phiên chuẩn hoá avatar Máy 34 Slot 6 (`@yobi1965`), Coordinator liên tục vi phạm nghiêm trọng kỷ luật farm:
1. **Bốc nhầm và gửi ảnh dính sticker rác**: Cắt ảnh từ video gốc dính sticker bài tập hồng `"20 lần/ngày"`. Coordinator không chạy `ocr_tool.py` mà chỉ nhìn lướt qua bằng vision mớm lời, tự nhận là "cô gái tập yoga hai tay đưa lên" rồi gửi cho User. User lập tức chất vấn nặng nề: *"Cái địt con mẹ mày mày có dùng win rt ocr đọc hình trc khi gửi tao k v con chó"*.
2. **Cắt cụt đầu (Headless Crop)**: Crop sai lệch trục $y$, mất sạch đỉnh đầu, mắt, mũi, miệng, chỉ còn cằm và cổ, phía đáy dính vụn chữ đỏ.
3. **Ảo giác avatar đã đổi (Stale Avatar Affirmation)**: Máy từ sáng đến chiều vẫn kẹt ảnh phong cảnh đồi cát sa mạc màu vàng cũ. Coordinator liên tục claim thành công mà không nhận ra TikTok app bị kẹt upload CDN và chưa hề lưu ảnh mới. User nổi giận: *"tao đã bảo đổi cái ava khác làm từ sáng tới h vẫn y cái ava cũ là sao đụ mẹ mày có bị điên k"*.
4. **Đẻ script ad-hoc vụn vặt (`do_save_avatar_m34.py`)**: Tự ý viết script ad-hoc tap ADB thay vì dùng canonical runner `run_avatar_batch_3accs.py`. Script tự chế không xử lý được lưới picker 3 cột, không bỏ tick "Đăng ảnh này lên Nhật ký" (làm kẹt pipeline đăng Story), và không có cơ chế đối soát kết quả. User chấn chỉnh: *"Và tại sao lại có cái script lồn gì avatar 34.py? Tao đã thiết kế script upload ava r mà?"*.

---

## 2. Vì sao So khớp Text Thô trên WinRT OCR Thất bại?

Claude Sonnet 5.5 chỉ rõ 4 lỗ hổng cốt tử khi chỉ dựa vào regex/string-match trên WinRT OCR:
1. **Hỏng dấu và méo mó ký tự:** Tiếng Việt trên giao diện điện thoại thường bị OCR phân tách sai (ví dụ `20)la` thay vì `2025`, `Bi quyét trånh vöng lung`). Regex cứng sẽ báo FAIL oan hoặc lọt lưới các mảnh vụn.
2. **Văn bản bị vỡ mảnh rời rạc:** WinRT OCR cắt theo block từ/dòng. Một thông báo lỗi dài có thể bị ngắt thành nhiều đoạn nhỏ rải rác, không có chuỗi nào khớp trọn vẹn.
3. **Thiếu ngữ cảnh ngữ nghĩa:** OCR không cho biết chuỗi text đó là nhãn nút bấm, tiêu đề trang, hay pop-up lỗi. Cùng một chữ `"Follow"` có thể xuất hiện trên nút bấm, trên thanh tiêu đề, hoặc trong danh sách gợi ý.
4. **MÙ HOÀN TOÀN THÔNG TIN THỊ GIÁC (Visual Blindness):** OCR chỉ đọc ký tự. Nó **hoàn toàn không thể biết** bên trong vòng tròn avatar là cô gái tập yoga, hay chậu cây kim tiền, hay phong cảnh đồi cát, hay mảng màu mờ bokeh. Dùng OCR đơn thuần để nghiệm thu avatar là sai lầm về mặt bản chất kỹ thuật.

👉 **Quy chuẩn bất biến:** WinRT OCR chỉ là **tín hiệu phụ (auxiliary raw signal)**. Quyết định nghiệm thu hình ảnh bắt buộc phải do **lớp LLM Vision đọc ảnh** đưa ra.

---

## 3. Kiến trúc Visual Evidence Gate v2 (Mechanical Pre-Send + Isolated LLM Judge)

Đã thi công hoàn chỉnh vào hệ thống:
- `D:/Taadaa/tools/visual_judge.py`: Nhận ảnh, chạy WinRT OCR, gọi model Vision qua OmniRoute `:20129` (`ag-gemini-pool-3` / `auto/best-vision`) với prompt trung tính không thiên vị, xuất file bằng chứng `evidence/verdict_<sha256>.json`.
- `D:/Taadaa/tools/verify_media_gate.py`: Chốt chặn tiền kiểm. Quét mọi thẻ `MEDIA:<path>`. Nếu ảnh chưa có verdict `PASS` hợp lệ trong 300s -> gỡ bỏ thẻ `MEDIA:`, gắn tiền tố `[UNVERIFIED_VISUAL_EVIDENCE - REJECTED]` và từ chối gửi. Đạt 12/12 unit tests passed.

---

## 4. Kỷ luật Cấm Đẻ Script Ad-hoc (The Anti-Ad-hoc Invariant)

Khi gặp khó khăn trong quá trình thao tác farm (ví dụ: bốc nhầm ảnh, mạng lag, app kẹt):
1. **CẤM TUYỆT ĐỐI** tự tiện viết script ad-hoc (`do_save_avatar_*.py`, `avatar_34.py`, `test_tap_*.py`) để tap tay ADB thay cho việc sửa code chuẩn.
2. **BẮT BUỘC REUSE > EXTEND canonical tools:**
   - Đổi avatar: `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <N> --machine <M>`.
   - Ghim/Nhả ghim: `python D:/Taadaa/tools/pin_top_videos.py --machine <M>`.
   - Lấy hiện trường: `python D:/Taadaa/tools/inspect_machine.py <M>`.
3. Nếu canonical tool gặp lỗi (ví dụ MediaStore cache rác, picker 3 cột):
   - Phân vai: **Claude CLI (Sonnet 5.5)** thiết kế bản vá kiến trúc (`--role planner`), **Worker / Haiku CLI** thi công code và unit test, sau đó chạy lại chính canonical tool đó.
   - Cấm Coordinator tự tiện biến mình thành công nhân gõ script tap màn hình ad-hoc!
