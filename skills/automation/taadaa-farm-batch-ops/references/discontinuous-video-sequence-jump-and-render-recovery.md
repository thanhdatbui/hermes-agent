# Triage Lỗi Hết Video Khi Dãy Số Bị Nhảy Cóc (Missing Video Discontinuous Jump Trap)

## 1. Hiện Tượng & Dấu Hiệu Nhận Biết
- **Cảnh báo Farm Alert:** Một hoặc nhiều máy bị dừng với nhãn: `Hết video/Cần cào` (ví dụ: `M60: Hết video/Cần cào (1)`).
- **Mâu thuẫn thực tế khi kiểm tra thư mục render (`D:\TIKTOK-videonuoinick\<out_id>`):**
  - Thư mục có rất nhiều video (ví dụ 46 file `.mp4`).
  - Cột `Video Đã Đăng` trong file Excel (ví dụ `Tik4.xlsx`) ghi `10` clip.
  - Runner lại báo lỗi `[VIDEO_PATH_ERROR] RESOLVE_NEXT_VIDEO: Cannot resolve video path: Video file not found: D:\TIKTOK-videonuoinick\<out_id>\11.mp4`.

---

## 2. Bản Chất Bẫy Nhảy Cóc Dãy Số (Discontinuous Jump Trap)
1. **Quy tắc của Bot Upload TikTok:**
   - Bot luôn tính toán video tiếp theo cần đăng theo công thức tuần tự:
     $$\text{next\_video} = \text{posted\_count} + 1$$
   - Ví dụ: Đã đăng 10 clip $\rightarrow$ bắt buộc tìm đúng file `11.mp4`.
2. **Nguyên nhân khuyết file giữa chừng:**
   - Trong thư mục render, các đợt render hoặc copy cũ bị gián đoạn:
     * Đã có các file: `1.mp4`, `2.mp4` ... `10.mp4`.
     * Sau đó dãy số nhảy vọt lên: `27.mp4`, `28.mp4` ... `61.mp4`.
     * Toàn bộ đoạn giữa từ **`11.mp4` đến `26.mp4` hoàn toàn không tồn tại trên đĩa**.
   - Runner kiểm tra không thấy `11.mp4` nên fail-closed an toàn và báo *Hết video*.

---

## 3. Quy Trình Khắc Phục O(1) Bằng Script Canonical (`random_batch_render.py`)

Khi gặp lỗi này, **CẤM** xóa toàn bộ thư mục để render lại từ đầu làm lãng phí CPU/GPU và mất công sức trước đó. Bắt buộc thực hiện render bù đúng các clip thiếu theo quy trình sau:

### Bước 1: Xác định nguồn video gốc ($F_{src}$)
- Tra cứu cột `video gốc` trong file Excel `Tik<slot>.xlsx` (hoặc tính theo công thức: $F_{src} = (\text{Slot} - 1) \times 80 + \text{Machine}$).
- Kiểm tra trong `D:\video goc\<src_id>` xem file gốc `11.mp4` có sẵn không.

### Bước 2: Tạo danh sách file cần render bù
- Tạo một file text tạm (ví dụ `tmp_list.txt`) chứa đường dẫn tuyệt đối đến file nguồn cần render:
  ```text
  D:\video goc\<src_id>\11.mp4
  ```

### Bước 3: Chạy render bù với tham số chuẩn hóa
- Thực thi qua Python runner chuẩn với cấu hình:
  ```bash
  python -u scripts/random_batch_render.py \
    --input-dir "D:/video goc/<src_id>" \
    --output-dir "D:/TIKTOK-videonuoinick/<out_id>" \
    --preset "presets/preset_owner.json" \
    --file-list "tmp_list.txt" \
    --start-seq 11 \
    --slot <slot_idx> \
    --machine-id <machine_idx> \
    --randomize \
    --parallel 1
  ```
  *(Lưu ý: `start-seq` phải đặt đúng số clip thiếu, ví dụ `11`).*

### Bước 4: Kiểm chứng thành phẩm
- Xác nhận file `11.mp4` đã sinh ra trong thư mục output với dung lượng đầy đủ (>5MB) và ffprobe hợp lệ.
- Xóa file text tạm sau khi hoàn tất.
