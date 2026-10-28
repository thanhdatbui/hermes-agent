# Kỷ Luật An Ninh Máy Host Farm: Windows Defender & Quy Trình Quét Định Kỳ

Nhận từ phiên làm việc 28/10/2026: Đánh giá nguy cơ mã độc Stealer (Facebook Ads "tặng tool MMO free"), chính sách bảo vệ máy Host Farm và thiết lập lịch quét virus định kỳ cho 2 máy PC (Kibe & Admin).

---

## 1. So Sánh Windows Defender vs Antivirus Bên Thứ 3 Trên Máy Host Farm

| Tiêu chí | Windows Defender (Mặc định) | Antivirus bên thứ 3 (Kaspersky, Avast, Norton...) |
| :--- | :--- | :--- |
| **Ảnh hưởng mạng/ADB** | **0% can thiệp:** Giữ nguyên vẹn socket ADB, port 5037/5038, TCP tunnel. | **Rất nguy hiểm:** Hay chèn SSL/Network Filter làm đứt kết nối ADB, chặn MobiProxy, lỗi CDP GPMLogin. |
| **Tiêu tốn tài nguyên** | **Nhẹ:** Tích hợp tầng kernel, tự điều tiết khi CPU/Disk cao tải. | **Nặng:** Chiếm 1.5GB – 3GB RAM, quét file ngầm liên tục làm lag render/download. |
| **Độ phủ mẫu nhận diện** | **Đạt chuẩn xuất sắc:** AV-TEST / AV-Comparatives đạt 99.5% – 100%, có Cloud-delivered Protection. | Tương đương hoặc chỉ nhỉnh hơn ở các heuristic nâng cao. |
| **Xung đột phần mềm** | Không xung đột với Python venv, Node, MSYS bash, Git hooks. | Dễ bắt nhầm (False Positive) các script tự động hóa, hook kiểm soát và công cụ nội bộ. |

**Kết luận:** Trên máy Host vận hành Farm / MMO / Automation, **Windows Defender là lựa chọn tối ưu và đủ xài nhất**. Tuyệt đối không cài thêm các phần mềm AV bên thứ 3 làm nghẽn hạ tầng.

---

## 2. Điểm Mù Cốt Tử: Mã Độc Stealer FUD & Kịch Bản Lừa Đảo MMO

- **Hình thức phát tán:** Quảng cáo Facebook / bài viết "chia sẻ tool reup/vietsub miễn phí", yêu cầu comment nhận link Google Drive/Mega chứa file `.zip` có mật khẩu (để qua mặt bộ quét virus của Google/Chrome).
- **Cơ chế:** Bên trong chứa file `.exe`, `.lnk` hoặc script obfuscated chạy mã độc đánh cắp thông tin (Lumma Stealer, Vidar, RedLine...).
- **Độ trễ chữ ký (Signature Lag):** Hacker liên tục bọc crypter mới (FUD - Fully Undetectable) nên Defender và mọi AV thương mại đều bị qua mặt trong 24–48h đầu.
- **Hậu quả nếu bấm nhầm:** Cào sạch Cookie trình duyệt, Session Facebook/TikTok/Gmail, Token OAuth, Private Key ví Crypto và credentials các file `.env` trên máy host.
- **Biện pháp phòng ngừa:**
  - Tuyệt đối không tải và chạy các file tool crack / tool tặng không rõ nguồn gốc.
  - Khi cần công cụ tự động hóa, ưu tiên tự code bằng script mã nguồn mở (Python, FFmpeg, Whisper, Edge-TTS).
  - Nếu nghi ngờ máy bị nhiễm: Tải **Malwarebytes Free** quét 1 lần duy nhất (On-Demand scan) rồi tắt, không để chạy thường trực.

---

## 3. Lệnh Thao Tác Cơ Giới Hóa Microsoft Defender (MpCmdRun.exe)

Microsoft cung cấp công cụ dòng lệnh chính chủ tại:  
`"C:\Program Files\Windows Defender\MpCmdRun.exe"`

### Các lệnh chuẩn:
1. **Cập nhật mẫu nhận diện mới nhất (Signature Update):**
   ```cmd
   "C:\Program Files\Windows Defender\MpCmdRun.exe" -SignatureUpdate
   ```
2. **Quét Nhanh (Quick Scan - ScanType 1):**
   ```cmd
   "C:\Program Files\Windows Defender\MpCmdRun.exe" -Scan -ScanType 1
   ```
   - *Phạm vi:* Quét bộ nhớ RAM, Registry, tiến trình đang chạy và các thư mục hệ thống / Startup nhạy cảm.
   - *Thời gian:* 2 – 4 phút.
   - *Đặc điểm:* Rất nhẹ, hoàn toàn không gây nghẽn đĩa hay lag farm. **Khuyên dùng định kỳ 1 lần/tuần vào khung giờ nghỉ (ví dụ: 03:30 sáng Chủ Nhật).**
3. **Tại sao CẤM lên lịch Quét Toàn Diện (Full Scan - ScanType 2) tự động:**
   - Quét toàn bộ ổ cứng hàng TB dữ liệu video, profile cache, database.
   - Gây bão I/O đĩa (Disk 100%), làm nghẽn tiến trình render video, ghi log farm và timeout các lệnh ADB.

---

## 4. Kỷ Luật Subagent Contract Khi Điều Tra Trạng Thái Host

Khi Coordinator dispatch worker subagent qua `delegate_task` cho các tác vụ điều tra hoặc kiểm tra hệ thống:
1. **Bắt buộc khai báo Task Kind & Target File:**
   ```yaml
   TASK_KIND: INVESTIGATE
   TARGET_FILE: <đường_dẫn_tuyệt_đối_đến_file_cần_khảo_sát_hoặc_script_thực_thi>
   ```
2. **Bắt buộc tiêm Fail-Fast (Gate 4 Invariant):**
   ```yaml
   FAIL_FAST: NẾU trong <= 3 iterations đầu nhận thấy scope bất khả thi với budget 15 calls thì PHẢI DỪNG NGAY (ABORT) và báo cáo blocker.
   ```
Thiếu bất kỳ thành phần nào trên, hook `guard_delegate_contract.py` sẽ chặn dispatch với mã lỗi `MISSING_TASK_KIND` hoặc `INVESTIGATE_MISSING_FAIL_FAST`.
