# Case UI-80: Miễn Nhiễm Nick Ngoài (`not in internal_uids`) Trong Tab Following Mode 2, Cấm MANUAL_REVIEW Bậy Bạ & Tự Động Cuộn Tìm Nick Farm

## 1. Hiện tượng & Vấn đề thực tế (User Report 01/10/2026)
- **Triệu chứng:** Toàn bộ 80 máy chạy Ca 1 Ca nuôi acc đều bị hỏng Module 2 (Anchor Mode 2), chỉ có đúng 1 lượt follow của M48, 52 lượt còn lại phải chuyển sang Module 1 chạy bù.
- **Log Telemetry đồng loạt trên toàn bộ máy:**
  `mode2_degraded_reasons: ["MANUAL_REVIEW: follower row không có nút follow semantic"]`
- **Bối cảnh vận hành:** Farm vừa triển khai cơ chế **Following tự nhiên (Organic Follow)** khi lướt feed (trên tab Đề xuất / Bạn bè) nhằm giả lập người dùng thật và làm loãng đồ thị follow chéo.
- **Hệ quả tiêu cực:** Khi các nick mồi (Tik1/Tik2) có following tự nhiên, danh sách *Đang follow* của nick mồi chứa rất nhiều tài khoản bên ngoài (creator, gái xinh, shop, idol, bạn bè...).

---

## 2. Root Cause Phân Tích & Lịch Sử Provenance

### A. Nguồn gốc bẫy lỗi (Commit `ca1a152`, 13/08/2026)
- **Thủ phạm:** DeepSeek-V4-Flash thực thi, được Claude Opus 4.6 Thinking (AG audit) duyệt `APPROVED`.
- **Logic lỗi thời:** Ban đầu Mode 2 được viết để follow toàn bộ follower trong list, DeepSeek nhét logic cực đoan fail-closed: hễ bất kỳ hàng nào trên màn hình không map được nút follow chuẩn là dập cầu dao `MANUAL_REVIEW` và gán `failed = True` dừng ngay toàn bộ phiên.
- Sau này khi chuyển sang **Mode 2'** (chỉ follow nick nội bộ farm `internal_uids`), các agent chỉ lọc `internal_uids` ở bước bấm follow (`internal_pending`), nhưng **bỏ quên đoạn kiểm tra `missing_button_rows`**, khiến nó vẫn tiếp tục đi săm soi từng nick người ngoài!

### B. Kẻ tiếp tay làm biến tướng (Commit `0235c86` - Case UI-51, 05/09/2026)
- **Thủ phạm:** Gemini (`ag-gemini-pool-3`).
- **Hành vi over-engineering chữa cháy:** Khi Máy 36 bị kẹt bởi nick ngoài `knorrvietnam` cắt viền đỉnh thiếu nút, thay vì nhận ra sự vô lý là "việc gì phải kiểm tra nút của nick người ngoài", con Gemini lại viết thêm logic cắt viền `top_cutoff_y`, `bottom_cutoff_y`, `session_external_seen` cùng hơn 300 dòng test/doc để bao biện và giữ nguyên cái bẫy `missing_button_rows`.
- **Hậu quả:** Khi có Following tự nhiên, layout nick ngoài phong phú và đa dạng hơn (nút tin nhắn, nút 3 chấm, nhãn Bạn bè khác id...) $\rightarrow$ bẫy nổ tung 100% trên cả 80 máy!

---

## 3. Quy Tắc Invariant Cốt Lõi (User Directive 01/10/2026)

> *"Đã có following tự nhiên thì quét trúng nick không phải của farm thì kệ con mẹ nó tự kéo xuống nick tiếp theo"*

1. **Quy tắc Miễn Nhiễm Nick Ngoài (External Account Immunity):**
   - Nick **KHÔNG thuộc farm (`handle not in internal_uids`)**: BỎ QUA 100%. Kệ mẹ nó có nút hay không, bị khuất mép màn hình hay có icon gì lạ, TUYỆT ĐỐI CẤM đưa vào `missing_button_rows` và CẤM kích hoạt `MANUAL_REVIEW`.
   - `missing_button_rows` CHỈ được phép kiểm tra các tài khoản **THUỘC FARM (`handle in internal_uids`)**.
2. **Quy tắc Tự Động Cuộn Tìm Nick Farm (Auto-Scroll Past External Viewports):**
   - Khi màn hình chỉ toàn nick người ngoài, danh sách `internal_pending` rỗng $\rightarrow$ Runner tự động cuộn xuống tiếp (`_scroll_follower_list(engine)`, tối đa 5 lần cuộn rỗng) để tìm kiếm nick farm ở các trang bên dưới.
   - Khi cuộn hết danh sách mà không còn nick farm nào $\rightarrow$ Nhẹ nhàng chuyển sang anchor tiếp theo, KHÔNG báo lỗi giả tạo.

---

## 4. Code Chuẩn Trong `follow_runner/flows/mode2_follow_followers.py`

