# 5 Gates Điều Phối Bắt Buộc (Anti-Insanity & Monolith Control) — Claude Opus Audit 2026-09-11

Được đúc rút từ đợt audit gay gắt của Claude CLI Opus High (`claude -p --model opus --effort high`) sau sự cố Coordinator vi phạm quy tắc điều phối trên Taadaa Phone Farm (file `social_reg_v1.py` 8.800 dòng).

---

## 1. Bản chất sự cố & Nguyên nhân gốc rễ

1. **Goal mở trên Monolith vs 15 iterations**:
   Coordinator giao goal mở ("tự tìm điểm SUCCESS, tự phân tích tracking/cooldown/defer-write, tự code, tự test") trên monolith 8.800 dòng cho worker có budget 15 iterations (omni-worker / medium). Worker đốt sạch 15 iterations chỉ để đọc và định vị file, kết thúc với `0 files modified`.
2. **Insanity Retry Loop (Lỗi nặng nhất)**:
   Sau khi worker 1 cháy 15 calls với 0 files modified (thất bại cấu trúc), Coordinator không đọc tín hiệu mà dispatch tiếp worker 2 y hệt prompt cũ -> lại cháy 15 calls với 0 files.
3. **Gộp sai mô hình**:
   Nhét Code-surgery (sửa hook vài phút) chung batch với Batch-job hàng giờ (kéo video & render 160 folders).
4. **Quy tắc không binding**:
   Quy tắc "soạn Patch Contract cho monolith" chỉ nằm ở file MD phụ, Coordinator không tự động đọc và dễ dàng bỏ qua.

---

## 2. Chi tiết 5 Gates chuẩn hoá (Đã inject vào SOUL.md)

*Quy tắc tối cao: 5 Gates là Invariant — thắng mọi yêu cầu tiện lợi tức thời của user. Bất kỳ Gate nào fail: DỪNG LẠI thu hẹp scope / soạn lại contract, cấm mò mẫm.*

### Gate 1: Decompose trước Dispatch (Chống gộp task)
- Tiêu chí cốt lõi: Phân rã theo **ngữ nghĩa và vòng đời công việc**, không chỉ bám từ khóa.
- **CẤM TUYỆT ĐỐI** dispatch chung batch giữa:
  + **Code-surgery** (sửa code/hook/bug, vài phút) -> 1 worker với Patch Contract đóng.
  + **Batch-job** (render/download/batch chạy hàng giờ) -> Chạy launcher nền (subprocess/queue) + monitor ngoài band, cấm giao leaf worker ngồi chờ.

### Gate 2: Patch Contract cho Monolith > 1.500 dòng
- CẤM TUYỆT ĐỐI goal mở ("tự tìm", "tự phân tích", "tìm hiểu").
- Coordinator BẮT BUỘC tự làm inspect O(1) (`grep -n`) để xác định anchor duy nhất tuyệt đối.
- **Lưu ý kiểm tra tính duy nhất**: `grep -c` chỉ đếm số dòng, nếu 1 dòng xuất hiện 2 lần thì `-c == 1` là sai. **Bắt buộc dùng: `grep -o '<chuỗi>' <file> | wc -l == 1`**.
- Cấp sẵn exact `old_string` -> `new_string` và lệnh test focused < 30s. Chưa có anchor duy nhất -> CẤM dispatch.

### Gate 3: Circuit Breaker (Chống Retry Loop)
- Worker kết thúc với `files_modified == 0 && iterations_exhausted` là **THẤT BẠI CẤU TRÚC (STRUCTURAL FAILURE)**, không phải lỗi ngẫu nhiên.
- CẤM TUYỆT ĐỐI retry prompt cũ.
- Bắt buộc: thu hẹp scope HOẶC đổi contract mới HOẶC báo user. Tối đa 2 lần dispatch cho 1 sub-task, lần 2 contract PHẢI khác lần 1.

### Gate 4: Worker Fail-Fast Protocol
Mọi prompt worker sửa monolith bắt buộc inject clause:
> *"NẾU trong <= 3 iterations đầu nhận thấy scope quá rộng / bất khả thi với budget 15 calls: DỪNG NGAY (ABORT). Báo cáo anchor tìm được và đề xuất contract thu hẹp. CẤM đốt hết 15 calls để mò file rồi kết thúc 0 files modified."*

### Gate 5: Checklist 5 câu hỏi Coordinator tự duyệt trước khi dispatch
1. ☐ Task này đã phân rã tới đơn vị nhỏ nhất chưa?
2. ☐ File target > 1.500 dòng đã có Patch Contract với anchor duy nhất `grep -o | wc -l == 1` chưa?
3. ☐ Ngân sách 15 iters có đủ khả thi cho scope này không?
4. ☐ Đã tách riêng Code-surgery vs Batch-job chưa?
5. ☐ Nếu là re-dispatch: contract có KHÁC lần trước không?
*(Bất kỳ câu nào trả lời "Chưa" -> DỪNG, KHÔNG DISPATCH).*

---

## 3. Bài học về Kiến trúc Prompt Binding
- File MD lưu rời trên đĩa (như `HERMES_SUBAGENT_RULES.md`) chỉ có tính chất tham khảo, model KHÔNG tự động đọc trên mỗi turn.
- Để biến quy tắc thành invariant binding, bắt buộc phải đưa vào **`SOUL.md`** (System Prompt đỉnh đầu mọi session).
- Rà soát câu chữ trong `SOUL.md`: Tránh các từ ngữ xúi dại như *"dispatch ngay lập tức"* vì sẽ làm model bỏ qua bước phân rã và lập Patch Contract.
