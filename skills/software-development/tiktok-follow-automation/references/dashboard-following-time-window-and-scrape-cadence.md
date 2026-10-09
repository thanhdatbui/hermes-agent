# Dashboard Following Metric Semantics & Scrape Cadence Protocol

## 1. Bản chất hai tầng quét dữ liệu trên Farm (Scrape Cadence)
- **Quét toàn Farm (Daily Full Scrape — 04:00/07:00 sáng):**
  + Quét toàn bộ 1.000+ tài khoản 1 lần duy nhất mỗi ngày qua Proxy Pool xoay vòng.
  + Không quét toàn farm nhiều lần trong ngày để bảo vệ băng thông proxy 4G và tránh TikTok rate-limit/checkpoint nick do cào diện rộng.
  + Mốc so sánh: Day-over-Day ($T_{\text{today\_04h}} - T_{\text{yesterday\_04h}}$) $\rightarrow$ Con số tăng trưởng Web buổi sáng phản ánh trọn vẹn kết quả tích lũy của các ca chạy hôm qua.
- **Cào riêng theo ca (Pre-Session Scrape $T_0$):**
  + Chỉ cào đúng danh sách nick của các máy tham gia ca/phiên sắp chạy ngay trước khi spawn bot.
  + Mục đích: Lấy mốc tức thời sát giờ nhất để cuối ca ($T_1$) tính $\Delta = T_1 - T_0$ đối soát ngay lập tức xem có bị TikTok Silent Drop hay không.

## 2. Nghịch lý Time-Window Mismatch trên Dashboard Following
- **Vấn đề cũ (Ghép chung 1 dòng):**
  + `📈 Tổng tăng: +126` (Dữ liệu Web cào sáng nay = kết quả ca hôm qua).
  + `🔗 Nội bộ: +0` (Log bot của ngày hôm nay = chưa chạy ca nào).
  + Dẫn đến 2 hiểu lầm nghiêm trọng:
    * Sáng sớm: Tưởng rằng 126 lượt follow tăng kia hoàn toàn là follow ngoài luồng, không có nick nội bộ nào.
    * Chiều tối: Bot hôm nay chạy được +150 lượt, Dashboard hiện `Nội bộ: +150 | Tổng tăng: +126` $\rightarrow$ Số con lớn hơn số cha, phi logic.
- **Quy chuẩn hiển thị chuẩn hóa (Tách bạch 2 tầng):**
  + **Tầng 1 (Đối soát chu kỳ qua):** `📊 Đối soát hôm qua: Bot +X ➔ Web +Y` (so sánh số lượt bot đã bấm hôm qua với số Web ghi nhận tăng sau đợt quét sáng).
    * *Bẫy triển khai (Implementation Pitfall):* Biến `Web +Y` BẮT BUỘC phải là delta Following của ngày hôm qua (`total_delta_following_yesterday` trích từ `get_farm_history()`, ví dụ +118), TUYỆT ĐỐI KHÔNG dùng biến `total_delta_following` của ngày hôm nay (ví dụ +21). Nếu ghép nhầm Bot hôm qua (+104) với Web hôm nay (+21), người vận hành sẽ lầm tưởng hệ thống bị thất thoát 83 follow hoặc dữ liệu ngày hôm trước bị lẫn lộn vào ngày hôm sau.
  + **Tầng 2 (Tiến độ ngày hôm nay):** `⚡ Tiến độ hôm nay: Bot +Z lượt (Web +W)` (tích lũy realtime qua các ca nuôi trong ngày đi kèm với biến động Web delta của ngày hôm nay, ví dụ: `Bot +33 lượt (Web 📈 Tổng tăng: +42)`).

## 2.1. Phân biệt Tăng trưởng Tự nhiên (Organic) vs Follow Nội bộ (Internal Bot)
- **Hiện tượng 1 (Tăng Follower ngoài luồng):** Follower tăng vọt (+140) trong khi Following tăng rất ít (+21) và Bot mới chạy ít lượt (+14).
  + Khi video farm cắn đề xuất (ví dụ tổng tim tăng mạnh +1.895 tim/ngày), người dùng TikTok thật sẽ bấm follow tự nhiên dàn nick (hơn 100 nick cùng tăng 1-3 follow).
  + Bot nội bộ chỉ chạy nhắm mục tiêu một vài nick theo kế hoạch ca (3 nick, 14-17 lượt), tuân thủ safety gate (age >= 21d, video >= 6, rest 1/3).
  + Đây là trạng thái vận hành lý tưởng (Traffic nội dung > Bot follow). CẤM vội vàng tăng bot follow để "cân bằng số" vì sẽ gây rủi ro checkpoint và shadowban.

