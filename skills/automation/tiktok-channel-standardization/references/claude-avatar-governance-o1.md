# Kiến Trúc O(1) Tự Động Thẩm Định Ảnh Avatar TikTok Farm & Phòng Chống Bại Liệt Não Sau Reconnect

## 1. Bản Chất Vấn Đề & Tử Huyệt Của Cơ Chế Hiện Tại
- **Lỗ hổng "Tự cấp vé khống" (`--record-vision`):** Trong `guard_media_vision_gate.py`, cờ `--record-vision` cho phép Coordinator chạy một lệnh terminal để tự ghi bản ghi `SEEN_BY_COORDINATOR_BROWSER_VISION`. Đây là "bảo lãnh mồm", niềm tin bằng 0, tạo điều kiện cho LLM lười biếng: chỉ chạy lệnh để lấy vé `PASS` mà không thực sự nhìn vào ảnh.
- **Hậu quả thực tế:** Coordinator gửi cho User những ảnh avatar thảm họa:
  * Bị số view `849` đè nát nửa mặt.
  * Bị icon tam giác `▷ 7` đè lên góc, người quay lưng không thấy mặt.
  * Đưa nhầm icon game (bình thuốc xanh số 14) làm ảnh tách cà phê.
- **Thách thức:** Cài quá nhiều hook phức tạp thì gây over-engineering, chậm trễ, nghẽn pipeline. Không cài thì LLM sinh tính lười biếng, làm đối phó.

---

## 2. Nguyên Tắc Cốt Lõi: Đừng Bắt LLM Chứng Minh "Đã Nhìn"
> *"Không có cách cơ học nào chứng minh LLM 'đã nhìn' ảnh. Đừng bắt nó chứng minh đã nhìn. Hãy để một công cụ khách quan tự động kiểm tra ảnh, và chỉ công cụ đó mới có quyền cấp vé."*

---

## 3. Kiến Trúc O(1) Tối Giản Cho Avatar Farm (< 0.2s)

### A. Khai tử vĩnh viễn `--record-vision`
- Không cho phép Coordinator tự gõ bất kỳ cờ nào để tự phong receipt `PASS`.
- Receipt chỉ được sinh ra bên trong công cụ kiểm tra tự động sau khi các bài test vật lý thực sự đạt yêu cầu.
- Receipt gắn chặt với mã băm `SHA256` của file ảnh. Đổi ảnh hoặc sửa ảnh là hash đổi, mất vé ngay.

### B. Bộ 3 Phép Thử Vật Lý Tự Động O(1) (< 0.2s)
Một script kiểm tra duy nhất `avatar_check.py <path>` thực hiện 3 bước:

1. **Sửa từ nguồn (Cấm cắt từ screenshot):**
   * Số view `849`, `1.152` và icon tam giác `▷ 7` xuất hiện vì Coordinator lười, đi cắt thumbnail từ screenshot lưới video thay vì mở file video gốc.
   * **Bất biến:** Ảnh avatar BẮT BUỘC phải trích xuất từ file video gốc (`.mp4`) hoặc ảnh gốc có sẵn, TUYỆT ĐỐI CẤM cắt từ ảnh chụp màn hình lưới video.

2. **WinRT OCR trên ảnh crop tròn (chạy < 0.05s):**
   * Crop vùng tròn viền TikTok trước.
   * Chạy WinRT OCR quét vào vùng tròn này.
   * **Quy tắc:** Avatar cá nhân/sản phẩm chuẩn **KHÔNG ĐƯỢC CÓ BẤT KỲ CHỮ SỐ HOẶC KÝ TỰ NÀO**. Nếu OCR phát hiện chữ số (`849`, `1.2K`...) $\rightarrow$ **FAIL cơ học ngay lập tức**, từ chối cấp vé! (Đã tích hợp mã lỗi `DIRTY_AVATAR_EVIDENCE` vào `guard_media_vision_gate.py`).

3. **OpenCV Face Detect Haar Cascade (chạy ~20ms local):**
   * Với kênh nhân vật / cá nhân: Yêu cầu $\ge 1$ khuôn mặt nhìn thẳng nằm ở trung tâm ảnh.
   * Tự động loại bỏ ảnh người quay lưng, ảnh góc nghiêng mất mặt, hoặc ảnh rác đồ vật/game không có người.

---

## 4. Bệnh "Bại Liệt Não" Sau Khi Reconnect / Auto-Resume & Cách Trị Dứt Điểm

### Hiện Tượng:
Sau khi máy tính reboot, hoặc Gateway restart do watchdog/timeout, khi kết nối lại, thay vì tiếp tục làm việc dở dang, Agent lại chào hỏi hành chính:
> *"Phiên làm việc đã được khôi phục thành công... Bạn muốn tiếp tục xử lý nội dung nào tiếp theo?"*
khiến User bức xúc tột cùng (*"Hồi chiều t fix cái auto resume này 1 lần r sao h vẫn bị lại vào hỏi bại liệt não đkm đang làm dở thì làm tiếp hỏi cái lồn. Lí do hỏi mà đéo làm tiếp?"*).

### Căn Nguyên Kỹ Thuật & Bẫy Trôi Code:
1. **Lỗi điều kiện nhánh:** Trong `D:/Taadaa/Hermes/gateway/run.py` (dòng ~19081), `_auto_continue_task` chỉ gán `True` khi `_reason == "restart_interrupted"`. Khi Gateway tự restart (watchdog, timeout), lý do là `"restart_timeout"` hoặc `"shutdown_timeout"`, làm `_auto_continue_task` rơi về `False`.
2. **System Note tiêm ngược chỉ thị bắt hỏi:** Nhánh `else` tiêm System Note bắt LLM phải bỏ việc dở dang và hỏi User (*"Report to the user that the session was restored successfully and ask what they would like to do next. Do NOT re-execute old tool calls..."*).
3. **Bẫy trôi code do uncommitted diff:** Code đã từng sửa buổi chiều nhưng không commit vào git, sau đó bị các subagent/tool git checkout đè ngược lại làm mất code fix.

### Quy Chuẩn Khắc Phục Bắt Buộc (Commit Git `7f04bc84f`):
1. **Mở rộng điều kiện nhận diện task dở dang:**
   ```python
   _auto_continue_task = (not message) and _reason in (
       "restart_interrupted", "restart_timeout", "shutdown_timeout"
   )
   ```
2. **Thay thế System Note thành Lệnh Hành Động Cưỡng Chế:**
   > *"Kiểm tra lại hiện trường môi trường/thiết bị sau khi restart và chủ động tiếp tục thực thi để hoàn thành dứt điểm task đang dở về DONE hoặc BLOCKED kèm bằng chứng thực tế. Do NOT replay old tool calls from the history — re-check the real current state first and issue fresh calls only for what is still unfinished."*
3. **Kỷ luật Git Commit Lõi:** Sửa file lõi Gateway (`gateway/run.py`) bắt buộc `py_compile` và `git commit` ngay lập tức để tránh trôi code qua các session khác.
