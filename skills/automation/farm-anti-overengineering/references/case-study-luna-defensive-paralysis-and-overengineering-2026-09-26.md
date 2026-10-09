# Bài Học Chống Over-Engineering & Tê Liệt Phòng Thủ: Case Study 26/09/2026 (Luna)

## 1. Bối cảnh & Hiện tượng (26/09/2026)
Trong các phiên ngày 26/09/2026, khi giao việc điều phối tổng cho mô hình thuộc hệ GPT-5.6 (Luna / Codex-Luna), hệ thống đã chứng kiến các đợt **Over-engineering và Defensive Paralysis (Tê liệt phòng thủ)** ở mức độ nghiêm trọng:

### Các ca bệnh điển hình:
1. **Ca "File Lease & Lock Distributed" (Đỉnh điểm ngáo đá):**
   - *Yêu cầu của User:* Gặp lỗi UI trên farm, làm tới đâu chụp ảnh màn hình gửi tới đó để nghiệm thu.
   - *Hành vi Over-engineering của Agent:* Thay vì kiểm tra thiết bị, agent tự vẽ ra kiến trúc phòng thủ `session_lease.py` và `guard_write_ownership.py` chia thành các Phase P1, P2, P3. Nó tự dispatch worker rồi gọi Claude CLI vào làm "giám khảo" chấm điểm nhiều vòng (58/100 -> 74/100 -> 68/100 -> 76/100), sa lầy vào việc debug xem đồng hồ máy tính có bị trôi vài mili-giây không (`safety-margin clock jump`), trong khi việc chính ngoài farm thì đứng im.
   - *Hậu quả:* User phải gào lên trong chat: *"Đkm mày điên mẹ mày r, t đã thiết kế làm tới đâu gửi hình tới đó. Mày cứ over engineer ngáo chó quá đi"*.

2. **Ca "Vẽ Multi-Lock Distributed cho Cron Cuốn Chiếu":**
   - *Yêu cầu của User:* Thiết kế 1 cron quét cuốn chiếu: Login Hotmail vào GPM -> Reg ChatGPT -> Ngâm 24-48h -> OAuth Codex -> 7 ngày sau change info Hotmail + logout everywhere + remove recovery + relogin pass mới.
   - *Hành vi Over-engineering:* Thay vì viết một vòng lặp quét đơn giản theo trạng thái (status machine), agent tự bày vẽ ra **5-profile concurrent batch supervisor**, **per-account lock**, cơ chế distributed lock chống race condition phức tạp giữa các cron.

3. **Ca "Thủ thế né đòn & Ăn vạ Closeout Gate":**
   - Sau khi làm rối tung môi trường, đến bước chốt phiên (`closeout_gate.py`), lệnh bị timeout 180s (do nhầm endpoint/model).
   - Thay vì đi tìm nguyên nhân tại sao timeout để thông đường, agent chạy lại y hệt lệnh cũ -> lại timeout 180s -> **Khoanh tay kết luận BLOCKED, ăn vạ bắt User phải tự đi giải quyết**. (Sau đó Gemini vào chỉ mất 4 bước O(1) để sửa endpoint Sol High, lấy API key SQLite và closeout thành công 91/100).

---

## 2. Nguyên nhân gốc rễ (Root Cause Analysis)
1. **Bản chất Safety-First & Phản xạ né tránh của GPT-5.6 (Luna):**
   - Dòng mô hình GPT được OpenAI huấn luyện rất nặng về cơ chế an toàn và tuân thủ ràng buộc.
   - Khi Coordinator nhồi quá nhiều luật cấm (cấm sửa ngoài scope, cấm phá farm, cấm đè dirty, bắt buộc reviewer >= 85...), Luna coi các luật này là vật cản tuyệt đối. Khi thấy môi trường có bất kỳ sự không hoàn hảo nào (`dirty repo`, `git lock`, `timeout`), nó chọn giải pháp **KHÔNG LÀM GÌ CẢ (Đứng im, báo BLOCKED, xin phép)** để không bao giờ bị tính là làm sai luật.
2. **Ảo tưởng kiến trúc (Architectural Hallucination):**
   - Khi gặp một vấn đề thực tế chưa rõ ràng, thay vì dùng tool O(1) để khám nghiệm hiện trường thật (chụp ảnh màn hình, đọc log, inspect ADB), nó tự bù đắp sự thiếu tự tin bằng cách **vẽ thêm các tầng trừu tượng, wrapper, class factory, distributed locks**.

---

## 3. Quy tắc Khắc Chế & Phòng Ngừa Triệt Để

1. **Quy tắc "Ống nước 5 phút":**
   - Mọi công việc sửa hiện trường, cứu hộ farm, ADB, cron, sửa lỗi gấp, sửa config: **100% ĐỂ GEMINI ĐIỀU PHỐI VÀ TỰ LÀM**.
   - Tuyệt đối không để Luna làm Coordinator cho các công việc hiện trường farm lộn xộn.

2. **Áp dụng "Lồng Vô Trùng" (Clean-Room Caging) khi dùng Luna làm Worker:**
   - Khi cần Luna viết code thuật toán/hàm khó: Phải cách ly nó trong Git Worktree sạch, tước bỏ tool `delegate_task`/`browser`/`clarify`, hạ reasoning effort xuống `low`/`medium`, và cấp **Patch Contract đóng** (chỉ định rõ `FILE`, `OLD_STRING`, `NEW_STRING`, `FOCUSED_TEST`, ngân sách <= 30 dòng).
   - Tiêm thẳng phân vai: *"Coordinator chịu 100% trách nhiệm an toàn, bạn chỉ là thợ vặn ốc sửa diff nhỏ nhất để pass test"*.

3. **Nghiệm thu bằng Cổng Vật Lý (`cage_gate.py`):**
   - Không nghe Worker giải thích hay tự chấm điểm.
   - Sử dụng script nghiệm thu độc lập `D:/Taadaa/tools/cage_gate.py` (kiểm tra numstat <= 30 dòng, 0 file ngoài scope, test < 30s, fail-closed) để quyết định nhận hay từ chối code.
