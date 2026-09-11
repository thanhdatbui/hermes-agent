# 5 Gates Điều Phối Bắt Buộc (Anti-Insanity & Monolith Control)

Được đúc rút từ đợt audit chuyên sâu với Claude CLI Opus High (2026-09-11) sau sự cố Coordinator dispatch goal mở trên monolith 8.800 dòng và retry vòng lặp vô nghĩa (insanity loop).

## 1. Bản chất sự cố gốc rễ
- **Mâu thuẫn chí mạng**: Quăng goal mở ("tự tìm điểm SUCCESS", "tự phân tích tracking") vào file monolith 8.800 dòng (`social_reg_v1.py`) với leaf worker ngân sách 15 iterations. Riêng đọc và hiểu call graph đã ngốn 8-10 calls, worker không thể code và test kịp.
- **Thất bại cấu trúc (Structural Failure)**: Worker cạn sạch 15 iterations với `0 files modified`. Đây là lỗi thiết kế nhiệm vụ từ Coordinator, không phải lỗi ngẫu nhiên.
- **Insanity Retry Loop**: Coordinator không đọc tín hiệu thất bại, retry lần 2 y hệt prompt cũ -> worker 2 tiếp tục cháy 15 iterations với 0 files.
- **Gộp sai mô hình**: Nhét task Code-surgery (vài phút) chung batch với Batch-job (render hàng trăm GB video hàng giờ).

## 2. Quy tắc 5 Gates Bắt Buộc Trước Khi Dispatch

```
                        [LỆNH TỪ USER]
                              │
                              ▼
        [GATE 1: DECOMPOSE (Phân rã ngữ nghĩa & vòng đời)]
       Code-surgery (phút) vs Batch-job (giờ) -> CẤM chung batch
                              │
                              ▼
        [GATE 2: FEASIBILITY (Kiểm tra Monolith & Budget)]
       File > 1.500 dòng: Bắt buộc Patch Contract đóng
       Anchor duy nhất: grep -o ... | wc -l == 1
       CẤM TUYỆT ĐỐI goal mở ("tự tìm", "tự phân tích")
                              │
                              ▼
        [GATE 3: CIRCUIT BREAKER (Chống Insanity Retry)]
       Worker kết thúc 0 files: CẤM retry prompt cũ
       Bắt buộc thu hẹp scope / đổi contract mới (tối đa 2 lần)
                              │
                              ▼
        [GATE 4: WORKER FAIL-FAST INJECTION]
       Inject vào prompt: abort <= 3 iters nếu scope bất khả thi,
       trả về anchor + proposal thay vì đốt hết budget
                              │
                              ▼
        [GATE 5: COORDINATOR 5-QUESTION CHECKLIST]
       Tất cả 5 câu "Đã hoàn tất" -> MỚI ĐƯỢC DISPATCH
```

### Chi tiết 5 Gates:

### GATE 1 — DECOMPOSE TRƯỚC DISPATCH (CHỐNG GỘP TASK)
- Phân rã theo ngữ nghĩa và vòng đời công việc, không ánh xạ 1-1 câu nói ghép của user.
- CẤM TUYỆT ĐỐI dispatch chung batch giữa:
  - **Code-surgery** (sửa hook/bug, vài phút): 1 worker với Patch Contract đóng.
  - **Batch-job** (render/download/batch chạy hàng giờ): Chạy qua launcher nền (subprocess/queue) + monitor ngoài band. CẤM giao cho leaf worker ngồi đợi `ffmpeg` hay download.

### GATE 2 — FEASIBILITY CHECK & PATCH CONTRACT CHO MONOLITH > 1.500 DÒNG
- File target > 1.500 dòng: CẤM TUYỆT ĐỐI goal mở.
- Coordinator BẮT BUỘC tự grep O(1) xác định anchor duy nhất tuyệt đối:
  ```bash
  grep -o '<chuỗi neo>' <file> | wc -l   # Bắt buộc == 1
  ```
  *(Lưu ý: `grep -c` chỉ đếm dòng, không đếm số lần xuất hiện — dễ false positive nếu 1 dòng có 2 lần match).*
- Soạn sẵn exact `old_string` -> `new_string` và lệnh test focused < 30s. Chưa có anchor -> DỪNG, CẤM dispatch.

### GATE 3 — CIRCUIT BREAKER (CHỐNG RETRY LOOP VÔ NGHĨA)
- Worker kết thúc với `files_modified == 0 && iterations_exhausted` là **THẤT BẠI CẤU TRÚC**.
- CẤM TUYỆT ĐỐI retry với prompt cũ. Bắt buộc thu hẹp scope, đổi contract mới hoặc báo user.
- Tối đa 2 lần dispatch cho 1 sub-task, lần 2 contract PHẢI khác lần 1.

### GATE 4 — WORKER FAIL-FAST PROTOCOL
- Mọi prompt worker sửa monolith bắt buộc inject clause:
  > *"NẾU trong ≤ 3 iterations đầu nhận thấy scope quá rộng / bất khả thi với budget 15 calls: DỪNG NGAY (ABORT). Báo cáo anchor tìm được và đề xuất contract thu hẹp. CẤM đốt hết 15 calls để mò file rồi kết thúc 0 files modified."*

### GATE 5 — COORDINATOR 5-QUESTION CHECKLIST
Trước khi gọi `delegate_task`, Coordinator tự kiểm tra:
1. Task này đã được phân rã tới đơn vị nhỏ nhất chưa?
2. File target > 1.500 dòng đã có Patch Contract với anchor `grep -o | wc -l == 1` chưa?
3. Ngân sách 15 iters có đủ khả thi cho scope này không?
4. Đây là code-surgery hay batch-job? (Batch-job cấm giao leaf worker ngồi chờ).
5. Nếu là re-dispatch: contract có KHÁC lần trước không?
*(Bất kỳ câu nào trả lời "Chưa / Không" -> DỪNG LẠI, CẤM DISPATCH).*
