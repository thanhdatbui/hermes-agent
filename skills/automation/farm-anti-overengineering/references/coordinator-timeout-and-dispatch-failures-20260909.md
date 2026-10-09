# Coordinator Timeout & Dispatch Failures — Post-Mortem 09/09/2026

## Incident Summary
Phiên xử lý Farm Alert (night-chain-reg-pipeline Phase 2a FAILED: 21/26) mất **hơn 1 tiếng**
cho một bài toán đáng lẽ chỉ cần 10 phút. Tad mắng thẳng: *"Sao xử lý gì tận hơn 1 tiếng v"*
và *"tiếp tục ngu lồn k tuân thủ rule"*.

Claude Opus CLI xác nhận: **4 vi phạm rule bất biến đồng thời**.

---

## Vi phạm 1 — read_file trên log 215MB (timeout 900s)

### Gì đã xảy ra
Coordinator gọi `read_file("D:/Taadaa/Tiktok_Reg/social_reg_log.txt")` mà không kiểm tra
dung lượng trước. File log 215MB, tool cố load và đếm toàn bộ → kẹt cứng đúng 900s timeout.

### Rule bị vi phạm
- **O(1) log inspection**: CẤM đọc log farm > 10MB. BẮT BUỘC dùng `tail`/`inspect_machine`.
- **Cap timeout ≤60s**: Tool call mà im lặng > 2 phút là đã sai từ bước đầu.

### Cách đúng
```bash
# Bước 0 bắt buộc: kiểm tra size trước
ls -lh D:/Taadaa/Tiktok_Reg/social_reg_log.txt
# Nếu > 10MB → chỉ dùng tail
tail -n 200 D:/Taadaa/Tiktok_Reg/social_reg_log.txt
```

---

## Vi phạm 2 — pytest tests/ quét toàn repo (timeout 900s lần 2)

### Gì đã xảy ra
Sau khi Worker sửa code xong, thay vì chạy đúng file test focused (`test_detect_after_continue.py`),
Coordinator chạy `pytest tests/` quét toàn bộ suite. Trong đó có `test_night_chain_pipeline.py`
giả lập subprocess dài → kẹt thêm 900s.

### Rule bị vi phạm
- **Cấm test inflation**: Chỉ chạy đúng file test liên quan, không bao giờ quét suite.
- **Cap timeout ≤60s**: Kẹt lần 2 mà vẫn không học từ lần 1.

### Cách đúng
```bash
# Chỉ chạy file test mới + file test liên quan trực tiếp, với timeout cứng
D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest \
  D:/Taadaa/Tiktok_Reg/tests/test_detect_after_continue.py \
  D:/Taadaa/Tiktok_Reg/tests/test_fill_email_continue_btn.py \
  --timeout=30 -q
```

---

## Vi phạm 3 — Dispatch 4–5 lượt Worker (analysis paralysis loop)

### Gì đã xảy ra
- Lượt 1 & 2: Worker sa đà phân tích/kế hoạch, chạm trần 15 tool calls mà chưa sửa 1 dòng.
  → **Lỗi thuộc về Coordinator**: prompt không đóng gói sẵn diff/hướng dẫn.
- Lượt 3 & 4: Worker vướng `autouse` fixture mock và ambiguous header openpyxl trong test cũ.
  → **Lỗi thuộc về Coordinator**: không rà soát môi trường test trước khi dispatch.
- Lượt 5: Phải tách sang file test mới (`test_detect_after_continue.py`) để tránh fixture conflict.

### Rule bị vi phạm
- **Dispatch contract**: Prompt Worker PHẢI chứa: (a) đường dẫn tuyệt đối, (b) diff định hướng
  sẵn, (c) test command chính xác, (d) budget nghiêm ngặt. Cấm để Worker tự mò.
- Worker "tự mò" = **lỗi của Coordinator**, không phải lỗi Worker.

### Cách đúng
```
Dispatch prompt phải có:
- ABSOLUTE FILE PATHS chính xác từng file cần sửa
- Diff/old_string/new_string sẵn sàng áp dụng
- Test command exact: "D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest [FILE] --timeout=30"
- Giới hạn: "Complete all in <= 6 tool calls!"
- Cảnh báo pitfall nếu có conflict môi trường
```

---

## Tóm tắt thời gian lãng phí
| Nguyên nhân | Thời gian |
|---|---|
| read_file 215MB timeout | ~15 phút |
| pytest tests/ timeout | ~15 phút |
| Dispatch 4-5 lượt Worker | ~30 phút |
| **Tổng** | **~60 phút cho bài toán 10 phút** |

---

## 3 Phản xạ Coordinator PHẢI có (từ Claude Opus audit)
1. **Trước mọi lệnh dài**: gắn timeout ≤60s. Im lặng >2m = đã sai.
2. **Log = luôn `tail`**, không bao giờ `read_file` nguyên file. Kiểm size trước.
3. **Test = luôn chỉ đích danh 1-2 file <30s**, không bao giờ `pytest tests/`.
4. **Dispatch = prompt phải chứa diff + file + test command**. Worker "tự mò" = lỗi Coordinator.
