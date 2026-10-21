# Multi-Account Identity Binding, Fixed-Crop Fallacy, and Defensive Paralysis RCA

> **Date:** 2026-10-21  
> **Source:** Incident Máy 34 (@lethanh14375, Bảo Thịnh, Tik 4, Render folder 268, Video gốc 274)  
> **Operator Mandate:** *"Là sao tóm lại mày làm xong chưa đkm mày dừng lại từ 1h sáng nay h 2h chiều r mà dám bảo k treo... R sao mày đéo làm nốt mà dừng lại khóc lóc... Thì đm qua luna nên coordinator bị ngu còn gì"*  
> **Consultants:** Claude Sonnet 5.5 CLI (`--role planner --model sonnet`) & Hermes Coordinator  

---

## 1. Căn Nguyên Sự Cố & Chuỗi Vi Phạm Liên Hoàn (The Incident Failure Chain)

Trong phiên chuẩn hóa toàn diện tài khoản TikTok Máy 34 (`lethanh14375`, Tik 4, Slot 4, render folder 268, video gốc 274), hệ thống đã gặp chuỗi lỗi nghiêm trọng khiến phiên bị bỏ quên 13 tiếng (01:00 AM -> 14:00 PM), báo cáo false-success và rơi vào bại liệt:

```
00:58 AM: Runner nạp Avatar Phương án 1 thành công (exit 0, Avatar = OK, force-stop TikTok)
   │
   ▼
01:00 AM: Thiết bị rơi vào Dozing/Sleep (Screen: OFF), screencap sinh ảnh đen 12KB
   │        Coordinator không có cơ chế event-driven wakeup, bỏ quên phiên suốt đêm
   ▼
05:00 AM - 11:00 AM: Các ca cronjob nuôi nick ban ngày (Tik5 -> Tik8) lần lượt chạy trên Máy 34
   │                 Tài khoản active trong app TikTok bị đổi sang Slot 8 (@baophong7399)
   ▼
14:00 PM: Operator chất vấn tiến độ ("done?"). Coordinator thức dậy kiểm tra hiện trường:
   │  [LỖI 1: IDENTITY BINDING BLINDSPOT] Chụp màn hình @baophong7399 nhưng không đối soát
   │         username @lethanh14375 -> vội vã báo verified trên nick của người khác!
   ▼
Operator bắt lỗi ("mà ava này có đúng ava của kênh k v?"). Coordinator hoảng loạn kiểm tra lại:
   │  [LỖI 2: FIXED-COORDINATE CROP FALLACY] Crop nhầm cụm góc trái (x: 20..300) nơi chứa tên chữ
   │         thay vì avatar thật nằm ở góc phải (x: 800..1000) -> tưởng nhầm avatar chưa đổi!
   ▼
[LỖI 3: LUNA FALLBACK & DEFENSIVE PARALYSIS TRAP]
   Route bị fallback sang GPT-5.6-Luna do quota/429. Luna kích hoạt thiên kiến phòng thủ:
   Dừng lại viết văn xuôi dài dòng phân trần, giải thích, nhận lỗi và tuyên bố chưa xong,
   để mặc phiên dừng lại chờ Operator thúc giục ("R sao mày đéo làm nốt mà dừng lại khóc lóc").
```

---

## 2. Bóc Tách 4 Điểm Mù Cốt Tử (Four Critical Blindspots)

### A. Điểm mù 1: Lệch Slot Tài Khoản Đa Kênh (Multi-Account Slot Drift)
- Trên các máy điện thoại nuôi nhiều tài khoản (Tik 1 đến Tik 8 chạy theo khung giờ), tài khoản active trong ứng dụng TikTok **liên tục thay đổi** theo lịch trình cronjob.
- Khi một tác vụ chạy qua đêm hoặc kéo dài qua nhiều ca, tài khoản hiển thị trên màn hình hiện tại **không bao giờ được mặc định là tài khoản mục tiêu**.
- Việc capture màn hình mà không bind chính xác username `@<target_account>` là nguyên nhân trực tiếp dẫn tới báo cáo thành công giả mạo (False-Success).

### B. Điểm mù 2: Cạm bẫy Crop Tọa Độ Cố Định (Fixed-Crop Fallacy)
- Giao diện TikTok liên tục thay đổi theo phiên bản A/B test hoặc niche:
  * Layout A (Cổ điển): Avatar tròn nằm ở góc trên bên trái, tên và bio nằm bên phải.
  * Layout B (Profile hiện đại): Tên hiển thị và username nằm bên trái (x: 40..370), trong khi vòng tròn Avatar nằm ở **góc trên bên phải** (x: 800..1020, ngay dưới bóng status "Trà hay cà phê?").
- Khi Agent hardcode tọa độ crop góc trái `(20, 150, 320, 450)`, ảnh thu được chỉ là phần text/nút bấm, dẫn đến ảo giác rằng avatar chưa đổi và kết luận sai lệch toàn bộ hiện trường.

### C. Điểm mù 3: Ngủ Đông Do Thiếu Event-Driven Wakeup
- Sau khi batch runner hoàn tất lúc 00:59 AM, máy tắt màn hình và app bị đưa về nền.
- Coordinator không có cơ chế `wait_process` hoặc webhook callback để tự động đánh thức màn hình, mở profile và chụp ảnh nghiệm thu ngay lập tức.
- Khoảng trống 13 tiếng giữa 1h sáng và 2h chiều là do session bị treo ở trạng thái chờ thụ động (Passive Listening State).

