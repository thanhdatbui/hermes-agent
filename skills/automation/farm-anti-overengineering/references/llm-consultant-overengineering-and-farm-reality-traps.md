# LLM Consultant Overengineering & Farm Reality Traps

**Ngày cập nhật:** 25/09/2026
**Bối cảnh:** Khi tham vấn ý kiến các LLM cố vấn kiến trúc cấp cao (Claude CLI, Sol Auditor / GPT-5.6), các mô hình này thường mắc bệnh lý thuyết hóa vấn đề, tự sáng tác các cơ chế bảo vệ quá mức (hyper-protective / over-engineered) gây tê liệt hoặc tăng gánh nặng thủ công cho Phone Farm.

---

## 1. BẪY "QUARANTINE BẤT TỬ" & BẮT USER KIỂM TRA BẰNG TAY (MANUAL REVIEW)

* **Hiện tượng của LLM:** Thấy video mới đăng bị 0-view hoặc vài view, LLM lập tức coi là "nguy hiểm / shadowban" và đề xuất đưa nick vào trạng thái `QUARANTINE`, dừng đăng bài hoàn toàn và bắt người vận hành phải vào kiểm tra thủ công (`manual_release`).
* **Thực tế Farm Taadaa:**
  - Video mới up lên TikTok chuyện bị 0-view hoặc vài view do trễ lập chỉ mục (delayed indexing), kẹt hàng đợi phân phối là chuyện bình thường hàng ngày.
  - Farm vận hành hàng trăm tài khoản trên hàng chục máy điện thoại thật, **tuyệt đối không bao giờ bắt user đi kiểm tra tay từng nick**.
  - **Quy tắc:** CẤM cơ chế Quarantine dừng đăng vì 0-view. Nick flop/0-view cứ để automation chạy ở nhịp thường (có xen kẽ ngày dưỡng sinh 1/3), thuật toán tự điều chỉnh.

---

## 2. BẪY "KHÓA 1 CHIỀU KHI FARM CÓ BIẾN" (ONE-DIRECTION ESCALATION FREEZE)

* **Hiện tượng của LLM:** Tự nghĩ ra các cơ chế lý thuyết phân tán phức tạp như "nếu >30% farm sụt giảm chỉ số thì đóng băng toàn bộ chiều chuyển trạng thái".
* **Thực tế Farm Taadaa:**
  - Gây phức tạp hóa code không cần thiết, dễ tạo dead-lock logic khi có biến động dữ liệu hoặc bảo trì proxy.
  - **Quy tắc:** CẤM đưa các khái niệm trừu tượng, viễn vông vào code trừ khi có yêu cầu bài toán cụ thể và chỉ thị từ User.

---

## 3. HIỂU SAI THUẬT NGỮ DOMAIN: "DƯỠNG SINH" (ORGANIC REST)

* **Hiểu lầm của LLM:** LLM tưởng "dưỡng sinh" là hành động *đi lướt feed*, và tưởng "bỏ dưỡng sinh" cho nick cắn đề xuất là *cắt luôn lướt feed để chỉ nhảy vào đăng video* $\to$ la lên là "lộ pattern bot".
* **Định nghĩa chuẩn của Farm Taadaa:**
  - **LƯỚT FEED LÀ BẤT BIẾN 100%:** MỌI nick khi vào ca nuôi ĐỀU LƯỚT FEED để nuôi trust score và IP proxy. Lướt feed không phải là dưỡng sinh.
  - **DƯỠNG SINH (ORGANIC REST 1/3):** Chính xác là thao tác **TẮT ĐĂNG VIDEO + TẮT FOLLOW** trong ngày nuôi đó (`0 Follow + 0 Upload`).
  - **Bỏ dưỡng sinh cho nick cắn đề xuất (`BOOST`):** Vẫn lướt feed 100%, chỉ đơn giản là **gỡ bỏ lệnh cấm upload** để nick được đăng đều đặn 48h/lần (2 ngày 1 video) nhằm đón trọn sóng view.

---

## 4. BẪY ĐỌC VẸT COMMENT / DOCSTRING CŨ THAY VÌ CONFIG CHẠY THẬT

* **Hiện tượng:** LLM đọc comment/docstring cũ trong code (`# full 6-10`) rồi khẳng định budget follow của farm là 6-10.
* **Thực tế:** File cấu hình chạy thật của từng máy (`config/machine*.yaml`) quy định:
  ```yaml
  budget_per_session_min: 10
  budget_per_session_max: 20
  budget_per_session: 20
  ```
* **Quy tắc:** Khi xác định quota và ngân sách farm, **Source of Truth là file YAML config chạy thật**, không được tin vào comment/docstring đã lỗi thời trong file Python.

---

## 5. BẪY DAO ĐỘNG DASHBOARD (FLAPPING "HÔM NAY CẮN MAI MẤT")

* **Nguyên nhân:** Dashboard chỉ đo delta 24h ($T$ so với $T-1$). Nếu dùng delta 24h làm công tắc trực tiếp: hôm nay cắn đề xuất (đổi lịch 48h), mai delta hạ nhiệt (về dưỡng sinh 72h) $\to$ lịch đăng bị giật cục liên tục.
* **Giải pháp chuẩn:**
  - Gắn cờ `BOOST` và **khóa giữ trong 5 ngày liên tiếp** (đủ để nick đăng trọn vẹn 2-3 video nhịp 48h).
  - Tự động hạ về bình thường sau 5 ngày nếu hết đà. Tuyệt đối không để lịch đăng nhảy giật theo từng ngày.
