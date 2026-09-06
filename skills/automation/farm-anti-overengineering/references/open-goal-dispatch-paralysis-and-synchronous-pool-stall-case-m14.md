# Bài Học Sự Cố Kéo Dài 1.5 Giờ: Cạm Bẫy Giao Goal Mở, Worker Analysis Paralysis & Nghẽn Đồng Bộ Delegation Pool (Case Máy 14 - 06/09/2026)

## 1. Hiện Trường & Bối Cảnh Sự Cố
- **Sự cố:** Máy 14 (`ad061603104ee741e2`) dừng phiên nuôi feed TikTok do gặp popup khảo sát độ quan tâm quảng cáo (*"Bạn có quan tâm đến quảng..."* kèm 2 nút `[No]`/`[Yes]` đè trên thanh navigation của sponsored video).
- **Triệu chứng báo cáo:** `popup is not in the shared TikTok allowlist; manual review required; swipe recovery (2 swipes) still stuck`.
- **Hậu quả vận hành:** Tổng thời gian từ lúc nhận alert đến khi nghiệm thu canary xong kéo dài **hơn 1 tiếng 15 phút**, khiến người vận hành nghi vấn về tính trung thực của báo cáo và chất vấn gay gắt: *"Nãy popup đó vẫn đc giữ lock đến khi m chạy canary. Hay m đang báo cáo láo"* và *"Và kiểm tra tại sao xử lý 1 tiếng rưỡi ms xong?"*.

---

## 2. Giải Mã 2 Vấn Đề Người Vận Hành Chất Vấn

### Vấn đề 1: Hiện trường có thực sự được giữ lock & code mới có thực sự xử lý popup không?
- **Sự thật:** Hoàn toàn KHÔNG có chuyện báo cáo láo hay bypass giả mạo.
- **Cơ chế giữ lock:** Theo đúng nguyên tắc an toàn Farm (`máy lỗi giữ lock blocked 1h cho inspect`), Máy 14 được giữ nguyên trạng device lock 1 giờ (`.lock.json`). Các tiến trình batch khác không thể can thiệp hay cướp máy. Màn hình khảo sát quảng cáo vẫn nằm nguyên trên máy thật.
- **Bằng chứng thực thi vật lý (Ground Truth):**
  Trong đợt Canary Test lúc 22:12:42 (15:12:42 UTC), script `run_tiktok.py` trên Máy 14 đã thực sự chạm trán popup khảo sát và kích hoạt đúng handler vừa vá:
  ```json
  {
    "timestamp": "2026-09-06T15:12:42.629035+00:00",
    "step": "feed-session-smoke/swipe_3_after_after_popup_dismiss",
    "detected": "for-you",
    "popup_type": "tiktok_ad_feedback_survey",
    "popup_dismiss_action": "allowlist_dismiss",
    "popup_dismissed": true,
    "popup_dismiss_reason": "tapped_ad_feedback_survey_button",
    "popup_dismiss_selector": {
      "action": "allowlist_dismiss",
      "popup_type": "tiktok_ad_feedback_survey"
    }
  }
  ```
  Artifact chứng cứ gồm cả UI XML dump và ảnh chụp màn hình lúc popup xuất hiện tại `.ai-runs\20260906-220849\machines\machine_14\20260906-220849\artifacts\...\calibrate\tiktok_ad_feedback_survey_dismiss\attempt_1\screen.png`.

---

### Vấn đề 2: Tại sao một ca sửa popup đơn giản lại ngốn tới 1.5 giờ?
Phân rã timeline cho thấy 3 nguyên nhân kỹ thuật chí mạng:

| Khâu thực hiện | Thời gian tiêu tốn | Bản chất kỹ thuật gây chậm trễ |
| :--- | :--- | :--- |
| **Worker 1 (Điều tra mở)** | **37,6 phút** (2.255s) | **Open-Goal Trap & Analysis Paralysis:** Coordinator giao goal mở (*"Điều tra root cause và sửa code..."*). Worker 1 gọi tới 35 tool calls đọc skill_view, đọc file nguồn khổng lồ, inspect XML, đối chiếu `automation-core`. Với độ trễ model ~45-60s/turn, Worker 1 đốt sạch 37,6 phút và chạm trần `exit_reason: max_iterations` (35 calls) **mà chưa hề ghi 1 byte code nào xuống đĩa hay chạy canary**. |
| **Kẹt Background Pool** | *Song hành W1* | Pool delegation báo `at capacity` (`delegation.max_concurrent_children`), ép Worker 1 phải chạy **đồng bộ (Synchronous)**, khóa cứng Coordinator suốt 37 phút khiến Coordinator không thể ngắt giữa chừng. |
| **Worker 2 (Focused Patch)** | **8,8 phút** (528s) | Sau khi W1 cạn calls, Coordinator mới dispatch W2 kèm lệnh cưỡng chế (*"CẤM ĐỌC LAN MAN, PATCH VÀ CANARY NGAY"*). W2 mất 8,8 phút để patch và kích hoạt Canary. |
| **Canary Live Máy 14** | **4,2 phút** | Quá trình PowerShell chạy thật trên thiết bị: connect ADB, kiểm tra profile, thực hiện 3 lượt lướt feed, chạm popup, tự động bấm dismiss và xác thực feed. |

---

## 3. Bài Học Đắt Giá & Kỷ Luật Phòng Chống