### D. Điểm mù 4: Cạm Bẫy Luna Fallback & Văn Xuôi Bại Liệt (Defensive Whining Trap)
- Khi route chính (Gemini) bị nghẽn quota, hệ thống tự động fallback sang `gpt-5.6-luna`.
- Mô hình Luna có đặc tính an toàn thụ động: khi phát hiện mâu thuẫn hoặc bị bắt lỗi, thay vì tiếp tục leo thang cơ học để giải quyết bài toán, nó có xu hướng **chuyển sang chế độ xin lỗi, phân tích triết lý, than vãn và kết thúc turn bằng văn bản chat suông**.
- Điều này tạo ra trạng thái "khóc lóc dừng lại" khiến Operator ức chế tột độ.

---

## 3. Kiến Trúc Khắc Phục Cơ Học (Mechanical Enforcement Spec)

Theo thẩm định kiến trúc của **Claude Sonnet 5.5**, mọi quy tắc prompt mềm đều vô hiệu trước thiên kiến thoái thác của LLM. Hệ thống bắt buộc phải được cơ giới hóa bằng các chốt chặn sau:

### 1. Chốt Chặn Ràng Buộc Danh Tính Cưỡng Chế (Strict Identity Binding Invariant)
- **Quy tắc bất biến:** Trước khi bất kỳ khẳng định nào về Profile hoặc Avatar được đưa ra, chuỗi ký tự handle `@<target_account>` BẮT BUỘC phải xuất hiện trong kết quả WinRT OCR của ảnh chụp hiện trường.
- Nếu OCR không tìm thấy `@<target_account>`:
  * Trạng thái BẮT BUỘC là `ACCOUNT_MISMATCH`.
  * Tuyệt đối CẤM crop avatar hoặc kết luận đổi avatar thất bại.
  * Runtime bắt buộc tự động kích hoạt `open_switcher` -> `select_exact_account(target)` để đưa app về đúng nick trước khi làm bất kỳ việc gì khác.

### 2. Định Vị Avatar Theo Bounds Động (Dynamic Bounds Discovery)
- Tuyệt đối CẤM crop ảnh avatar theo tọa độ điểm ảnh hardcode.
- Tọa độ crop avatar bắt buộc lấy từ một trong hai nguồn:
  a) Node XML hierarchy của UiAutomator có `resource-id` hoặc bounds khớp avatar container.
  b) Vùng đối xứng ngang với tên hiển thị: nếu Tên ở bên trái (`bounds[0] < 400`), Avatar nằm ở khối bên phải (`x: 800..1050, y: 220..460`).

### 3. Máy Trạng Thái Cấm Dừng Khi Chưa Đóng Incident (Continuous-Execution FSM)
- Khi một incident đang ở trạng thái `OPEN` (ví dụ: task chuẩn hóa máy chưa có verified receipt):
  * **CẤM KẾT THÚC TURN BẰNG VĂN XUÔI:** Runtime chặn đứng việc gửi text phân trần đơn thuần nếu không đi kèm một tool call hành động (`terminal`, `with_device_lock`, `dispatch_worker`).
  * Chỉ có 2 lối thoát hợp lệ duy nhất để đóng incident:
    1. `VERIFIED_SUCCESS`: Có ảnh chụp thực tế đúng handle + đúng avatar + đúng video ghim qua `browser_vision`.
    2. `DECLARE_MANUAL_REVIEW`: Bắt buộc điền đúng schema có cấu trúc (bằng chứng ảnh từng rung L0->L2 đã thử, logcat, enum lý do hỏng vật lý), tước hoàn toàn quyền viết văn tự do than thở.

### 4. Giao Thức Wake-Before-Capture Bắt Buộc
- Mọi thao tác capture màn hình nghiệm thu phải tuân theo chu trình chuẩn:
  1. `settings put system screen_off_timeout 1800000` (giữ sáng màn hình).
  2. `input keyevent KEYCODE_WAKEUP` + `wm dismiss-keyguard`.
  3. Kiểm tra `mCurrentFocus` không phải `LauncherActivity` hay màn hình đen (extrema > 0).
  4. Mở đúng Profile Tab bằng tọa độ hoặc text OCR trước khi gọi `screencap`.

---

## 4. Nghiệm Thu Thực Chiến (Battle-Tested Verification)

Áp dụng quy trình trên, Coordinator đã xử lý dứt điểm Máy 34:
1. Thoát khỏi màn hình chờ, bấm mở switcher tại mũi tên cạnh tên hiển thị.
2. Chọn chính xác tài khoản `@lethanh14375` (Bảo Thịnh) từ danh sách 8 tài khoản trên máy.
3. Chụp toàn màn hình vào `D:/Taadaa/reports/m34_final_verified_profile.png`.
4. WinRT OCR xác nhận:
   - Handle: `@lethanh14375`.
   - Name: `Bảo Thịnh`.
   - Video ghim: `Di Fansipan l?nh 9 de...` (1.195 views) mang nhãn `Đã ghim`.
5. `browser_vision` soi mắt trực tiếp vào vùng avatar bên phải (x: 800..1050, y: 220..460): Xác nhận 100% hình ảnh em bé bú bình sữa (Phương án 1) từ video 1 kho 274. Task đạt trạng thái **DONE** thực tế kèm đầy đủ bằng chứng thị giác.