- **Hiện tượng 2 (Following tự nhiên khi lướt feed ngốn quota Follow chéo):** Số lượt following tăng ngoài kế hoạch (ví dụ Web +70 so với Bot chéo +56, phát sinh 14 lượt follow tự nhiên).
  + **Bẫy ngụy biện tỉ lệ ảo:** CẤM nhìn vào tỉ lệ % trên tổng video lướt (ví dụ 0.5% / 1.300 video) rồi kết luận "thấp và bình thường". Phải đối chiếu số follow tự nhiên với **tổng lượt follow kế hoạch của ca** (14 tự nhiên vs 56 chéo = 25% — mức quá cao!).
  + **Nguy cơ cạn kiệt Daily Action Budget & Nhả follow:** Trong farm, số lượng nick đủ điều kiện đi follow rất ít (đa phần bị gác do dưỡng sinh 1/3, nhả follow, hoặc chưa đủ trust). Mỗi nick có hạn ngạch action hàng ngày rất hạn chế từ TikTok. Nếu nick đem quota đi bấm follow dạo trên For You:
    * Ăn mòn trực tiếp hạn ngạch follow chéo nội bộ.
    * Tỉ lệ nhả follow tự nhiên cực cao (>60%, thực tế 11/17 lượt bị TikTok revert ngay trong ca) do thiếu tín hiệu xem sâu.
    * Kích hoạt spam filter làm ô nhiễm trust của nick khi sang follow chéo.
  + **Kỷ luật cấu hình (Organic Follow Cadence Invariant):**
    * Tỉ lệ follow tự nhiên khi lướt feed (`DEFAULT_FEED_FOLLOW_RATES[FEED_TYPE_FOR_YOU]` và `deep_follow_rate_percent`) BẮT BUỘC duy trì ở mức **SIÊU THẤP (<= 1%)**, tuyệt đối CẤM để mức 5% hay 20%.
    * Không đẻ thêm logic giới hạn theo tuần cồng kềnh; việc dìm xác suất về 1% đảm bảo trung bình cả dàn 80 máy mỗi ca chỉ phát sinh 0-1 lượt ngẫu nhiên, bảo toàn 100% quota cho follow chéo.

## 3. Quy tắc kỹ thuật khi patch Dashboard Following & tránh lỗi hồi quy (Regression Pitfalls)
- **Giữ nguyên nhãn chỉ số âm/dương (`following_delta_label` & `flLabel`):**
  + Khi delta âm (`total_delta_following < 0`), nhãn Web bắt buộc đổi thành `📉 Tổng giảm:` và hiển thị số âm đỏ (ví dụ `-85`).
  + Khi delta dương hoặc bằng 0, nhãn là `📈 Tổng tăng:`.
  + **Pitfall hồi quy:** Trong template HTML và JS auto-refresh `setInterval`, không được hardcode chữ `Web +...` mà phải chèn dynamic label `{following_delta_label}` (Python) và `${flLabel}` (JS) để vượt qua bộ kiểm thử `test_dashboard_follow_breakdown_negative`.

## 4. Kỷ luật Dispatch Worker O(1) trên Monolith Dashboard (> 2.500 dòng)
- File `tiktok_dashboard.py` có độ dài > 2.600 dòng. Worker vào mò bằng `read_file` phân trang sẽ bị cạn kiệt budget 15 calls (Gate 4 Fail-Fast) dẫn đến `files_modified == 0`.
- **Quy chuẩn dispatch O(1):** Coordinator bắt buộc định vị chính xác anchor duy nhất trước (`grep -o ... | wc -l == 1`), cấp exact `old_string` -> `new_string`, và ép worker: **CẤM GỌI READ_FILE ĐỌC TOÀN BỘ FILE, BẮT BUỘC GỌI NGAY TOOL PATCH TRONG TURN 1**, sau đó gọi focused test `pytest` để hoàn tất task trong <= 5 tool calls.

## 5. Bẫy Lệch Mẫu Quét Dở Dang & Thuật Toán Forward-Fill Khắc Phục Delta Ảo
- **Hiện tượng (Phantom Growth / Phantom Drop):**
  + User giật mình chất vấn: *"Ủa từ giữa đêm tới h mà +26 following à t nhớ mấy acc toàn bị khoá k cho đi follow mà"*.
  + Kiểm tra DB thực tế: 0 follow mới từ nửa đêm, bot không chạy lén.