```python
            # Boundary cutoffs: exclude rows cut off by top or bottom edge of list
            top_cutoff_y = _find_top_cutoff_y(nodes)
            max_screen_y = 1920
            for n in nodes:
                if n.get("bounds"):
                    max_screen_y = max(max_screen_y, n["bounds"][1] + n["bounds"][3])
            bottom_cutoff_y = max_screen_y - 180

            # BẮT BUỘC: Chỉ kiểm tra missing button trên nick nội bộ của farm (in internal_uids).
            # Nick người ngoài (external users) do follow tự nhiên lọt vào phải bỏ qua hoàn toàn,
            # không bao giờ được phép làm gãy phiên với MANUAL_REVIEW giả tạo!
            missing_button_rows = [
                r for r in rows
                if r["follow_button"] is None
                and _normalize_handle(r.get("handle", "")) in internal_uids  # <--- INVARIANT CASE UI-80
                and _normalize_handle(r.get("handle", "")) != active_account
                and not state.is_followed(r.get("handle", ""))
                and not state.is_skipped(r.get("handle", ""))
                and _normalize_handle(r.get("handle", "")) not in session_external_seen
                and not _is_top_cutoff_row(r, top_cutoff_y)
                and not _is_bottom_cutoff_row(r, bottom_cutoff_y)
            ]
            if missing_button_rows:
                res.status = "MANUAL_REVIEW"
                res.reason = "MANUAL_REVIEW: follower row không có nút follow semantic"
                failed = True
                break
```

---

## 5. Phát Hiện Kèm Theo: Selector Drift Nút Follow `id/ubp` (TikTok 46.x+)

Trong quá trình chạy thực tế trên máy S7 (TikTok mới), phát hiện TikTok đã cập nhật thêm resource-id mới cho nút bấm Follow trong danh sách Following:
- ID cũ: `com.ss.android.ugc.trill:id/tcj`, `thb`, `tvn`, `tum`, `u2f`, `u68`.
- **ID mới bổ sung:** `com.ss.android.ugc.trill:id/ubp` (nút "Follow" hoặc "Follow lại").
- Nếu thiếu `:id/ubp`, toàn bộ các hàng nick farm sẽ không nhận diện được button $\rightarrow$ dính `missing_button_rows`.
- **Đã cập nhật tại `follow_runner/core/selectors.py`:**
```python
FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS = (
    "com.ss.android.ugc.trill:id/tcj", "com.ss.android.ugc.trill:id/thb", "com.ss.android.ugc.trill:id/tvn",
    "com.ss.android.ugc.trill:id/tum", "com.ss.android.ugc.trill:id/u2f", "com.ss.android.ugc.trill:id/u68",
    "com.ss.android.ugc.trill:id/ubp",
    ":id/tcj", ":id/thb", ":id/tvn", ":id/tum", ":id/u2f", ":id/u68", ":id/ubp",
    "id/tcj", "id/thb", "id/tvn", "id/tum", "id/u2f", "id/u68", "id/ubp",
)
```

---

## 6. Quy Tắc Nghiệm Thu Bắt Buộc (User Directive: Multi-Follow Canary Invariant)

> *"Fl vài lượt nghiệm thu k phải 1. Lí do lỡ lượt đầu tìm đúng nick trong farm thì code cũ nó cũng qua đc mà"*

- **CẤM NGHIỆM THU 1 LƯỢT DUY NHẤT:** Khi kiểm chứng sửa logic cuộn/lọc nick ngoại của Mode 2, nếu chỉ chạy 1 lượt follow (`budget=1`), runner có thể tình cờ bấm đúng nick farm nằm ngay đầu trang $\rightarrow$ không chứng minh được khả năng bỏ qua nick ngoài hay cuộn trang.
- **BẮT BUỘC NGHIỆM THU MULTI-FOLLOW (n >= 3-4 lượt liên tiếp):**
  - Chạy với tài khoản sạch (`fail_streak = 0`, `follow_failed = False`).
  - Thiết lập budget phiên >= 3-4 lượt.
  - Phải thấy rõ telemetry: Mode 2 lướt qua các tài khoản ngoài farm (`session_external_seen`), cuộn tiếp danh sách và follow liên tục nhiều nick farm nội bộ mà không bị giãy `MANUAL_REVIEW`.
  - Nghiệm thu bằng chứng 2 tầng: telemetry `FOLLOW_RESULT` trả về `mode2_followed_count >= 3` VÀ ảnh chụp màn hình Profile thực tế số lượng following tăng tương ứng.
- **QUY TẮC VISUAL EVIDENCE MÀN HÌNH LÕI (USER CORRECTION 01/10/2026):**
  - Khi nghiệm thu canary cho Mode 2 (hoặc bất kỳ flow quan hệ nào), **BẮT BUỘC chụp ảnh ngay tại màn hình thao tác lõi** — tức là màn hình danh sách **Đã follow (Following)** của nick mồi (Anchor), nơi bot đang trực tiếp lọc nick và bấm nút follow.
  - **TUYỆT ĐỐI CẤM** chụp màn hình Profile cá nhân hoặc màn hình Home ngoài luồng rồi gửi báo nghiệm thu, vì ảnh profile cá nhân không chứng minh được runner có thực sự vượt qua danh sách following của anchor hay không.

---

## 7. Bằng Chứng Thực Tế Nghiệm Thu (Máy 41, 01/10/2026)
- **Thiết bị:** Máy 41 (Serial: `ce031823f9b1903c01`), tài khoản `@thu.trangg584` (Row 1).
- **Kết quả execution:**
```json
FOLLOW_RESULT {
  "machine": 41, 
  "status": "OK", 
  "reason": "", 
  "followed": ["phammai1805", "quch.trangg", "nguyenthanhvy2756", "nguyenkhoi1403"], 
  "skipped": [], 
  "failed_ids": [], 
  "failed": false, 
  "follow_failed": false, 
  "details": {
    "mode2_zero_following_fix": "zero-following-skip-v2", 
    "mode2_followed_count": 4, 
    "mode1_followed_count": 0
  }
}
```
- **Xác nhận thực địa:** Đã lướt qua các nick ngoài như `h.h67426`, `dangmy3001`, `skitezrfa3o`... mà không bị dừng; theo dõi thành công 4 nick farm liên tiếp; chỉ số Đang follow trên profile tăng từ 144 lên 148.
