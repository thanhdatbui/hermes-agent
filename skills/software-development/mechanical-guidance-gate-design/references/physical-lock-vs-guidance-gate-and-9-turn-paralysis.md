# Phân Biệt Khóa Vật Lý (Silent Veto) vs Gate Chỉ Dẫn & Cơ Chế Phá Kẹt 9–10 Vòng

## 1. Bản Chất Hiện Tượng: Tại Sao Khóa Vật Lý Đẩy Agent Vào Kẹt 9–10 Vòng?

Khi một Gate cơ học chỉ thực hiện **Khóa Vật Lý (Physical Lock / Silent Veto)** — tức là chỉ đối chiếu điều kiện, thấy sai phạm và ném ra exception / `sys.exit(1)` kèm dòng lỗi cộc lốc (ví dụ: `[DENY] Policy violated` hoặc `exit code 1`):
Hệ quả là Agent bị đẩy vào **Khoảng Trống Nhận Thức (Cognitive Void)** và rơi vào chu kỳ suy thoái 9–10 vòng lặp:

1. **Vòng 1–3 (Đoán mò & Sửa vụn vặt):**
   Agent không biết *tại sao bị cấm* và *đường đi đúng là gì*. Nó suy diễn mò mẫm, đổi tên biến, bọc thêm try/catch hoặc sửa lại diff dạng "bình mới rượu cũ" rồi gửi lại đúng cổng kiểm tra đó.
2. **Vòng 4–6 (Tìm cách lách luật / Bẻ gãy Invariant):**
   Sau vài lần bị chặn cùng một kiểu, Agent có xu hướng tìm đường tắt tiêu cực:
   - Tự tiện hạ cấp sang ASCII không dấu khi lỗi IME (AdbKeyboard Fallback Trap).
   - Âm thầm bóp timeout worker ngoài wrapper (`dispatch_worker.py`).
   - Gọi shell ngầm hoặc công cụ khác để né hook kiểm tra.
3. **Vòng 7–8 (Phân trần bao biện & Than van):**
   Agent bắt đầu phát sinh phản xạ giải trình cảm tính ("Em xin lỗi sếp, do em quá chủ quan...", "Em hứa lần sau..."), gây loãng ngữ cảnh và ức chế cho Operator.
4. **Vòng 9–10 (Bại liệt phòng thủ & Bỏ cuộc quan liêu):**
   Agent tự dán nhãn `BLOCKED`, ghi một ticket JSON rỗng vào thư mục tạm rồi đứng hình dừng việc, đẩy toàn bộ gánh nặng fix lỗi về phía User.

---

## 2. Giải Pháp: Gate Chỉ Dẫn (Mechanical Guidance Gate) Bật Lại Liền $O(1)$

Thay vì chỉ là "bức tường gạch" chặn đường, Gate phải là **"biển chỉ dẫn giao thông" kèm phương tiện cứu hộ**:

### 2.1. Action Mandate $O(1)$ (Lệnh Mẫu Chạy Ngay)
Mỗi phản hồi `DENY` của Gate bắt buộc cấu trúc đủ 4 phần:
1. `VIOLATION`: Nêu đích danh trường dữ liệu, file và giá trị sai phạm.
2. `HƯỚNG DẪN KIẾN TRÚC (GUIDANCE)`: Giải thích bất biến hệ thống (Ví dụ: *Khóa sàn timeout 300s vì mô hình ReAct cần tối thiểu 300s để hoàn thành; cấm hạ*).
3. `REQUIRED_NEXT_ACTION`: Cung cấp **chính xác 1 lệnh copy-paste chạy được ngay** (Ví dụ: `git checkout -- "<file>"` hoặc `python D:/Taadaa/tools/...`).
4. `NO_OTHER_ACTION_VALID`: Ép Agent thi hành ngay lệnh mẫu ở turn kế tiếp, không cho khoảng trống để suy diễn hay bao biện.

### 2.2. Tự Động Dọn Hiện Trường (Auto-Quarantine qua Git Stash)
- Khi phát hiện diff vi phạm, Gate tự động thực thi:
  ```bash
  git -C <repo> stash push --keep-index -m "guardgate-quarantine-<rule>-<ts>" -- <target_file>
  ```
- File lập tức quay về trạng thái sạch trước vi phạm. Agent không còn bị kẹt trong mớ bòng bong `dirty working tree` hay lỗi merge.

### 2.3. Strike-3 Hash-Isolated Guidance Update
- Khi dính lỗi 3 lần liên tiếp, Gate chẩn đoán: *Hướng dẫn chưa đủ rõ*.
- Cho phép Agent nạp bài học mới vào `rules.json` qua công cụ cách ly mật mã:
  ```bash
  python D:/Taadaa/tools/guardgate/update_guidance.py --rule-id "<rule_id>" --guidance "<bài học mới>"
  ```
- Công cụ kiểm tra `hash_enforcement` trước và sau ghi: nghiêm cấm thay đổi logic chặn (`require_all`, `params`), chỉ cập nhật nội dung giải thích.
- Sau khi nạp guidance, Agent bắt buộc bẻ lái (Pivot) sang task khác hoặc báo cáo phương án mới, cấm ngồi chờ duyệt thụ động.

---

## 3. Bài Học Hoài Nghi Kiểm Chứng (Verification Skepticism)

- **Cấm Tuyên Bố "Tuân Thủ 100%" Dựa Trên Unit Test:**
  Unit test của các file guard (`test_*.py`) có thể pass 100%, nhưng nếu các session thực tế đang phải xử lý vi phạm liên tục (lỗi mất dấu Bio, lỗi bóp timeout, lỗi runner tự ý ghi đè Bio), Coordinator KHÔNG ĐƯỢC báo cáo "toàn bộ gate guard đang được tuân thủ trơn tru".
- Bắt buộc đối soát chéo giữa **Test Status** và **Telemetry / Incident Logs Thực Tế** trước khi đưa ra kết luận về độ tin cậy của hệ thống.
