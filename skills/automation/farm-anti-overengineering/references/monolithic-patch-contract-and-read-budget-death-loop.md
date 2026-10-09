# Monolithic Patch Contract & Read Budget Death Loop Prevention (11/09/2026)

Nguồn: Phân tích sự cố xử lý 42 phút (Alert Máy 25 - TikTok GO & Profile Mismatch) — Claude Opus CLI audit.

---

## 1. Hiện tượng "Read Budget Death Loop" (Bài học đắt giá Máy 25)

### Triệu chứng thực tế:
- Phiên chat Telegram bị treo suốt **42 phút** ở trạng thái `⚙️ Working — 42 min — iteration 31/200, delegate_task`.
- Người dùng bức xúc phản hồi: *"Clg lâu thế. Mày lại đi grep quét cả ổ đĩa phải k"*, *"Tool call v k đủ đọc context à"*.

### Phân tích Root Cause từ Claude Opus CLI:
- File `feed_swipe_smoke.py` của repo `tiktok-luot nuoi acc` dài tới **22.260 dòng (~630 KB)**.
- Coordinator tìm ra nguyên nhân rất nhanh, nhưng khi dispatch lại ném một goal mở: *"Sửa lỗi profile verification mismatch và xử lý thẻ TikTok GO trong repo tiktok-luot nuoi acc"*.
- Worker subagent nhận goal điều tra buộc phải tự định vị lại từ đầu. Nó dùng `read_file` phân trang liên tiếp 35 lần chỉ để dò tìm cấu trúc file và cạn kiệt toàn bộ quota tool calls (35/35) mà **không sửa được bất kỳ file nào** (`0 files modified`).
- Coordinator tiếp tục dispatch worker lần 2 với prompt tương tự, lặp lại chu kỳ đốt context.
- Chỉ đến khi Coordinator trích sẵn khối `old_string -> new_string` và cấm worker đọc file, worker mới hoàn thành trong **5 phút với 15 calls**.

**Phán quyết của Claude Opus:**
> *"Lỗi không nằm ở năng lực Worker, mà nằm ở Coordinator giao việc sai bản chất. Trên file monolithic lớn (> 1.500 dòng), giao goal mở là bản án tử hình cho quota tool calls của subagent."*

---

## 2. Kỷ luật Patch Contract bắt buộc cho File Monolithic

### Quy tắc bất biến:
1. **CẤM TUYỆT ĐỐI dispatch goal mở ("tự tìm", "tự phân tích") trên file > 1.500 dòng.**
2. **Coordinator BẮT BUỘC có sẵn `old_string` và `new_string` trước khi dispatch.** Chưa có diff = chưa dispatch.
3. **Worker chỉ đóng vai trò "cánh tay robot áp diff + chạy test focused"** với budget cực nhỏ ($\le 8$ tool calls).

### Checklist soạn Patch Contract cho Coordinator:
- **Định vị O(1):** Dùng `grep -n` để lấy số dòng và đọc đúng 20–40 dòng quanh điểm lỗi (không đọc toàn file).
- **Uniqueness Check (Xác nhận tính duy nhất):** Bắt buộc chạy `grep -c` cho `old_string` để bảo đảm **count == 1**. Trong file 22k dòng, nếu `old_string` không duy nhất hoặc lệch whitespace, patch tool sẽ fail và worker không đủ budget để tự gỡ.
- **Cấu trúc Contract gửi Worker:**
  ```text
  BẠN LÀ WORKER THỰC THI ÁP DIFF.
  CẤM ĐỌC LAN MAN, CẤM PHÂN TRANG TÌM HIỂU.
  Budget: tối đa 8 tool calls.

  1. FILE: D:\Taadaa\...\<file.py>
  2. OLD_STRING (duy nhất, grep -c == 1):
     ```python
     <10-15 dòng code cũ có neo ngữ cảnh>
     ```
  3. NEW_STRING:
     ```python
     <đoạn code mới thay thế>
     ```
  4. FOCUSED_TEST:
     PYTHONPATH="..." python -m unittest <đúng 1 file test>
  ```

---

## 3. Khóa "Read Budget" của Worker (Worker Constraints)

Trong prompt dispatch worker áp patch:
- **Khóa số lần đọc:** Quy định cứng worker chỉ được gọi tối đa **2 lần `read_file`** (chỉ dùng để check cú pháp syntax quanh điểm thay đổi nếu tool patch báo lỗi).
- **Fail-Fast Trigger:** Nếu `old_string` không match sau 2 lần thử, worker PHẢI DỪNG LẬP TỨC và báo về Coordinator kèm lý do, CẤM tự ý đọc phân trang dò tìm khắp file.

---

## 4. Escape Hatch: Investigation Mode

- Quy tắc Patch Contract chuyển trách nhiệm định vị từ worker sang coordinator. Tuy nhiên, nếu gặp bug phức tạp mà sau **2 phút (B1)** Coordinator không thể định vị được dòng lỗi:
  + **CẤM đoán mò hoặc soạn patch mù.**
  + Chuyển sang **Investigation Mode**: Dispatch 1 subagent chuyên trách điều tra (role=leaf) nhưng **cô lập phạm vi**: chỉ được dump stacktrace, probe runtime hoặc reproduce qua test tối giản, có budget trần 15 calls.
  + Khi tìm ra vị trí chính xác, quay lại chu trình Patch Contract chuẩn.

---

## 5. Rollback B5 khi Live Canary Thất Bại

- Trong playbook 5 bước, nếu Canary test ở **B4 FAIL**:
  + **B5 (Rollback khẩn cấp):** Ngay lập tức revert patch (`git checkout -- <file>`), trả môi trường farm về trạng thái an toàn.
  + Mở lại alert, lưu toàn bộ screencap / log artifact hiện trường của lần canary fail vào thư mục run để phân tích.
  + Tuyệt đối không để lại code hỏng / chưa kiểm chứng trên farm 80–160 máy đang chạy nền.

---

## 6. Playbook 5 Bước Farm Alert Chuẩn Hóa ($\le 12$ Phút - 1 Worker Duy Nhất)

| Bước | Thời gian | Vai trò | Hành động |
| :--- | :--- | :--- | :--- |
| **B0** | 90s | Coordinator | Inspect hiện trường O(1): `inspect_machine.py <N>`, dump XML / screencap. |
| **B1** | 2 phút | Coordinator | `grep -n` định vị hàm lỗi, xác nhận `grep -c == 1`, trích `old_string` 10-15 dòng. |
| **B2** | 2 phút | Coordinator | Soạn `new_string` xử lý bug triệt để + xác định lệnh focused unit test. |
| **B3** | 4 phút | Worker duy nhất | Dispatch 1 Worker áp patch contract + chạy focused test (Budget $\le 8$ calls). |
| **B4** | 2 phút | Coordinator | Chạy Live Canary 2 swipes trên máy farm (`run-feed-session.ps1 ...`), verify về Launcher & nhả lock. *(Nếu fail: kích hoạt B5 Rollback)*. |
