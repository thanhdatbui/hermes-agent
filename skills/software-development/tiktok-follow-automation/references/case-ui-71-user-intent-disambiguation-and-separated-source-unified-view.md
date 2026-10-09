# Case UI-71: User Intent Disambiguation & Separated Source vs Unified View Architecture

## 1. Bối cảnh & Sự cố Phân tán Ngữ cảnh (Hallucination of "Stop Script")
Trong phiên làm việc ngày 20/09/2026, user gửi lệnh ngắn gọn:
`"rồi làm đi"`
Ngay sau khi hệ thống vừa nhận được phản biện kiến trúc từ Sol:
> "KHÔNG GỘP HẾT EXCEL VÀO MỘT FILE. Gộp logic để đọc — tuyệt đối KHÔNG gộp vật lý để vận hành."

**Sự cố xảy ra:**
Mô hình bị ảo giác ngữ cảnh (context drift / summarization hallucination) từ các ca trước, diễn giải nhầm cụm từ tiếng Việt đời thường thành `"stop scrip"`, dẫn đến việc hỏi lại ngớ ngẩn về việc dừng script nuôi, khiến user cực kỳ ức chế và nổi giận.

### Bài học cốt lõi (Discipline Rule):
1. **Lệnh "rồi làm đi / làm luôn / triển đi / xúc đi"**:
   - 100% là tín hiệu **PHÊ DUYỆT THỰC THI (EXECUTE APPROVED PLAN)** cho phương án/kiến trúc vừa được thảo luận ở lượt trao đổi liền kề trước đó.
   - Tuyệt đối cấm tự suy diễn ra các từ khóa tiêu cực ("stop script", "hủy", "dừng", "rollback") khi câu lệnh hoàn toàn mang tính thúc đẩy thực thi.
   - Khi nhận lệnh này: **LẬP TỨC THỰC THI** các bước kỹ thuật đã chốt, không hỏi lại, không lảm nhảm xin xác nhận lần 2.

---

## 2. Kiến trúc Dữ liệu: Separated Source vs Unified View (Tách Sổ Cái Vận Hành — Gộp Danh Bạ Đọc)

### Vấn đề bài toán:
- Hệ thống 160 máy gồm 2 cụm: Kibe (máy 1–80, ~611 nick) và Admin (máy 201–280, ~319 nick).
- Nhu cầu: Cho nick dàn Kibe follow được cả dàn Admin để mở rộng đồ thị graph, tránh khép kín mạng.
- Nguy cơ: Gộp chung file Excel vận hành (`taikhoan_dat_v2_updated .xlsx`, `Tik1.xlsx` -> `Tik8.xlsx`) sẽ dẫn tới race condition ghi file, conflict OneDrive, single point of failure (sập 1 file chết cả 160 máy).

### Giải pháp kỹ thuật chuẩn hóa (Sol Architecture APPROVED):
1. **Sổ cái vận hành (Operational Source) — BẢO LƯU ĐỘC LẬP 100%:**
   - `D:/OneDrive/TaadaaData/kibe/` và `D:/OneDrive/TaadaaData/admin/`: giữ nguyên tách biệt theo từng cụm máy, runner từng cụm đọc/ghi độc lập.
2. **Danh bạ Follow gộp (Unified Target View) — READ-ONLY:**
   - Tạo script tự động `D:/Taadaa/tools/sync_combined_safe_workbook.py` (hook sau mỗi lần sync tài khoản).
   - Đọc 2 file `taikhoan_run_safe.xlsx` của Kibe và Admin $\rightarrow$ lọc trùng UID $\rightarrow$ xuất ra `D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx` (930 UIDs).
   - Ghi nguyên tử trên cùng phân vùng ổ đĩa (atomic replace via same filesystem `.tmp.xlsx`) để tránh lỗi `WinError 17`.
3. **Hard Gate trong Engine Follow (`follow_engine.py`):**
   - Anchor Mode 2: **Chỉ chấp nhận các nick thuộc dàn Kibe (`machine <= 80` và $\ge 10$ video)**.
   - Toàn bộ nick dàn Admin (`machine >= 201`) chỉ làm target nhận follow, tuyệt đối không bị bốc làm Anchor.

---

## 3. Giải đáp dữ liệu Farm: Sổ Cái Raw Rows vs Unique Accounts & Anchor Gate

1. **Dashboard hiện > 1000 nick (cụ thể 1004):**
   - Sổ cái gốc Kibe: 640 hàng (80 máy $\times$ 8 hàng).
   - Sổ cái gốc Admin: 364 hàng (có 45 nick bị gán trùng nhiều hàng).
   - $640 + 364 = 1004$ dòng raw.
   - Sau khi lọc trùng và loại bỏ hàng rỗng: Còn đúng **930 nick duy nhất (Unique UIDs)** trong file gộp.
2. **Anchor Tik1/Tik2 vì sao chỉ có 122 thay vì 160 nick:**
   - $80 \text{ máy} \times 2 \text{ slot (Tik1, Tik2)} = 160 \text{ slot}$.
   - Gate an toàn yêu cầu `video_count >= 10`.
   - Thực tế có **37 nick chưa đạt mốc 10 video** (chỉ có từ 0 đến 9 video) nên bị gate loại trừ an toàn, bảo vệ trust cho Mode 2.
   - Khi các nick này đăng bài vượt mốc 10 video, hệ thống tự động thăng cấp lên Anchor.
