# TikTok Post Button Recovery: resource-id `sp3`, Preview `rzu`, & Idempotency Stale Receipt

## 1. Nút Đăng mới: `sp3` và Bề mặt Preview / Editor

### Triệu chứng
- Khi hoàn tất video pick / caption, quy trình chuyển sang bước `POST`.
- TikTok phiên bản mới không hiển thị nút "Tiếp" / "Next", mà hiển thị trực tiếp giao diện Preview / Editor đã có sẵn nút **Đăng**.
- Nếu code chỉ tìm "Tiếp"/"Next" sẽ văng lỗi:
  `[POST_NEXT_SELECTOR_EXHAUSTED] POST: final composer/editor Next surface was not confirmed`

### Đặc điểm UI Selector
- **Resource ID nút Đăng**: `com.ss.android.ugc.trill:id/sp3` (tail: `sp3`).
- **Class**: `android.widget.Button`.
- **Text / Content-Desc**: `text="Đăng"` hoặc `content-desc="Đăng"`.
- **Bounds điển hình**: `[564,1770][1032,1902]` (nửa dưới bên phải).
- **Marker nhận diện bề mặt Preview / Editor**: `"Xem trước"`, `resource-id="...:id/rzu"`, `"sp3"`, `text="Đăng"`, `content-desc="Đăng"`.

### Cách xử lý chuẩn
1. Thêm `"sp3"` vào danh sách tuple các post button resource-id:
   `("sh8", "shd", "sox", "soz", "sp7", "sp3", "rbp", "t66", "post_action", "post_button")`
2. Tại nhánh kiểm tra preview / "Xem trước": mở rộng nhận diện `"rzu"` và `"sp3"`.
3. Tại bước Step 1 (tìm "Tiếp" / "Next"): nếu không tìm thấy "Tiếp", kiểm tra xem màn hình hiện tại có chứa các marker preview / Đăng (`"Xem trước"`, `"rzu"`, `"sp3"`, `text="Đăng"`, `content-desc="Đăng"`).
   - Nếu có: tap trực tiếp nút Đăng (`sp3` / exact text / content-desc) và tiếp tục flow, **KHÔNG được raise `POST_NEXT_SELECTOR_EXHAUSTED`**.

---

## 2. Pitfall Idempotency Barrier (`_record_post_intent` FileExistsError)

### Triệu chứng
- Khi chạy retry video hoặc canary test với `--video-number N`:
  `[WARNING] Post-intent receipt appeared during reservation; refusing to tap Post again`
- Dù nút Đăng xuất hiện trên màn hình, code vẫn từ chối tap và sau đó fail quy trình.

### Nguyên nhân gốc rễ
- File receipt `idempotency/post-attempts/machine_{safe_machine}_account_{safe_account}_video_{video_number}.json` đã tồn tại từ một lần chạy trước đó (ví dụ từ ngày hôm trước).
- Trong `_handle_post`, code có logic:
  ```python
  if receipt is not None and str(receipt.get("status") or "").casefold() == "completed":
      if current_run_id and receipt_run_id != current_run_id:
          receipt = None
  ```
  Nhưng khi gọi `_record_post_intent()`, nhánh tạo receipt dùng:
  ```python
  with path.open("x", encoding="utf-8") as handle:
      json.dump(payload, handle)
  ```
  Vì file cũ vẫn còn trên đĩa, `open("x")` ném `FileExistsError`, khiến hàm hiểu nhầm là có tiến trình khác đang race và trả về `False`.

### Giải pháp
1. Trong block `except FileExistsError`:
   - Đọc payload file hiện có trên đĩa.
   - Nếu `old_run_id != current_run_id`, đây là receipt cũ của phiên trước → ghi đè atomic bằng `self._write_post_attempt_receipt(payload)`.
   - Chỉ trả về `False` khi `old_run_id == current_run_id`.
2. Khi chạy canary test thủ công hoặc override video đã từng post:
   - Dọn dẹp receipt cũ tại `D:\CodexRuntime\tiktok-video\idempotency\post-attempts\machine_{M}_*_video_{N}.json`
   - Dọn dẹp media-fingerprint tương ứng tại `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\` nếu có reservation cũ.