- **Nguyên nhân gốc rễ (Sample Coverage Mismatch):**
  + **Tầng 1 (Lịch sử `get_farm_history`):** Ngày hôm qua cron cào bị dở dang (ví dụ 1.019 / 1.254 nick). Query SQL `GROUP BY substr(timestamp, 1, 10)` chỉ sum được 1.019 nick = 14.763 following (thiếu 235 nick tích lũy 26 following). Sáng hôm nay mới cào 363 nick, hàm kích hoạt fallback đè summary live toàn farm (1.254 nick = 14.789 following) để biểu đồ không bị tụt $\rightarrow$ $\Delta = 14.789 - 14.763 = +26$ ảo.
  + **Tầng 2 (Bảng Live KPI `get_farm_data` - Bẫy rò rỉ delta hôm qua do cào dở dang):**
    * Khi đợt cào buổi sáng (04:00 - 07:00) đang chạy dở dang (ví dụ lúc 05:15 mới cào được một phần farm): Các tài khoản chưa được cào hôm nay có snapshot mới nhất (`rn = 1` trong `LatestCurr`) vẫn mang ngày hôm qua (`T - 1`).
    * CTE `RankedPrev` lọc theo điều kiện `substr(s.timestamp, 1, 10) < substr(c.timestamp, 1, 10)`. Với các tài khoản này, `c.timestamp` là `T - 1` nên `RankedPrev` lấy snapshot của ngày `T - 2`!
    * Kết quả: Mức tăng của ngày hôm qua (`(T - 1) - (T - 2)`) bị cộng dồn vào `total_delta_following` của ngày hôm nay, tạo ra delta ảo (ví dụ: Web báo `+7` trong khi Bot `+0`).
    * Đến khi cron cào hoàn tất toàn farm (ví dụ 07:04), tất cả nick đều có snapshot ngày `T`, `c.timestamp` là `T` và `RankedPrev` là `T - 1`, delta ảo này tự động triệt tiêu về 0.

- **Kỷ luật giải thích cho Coordinator (Tránh ngụy biện Follow tự nhiên ca tối):**
  + **CẤM TUYỆT ĐỐI** giải thích qua loa cho User rằng con số tăng ban đêm/sáng sớm là "follow tự nhiên khi lướt feed ca tối".
  + Thực tế ca nuôi buổi tối/đêm hoàn toàn KHÔNG có follow tự nhiên (thẻ gợi ý bị dismiss vô điều kiện, tỷ lệ dìm <=1%, nick rest/chưa đủ gate bị chặn).
  + Khi thấy sáng sớm `Bot +0 | Web +N (N > 0)`, phản xạ đầu tiên BẮT BUỘC là truy vấn DB kiểm tra xem có phải các nick chưa được cào hôm nay đang bị tính delta hôm qua hay không (Partial Scrape Mismatch).
- **Giải pháp chuẩn hóa (Forward-Fill Cumulative State):**
  + Không dùng `GROUP BY dt` độc lập giữa các ngày.
  + Đọc toàn bộ snapshot theo thứ tự thời gian (`ORDER BY dt ASC`), duy trì state map `users_state[username] = (follower, following, heart, video)`.
  + Với mỗi ngày `dt`, cập nhật các nick có snapshot mới trong ngày; các nick chưa có snapshot mới tự động mang giá trị gần nhất từ ngày trước (forward-fill).
  + Tính tổng ngày từ `len(users_state)` và `sum(users_state.values())`.
  + **Hiệu quả:**
    * Giữ vững số lượng dàn nick $N=1.254$ qua các ngày dở dang.
    * Ngày quét thiếu vẫn phản ánh đúng mốc 14.789 của toàn farm.
    * Ngày hôm sau khi chưa có follow thật thì $\Delta = 0$ chuẩn xác 100%, không sinh delta ảo.

## 6. Cạm bẫy Tìm kiếm trên Dashboard khi đang ở Chế độ Lọc (Search with Active View Filter)
- **Hiện tượng:** User gõ tìm username (ví dụ `masy`, `tooanh`) hoặc máy (`m80`) nhưng bảng báo không có kết quả ("Không tìm thấy tài khoản nào"), khiến user tưởng nick không tồn tại trong farm hoặc bị mất data.
- **Nguyên nhân gốc rễ:** Trong `tiktok_dashboard.py`, hàm `filterData()` áp dụng điều kiện lọc giao diện (`matchQuery && filterView`) đồng thời. Nếu User đang ở tab `📈 Tăng Follower` (hoặc BXH following/tim), điều kiện `delta > 0` bắt buộc thỏa mãn. Nick có follower đứng yên (`delta == 0` hôm nay) sẽ bị ẩn dù tên khớp 100% với query.
- **Quy tắc giải thích & hỗ trợ User:**
  1. Khi User gửi ảnh chụp màn hình thắc mắc nick không hiển thị: Luôn soi mắt (visual eye) kiểm tra nút tab/filter đang active trên thanh điều hướng (ví dụ nút `📈 Tăng Follower` đang sáng active).
  2. Giải thích rõ ràng nguyên nhân do bộ lọc delta đang bật, hướng dẫn User bấm lại `🗂️ Toàn Bộ Farm`.
  3. Đồng thời tra cứu và cung cấp ngay vị trí thực tế của nick: Máy nào, Tik mấy (row index), dòng nào trong `taikhoan_run_safe.xlsx`, chỉ số live (video, follower, following) để user an tâm.