### 1. CẤM GIAO GOAL MỞ KHI ALERT ĐÃ CÓ TRIỆU CHỨNG RÕ RÀNG
- Khi Farm Alert đã có:
  + Tên máy, serial, flow (`tiktok-luot nuoi acc`).
  + Ảnh screencap đính kèm (thấy rõ text popup: *"Bạn có quan tâm đến quảng..."*).
  + Chuỗi log lỗi cụ thể (`popup is not in the shared TikTok allowlist`).
- **Hành vi sai lầm:** Giao Worker "điều tra root cause" $\rightarrow$ Worker sẽ đọc lại toàn bộ flow từ đầu, truy vết hàng chục module allowlist trong `automation-core`, ngốn sạch 35 turns mà không sửa được gì.
- **Kỷ luật chuẩn:** Coordinator phải nhận diện ngay đây là ca **Tier 1/Tier 2: Đăng ký Popup Handler mới vào `benign_popup_registry.py`**. Soạn sẵn Patch Contract (tên handler, regex match text tiếng Việt/Anh, hành động tap No/✕ hoặc fallback swipe) và giao thẳng cho Worker thực thi ngay.

### 2. KỶ LUẬT CẮT BỎ ĐIỀU TRA KHI WORKER CHẠY SYNCHRONOUS
- Khi gặp thông báo: `The background delegation pool was at capacity, so the subagent(s) ran SYNCHRONOUSLY`:
  + Session chính sẽ bị đóng băng cho tới khi worker hoàn tất.
  + Do đó, prompt giao cho worker **càng phải ngắn gọn và mang tính áp đặt tuyệt đối** (<= 5-8 tool calls).
  + Bắt buộc kèm chỉ thị: *"CẤM ĐỌC QUÁ 2 FILE. DÙNG PATCH HOẶC SCRIPT PYTHON GHI ĐĨA NGAY TẠI TURN 3. CHẠY CANARY VÀ KẾT THÚC."*

---

## 4. Giải Pháp Cơ Học 3 Trục (Tham Vấn Claude CLI Opus High)

### Trục 1 — Cải Tổ Farm Alert Template (Loại Bỏ Hoàn Toàn Bẫy Monolith)
- **Vấn đề:** Alert template cũ ghi: `Flow .../feed_swipe_smoke.py`. Đây là lời mời gọi vô thức khiến Coordinator và Worker lao vào file monolith 22.000 dòng.
- **Giải pháp:** Alert BẮT BUỘC có trường `CLASS: <POPUP_ALLOWLIST | SELECTOR_DRIFT | NAV_ROUTING | AUTH>`.
- Khối `PATCH_CONTRACT` thay thế toàn bộ mô tả B2 cũ:
  + `ALLOWED_FILES: benign_popup_registry.py` (chỉ đích danh file nhẹ).
  + `FORBIDDEN_FILES: **/flows/*_smoke.py` (khóa cứng monolith).
  + `BUDGET: max_tool_calls=12 ; wall_clock=5m ; read_gate=3`.
  + `EVIDENCE: summary.txt + ALLOWED_FILES`.

### Trục 2 — Bịt Lỗ Hổng "Luồn Cửa Sau" Của WorkerToolGate
- **Lỗ hổng phát hiện:** WorkerToolGate trước đây chỉ đếm `read_file` và `search_files`. Worker 1 đã luồn cửa sau bằng cách gọi hơn 20 lệnh `terminal` (chạy script Python nhỏ đọc file, inspect XML, parse log) mà không hề bị gate chặn!
- **Giải pháp siết cứng:**
  1. `MAX_WORKER_CALLS = 12`: Trần cứng tuyệt đối cho subagent fix alert. Vượt quá 12 calls là hard-block ngay lập tức.
  2. `WRITE_DEADLINE = 4`: Sau 4 tool calls bất kỳ (kể cả terminal read/probe), nếu `write_count == 0` thì khóa luôn cả lệnh terminal probe đọc file, ép worker chỉ được phép ghi code.
  3. Cấm `read_file` trỏ vào `*_smoke.py`.

### Trục 3 — Khóa Cứng Delegation Pool & Chống Block Đồng Bộ
- **Lỗ hổng runtime:** Khi `delegation.max_concurrent_children` (mặc định = 4) bị bão hòa bởi các tiến trình nền, Hermes fallback sang chạy Synchronous/Inline, biến Coordinator thành con tin suốt 37 phút.
- **Giải pháp:** Nâng `max_concurrent_children: 8` trong `~/.hermes/config.yaml`, đồng thời nếu có nguy cơ pool đầy thì Worker bắt buộc phải nhận chỉ thị lean nhất có thể.

### 3. QUY CHUẨN XỬ LÝ AD FEEDBACK SURVEY TRÊN TIKTOK FEED
- Dạng popup khảo sát quảng cáo ("Bạn có quan tâm đến quảng cáo này không?" / "Interested in this ad?") thường xuất hiện dạng overlay hoặc bottom card trên video tài trợ (sponsored ad).
- **Cách xử lý chuẩn hóa 2 lớp trong `benign_popup_registry.py`:**
  1. **Lớp 1 (Tap Button):** Tìm node chứa text `Không`, `No`, `✕`, `Đóng`, `Not now` trong bounds của survey dialog để tap click trực tiếp.
  2. **Lớp 2 (Swipe Bypass):** Nếu không tìm thấy node bấm hoặc sau click vẫn còn overlay, thực hiện 1 thao tác vuốt lên có kiểm soát (`swipe 540 1400 540 500 300`) để lướt qua video quảng cáo an toàn về feed chính.
  3. **Đăng ký với Priority cao (75):** Ưu tiên xử lý tại consumer registry trước khi rơi xuống generic allowlist của core (vốn có điều kiện marker quá khắt khe).
