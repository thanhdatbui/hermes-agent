# Multi-Cluster Watchdog Triage & USB Hub Block Drop Signatures

## 1. Giải Mã Thuật Ngữ & Cấu Trúc Báo Cáo Đa Cụm (Multi-Cluster Disambiguation)
Bản tin watchdog `[FARM ALERT] PHÁT HIỆN LỖI NUÔI FEED HÀNG LOẠT` gom kết quả của các cụm farm độc lập vào chung một thông điệp Telegram:
- **Cụm 1:** `🏢 【FARM KIBE - MÁY 1-80】 (Run: row-{row}-{hhmmss})`
- **Cụm 2:** `🏢 【FARM ADMIN - MÁY 201-280】 (Run: row-{row}-{hhmmss})`

### Phân biệt 2 ngữ nghĩa khi User hỏi về "Phiên 1" vs "Phiên 2":
1. **Nhầm lẫn Cụm / Dàn Farm:**
   - User thường nhìn vào thứ tự hiển thị từ trên xuống dưới và gọi Farm Kibe (M1-M80) là "phiên 1" / "dàn 1", và Farm Admin (M201-M280) là "phiên 2" / "dàn 2".
   - Khi Cụm Kibe báo lỗi nặng (vd 33 máy) còn Cụm Admin báo lỗi nhẹ (vd 4 máy), nguyên nhân thường là do hạ tầng controller/host của Kibe gặp sự cố riêng biệt, không ảnh hưởng sang host Admin.
2. **So sánh 2 lần chạy trong cùng một Ca (Phiên 1 vs Phiên 2):**
   - **Phiên 1 (Early Window):** Chạy ở khung giờ đầu ca (vd 06:00, 12:00, 18:00 - format nhãn `row-0-120031`).
   - **Phiên 2 (Late Window):** Chạy ở khung giờ sau (vd 08:00, 14:00, 20:00 - format nhãn `row-0-140735`). Phiên này có upload video hook và đồng bộ tài khoản theo Phiên 1 (S2 bám S1).
   - *Quy tắc phản hồi:* Bắt buộc giải thích ngắn gọn cả 2 góc nhìn (khác biệt hạ tầng giữa 2 Cụm, và đối chiếu log giữa 2 mốc giờ Phiên 1 vs Phiên 2) để người vận hành nắm trọn bức tranh.

---

## 2. Dấu Hiệu Rớt Phần Cứng Theo Block (Hardware Block Drop vs Software Bug)
Khi phân tích danh sách máy bị lỗi `Mất kết nối ADB/USB`:

### Chữ ký nhận diện (Failure Signature):
- **Phần cứng / USB Hub:** Danh sách máy mất kết nối dồn thành các **dải số liên tiếp** tương ứng với các cổng vật lý của một USB Hub:
  * Ví dụ: Dải `M1 - M14` (14 máy liên tiếp) và dải `M53 - M66` (14 máy liên tiếp).
  * Mỗi hub công nghiệp thường cấp 10-16 port. Khi sụt áp nguồn cấp (power brick) hoặc lỏng cáp USB uplink nối vào host, toàn bộ dải máy cắm trên hub đó sẽ mất tín hiệu ADB đồng loạt.
- **Phần mềm / App TikTok Crash:** Lỗi phân tán ngẫu nhiên (vd `M18: Lỗi mở/focus App`, `M74: Lỗi script/timeout`).
- **Hành động phản ứng chuẩn:**
  1. Tuyệt đối không can thiệp sửa code runner hay cấu hình script khi nhận thấy chữ ký rớt theo block liên tiếp.
  2. Hướng dẫn kiểm tra trực tiếp nguồn phụ của các bộ USB Hub tương ứng với dải máy.
  3. Sau khi cắm lại hub, khởi động lại ADB daemon trên host: `adb kill-server && adb start-server`.

---

## 3. Kỹ Thuật Trích Xuất Telemetry Tốc Độ Cao O(1) (Chống Timeout 60s)
- **CẠM BẪY:** Tuyệt đối không tự viết script gọi hàm phân tích toàn diện `parse_run_all` cho nhiều run/cluster đồng thời trong phiên chat (dễ bị nghẽn I/O và chạm timeout 60s).
- **QUY TẮC O(1):**
  * Mỗi run được runner ghi nhận tóm tắt độc lập tại:
    `D:/Taadaa/runtime/<cluster>/live/<target_date>/row-{row}-{hhmmss}/<run_id>/summary.txt`
  * Đọc trực tiếp 10 dòng đầu của file `summary.txt` hoặc đọc `run_manifest.json` để lấy ngay trạng thái, mã lỗi và thời gian bắt đầu mà không cần duyệt qua hàng ngàn file log chi tiết của từng máy.
