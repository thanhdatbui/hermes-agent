# Bài Học Case Máy 8: Bẫy "Hypothesis Roulette", Ngộ Nhận Toạ Độ Tâm x=540 Là Whitespace & Kỷ Luật "Ground Truth First"

## 1. Bối cảnh & Hiện tượng (Sự cố Máy 8 ngày 07/09/2026)
- **Cảnh báo farm:** `[FARM ALERT: MÁY 8] DỪNG PHIÊN - Nick: tolmavhj12k (Row 1) - profile username still mismatched after switch`.
- **Hiện trường:** TikTok 46.7.3 trên Samsung Galaxy S7 (`98862733584d384151`). Tài khoản hiện tại trên máy là Donie (`@donieovhdvc`). Tài khoản mục tiêu là `tolmavhj12k`.
- **Người dùng cảnh báo gắt:** *"Mày lại bắt đầu over engineer r phải k"*, *"Hqua t vs claude đã siết chặt để mày k bị over engineer. Nay lại tái diễn, gọi claude cli ra điều tra cho tao"*.

---

## 2. Chuỗi Sai Lầm Chí Tử: Bẫy "Hypothesis Roulette" (Xoay Vần Giả Thuyết)

Coordinator đã thay đổi 3 giả thuyết nguyên nhân gốc rễ qua 6 lượt mà **chưa từng một lần quan sát màn hình thực tế của Máy 8 sau khi thực hiện thao tác**:

| Lượt | Giả thuyết đưa ra | Đã xem màn hình thật chưa? | Hành động đẻ hạ tầng (Over-engineering) |
| :--- | :--- | :--- | :--- |
| **Lần 1** | Cho rằng bị Feed Drift (pattern-match từ Case 79) | ❌ Không xem màn hình | Dispatch worker kiểm tra code `feed_swipe_smoke.py`. |
| **Lần 2** | Canary B4 dừng phiên do mismatch | ❌ Không xem màn hình | Đẻ tiếp worker Canary. |
| **Lần 3** | Cho rằng $x=540$ là "dead whitespace bên phải" của hàng switcher | ❌ Không xem màn hình | Commit `60b3253`: Sửa code ép clamp toạ độ về inner TextView con ($x \approx 393$). |
| **Lần 4** | Va chạm device lock với tiến trình mẹ PID 51004 | ❌ Không xem màn hình | Loay hoay giải phóng lock. |
| **Lần 5** | Tự ý chạy PowerShell Canary đồng bộ tại session chính | ❌ Không xem màn hình | Session chính bị treo cứng 600s dính timeout tool terminal. |
| **Lần 6** | Cho rằng lệnh `input tap` 0ms bị nuốt | ❌ Không xem màn hình | Lại đổi sang giả thuyết giữ chạm 120ms (`input swipe`), dispatch worker sửa code tiếp. |

---

## 3. Phân Tích Kỹ Thuật Khách Quan (Audit từ Claude CLI Opus High)

1. **Hiểu lầm số học sơ đẳng về layout Android:**
   - Container hàng tài khoản `com.ss.android.ugc.trill:id/lkp` là full-width `[0, 600][1080, 816]`.
   - Toạ độ $x = 540 = 1080 / 2$ chính là **tâm ngang chính xác** của một button full-width, là điểm tap đáng tin cậy nhất.
   - Việc ngộ nhận $x=540$ là "dead whitespace" rồi commit `60b3253` ép tap vào $x \approx 393$ (child TextView `clickable=false`) **chính là nguyên nhân gây ra regression làm Máy 8 trượt click**.
2. **Sự thật trần trụi khi lấy Ground Truth quan sát thực tế:**
   - Khi revert commit `60b3253` và gửi lệnh `input tap 540 708`:
     * Bottom-sheet lập tức đóng lại và TikTok chuyển nick sang `tolmavhj12k` ngay lập tức!
     * Trên Profile, tài khoản đã đổi thành công sang `@tolmavhj12k` (Display Name hiển thị là `Linhnguyen1707`).
     * Ngay sau khi switch, TikTok hiện popup **"Follow bạn bè của bạn"** (`com.ss.android.ugc.trill:id/yxi`) che toàn bộ màn hình Profile, khiến các bước kiểm tra danh tính tiếp theo bị chặn.
3. **Bản chất của Over-engineering trên LLM:**
   - Không phải do viết code dài hay ngắn, mà là do **"debug mù" (blind debugging)**.
   - LLM có thiên hướng bẩm sinh "narrative bias / hypothesis spinning": tự thêu dệt các kịch bản logic trong đầu thay vì đi kiểm chứng bằng chứng vật lý.
   - Mỗi giả thuyết ảo lại kích hoạt bản năng "đẻ hạ tầng" (dispatch worker, chạy canary dài, lock contention) làm tê liệt toàn bộ phiên làm việc.

---

## 4. Kỷ Luật Cưỡng Chế "Ground Truth First" (Quy Tắc Số 0)

1. **QUAN SÁT HIỆN TRƯỜNG TRƯỚC KHI ĐƯỢC PHÉP ĐƯA GIẢ THUYẾT:**
   - Khi nhận Farm Alert `[MÁY N]`, bước duy nhất và bắt buộc đầu tiên là: lấy ảnh chụp màn hình (`screencap`) và/hoặc dump UI XML qua ATX.
   - **CẤM TUYỆT ĐỐI** đưa ra giả thuyết nguyên nhân gốc rễ hay dispatch worker sửa code khi CHƯA nhìn thấy màn hình thật của thiết bị lúc bị lỗi.
2. **LUẬT 1 BIẾN & QUAN SÁT TRƯỚC KHI ĐỔI TIẾP:**
   - Khi một thao tác không tạo ra kết quả mong muốn (ví dụ tap không thấy đổi trạng thái):
     **Hành động bắt buộc tiếp theo là chụp ảnh màn hình hiện trường (`screencap`) và dump XML ngay sau cú tap**, tuyệt đối không được tự ý đổi sang giả thuyết mới (đổi toạ độ, đổi duration, đổi logic) trước khi nhìn thấy màn hình thật.
3. **CẤM ĐÈ LỆNH CANARY ĐỒNG BỘ 600S TẠI SESSION CHÍNH:**
   - Lệnh Canary chạy trên máy thật cần thời gian dài (6-9 phút). BẮT BUỘC dispatch worker subagent chạy riêng hoặc bọc background, CẤM chạy đồng bộ tại session chính làm đơ giao tiếp với user.
