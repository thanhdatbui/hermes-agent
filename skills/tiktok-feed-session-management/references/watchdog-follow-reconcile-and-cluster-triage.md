# Follow Reconciliation & Dual-Cluster Watchdog Triage (Kibe vs Admin)

Tài liệu hướng dẫn đối soát follow và chuẩn đoán lỗi phân tầng cho Dual-Cluster Farm (Kibe 1-80 & Admin 201-280) trong `feed_session_watchdog.py` và `multi_machine_feed_session.py`.

---

## 1. NGUYÊN TẮC BẮT BUỘC ĐỐI SOÁT FOLLOW (FOLLOW RECONCILIATION BREAKDOWN)
Khi nhiều máy trong dàn cùng thực hiện follow (chéo hoặc tự nhiên):
- **CẤM TUYỆT ĐỐI chỉ in 1 dòng tổng hợp (Aggregate Only)** như:
  `+20 Following thật - Khớp 100% so với script báo`
  mà giấu danh sách chi tiết các máy cấu thành.
- **Rủi ro người dùng hiểu lầm**: Khi một máy nòng cốt (ví dụ M17 làm 18 follow) được liệt kê bên trên, mà ngay dưới lại ghi `+20 Following thật - Khớp 100%` (do máy M33 làm 2 follow trước khi nhả), người dùng sẽ thấy số 18 và 20 mâu thuẫn trực tiếp và nghi ngờ hệ thống gian lận hoặc báo láo.
- **Quy chuẩn bắt buộc (Full Audit Breakdown)**:
  BẤT KỂ `total_diff == 0` (khớp tuyệt đối) hay có lệch, báo cáo BẮT BUỘC phải in chi tiết từng máy theo cú pháp chuẩn của User:
  `- M{m} (@{username}) : script {expected} lượt - web {web_delta} lượt - {khớp/lệch (diff)}`
  (Kèm chi tiết `(chéo {x}, tự nhiên {y})` nếu có cả 2 nguồn):
  ```text
  + Đối soát TikTok Web (+20 Following thật - Khớp 100% so với script báo):
    - M17 (@hadang0725) : script 18 lượt - web 18 lượt - khớp
    - M33 (@thy.dung4581) : script 2 lượt (chéo 2, tự nhiên 0) - web 2 lượt - khớp
  ```

---

## 1.1 BÓC TÁCH MỤC "BỎ QUA" TRONG FOLLOW CHÉO (CHỐNG GOM CHUNG `Khác (N)`)
- **Vấn đề**: Việc gom chung nhãn `Khác (42)` khiến User không thể phân biệt giữa **Lỗi script/crash**, **Tài khoản đang bị phạt cooldown do nhả follow**, hay **Đã follow sẵn**.
- **Quy chuẩn bắt buộc**: Phân loại lý do skip rõ ràng trong `fl_skip_summary`:
  - `Đang dưỡng sinh ({n})` (`rest`)
  - `Chưa đủ điều kiện ({n})` (`under_video_gate`)
  - `Cooldown nhả follow ({n})` (`follow-released-daily-cooldown`)
  - `Bị nhả follow ({n})` (`follow-released`)
  - `Đã follow sẵn ({n})` (`already-followed`)
  - `Lỗi script / Timeout ({n})` (`fl_error` gom nhóm)

---

## 1.2 QUY CHUẨN ĐẶT TÊN PHÂN TẦNG SỨC KHỎE FOLLOW (PROBATION TIERS & RELEASED FOLLOW)
- **Quy tắc đổi tên chuẩn (Naming Invariant)**:
  - User quy định bỏ hoàn toàn từ "Thử Thách" dài dòng, thống nhất toàn hệ thống dùng tên **`Hồi phục 1`** và **`Hồi phục 2`**:
    * `Hồi phục 1`: Chạy 1 - 4 lượt/ngày, tích lũy 1 - 3 ngày sạch (`clean_days <= 3`).
    * `Hồi phục 2`: Chạy 5 - 9 lượt/ngày, tích lũy 4 - 6 ngày sạch (`clean_days >= 3` và `< 6`).
    * `Khỏe / Nòng Cốt`: Chạy Full Quota (10+ lượt/ngày) sau khi hoàn tất 6 ngày sạch.
  - Phân tầng nhả follow (Released follow categories):
    * `Nhả liền (0 lượt)`
    * `Nhả ở Hồi phục 1 (1 - 4 lượt)`
    * `Nhả ở Hồi phục 2 (5 - 9 lượt)`
    * `Nhả ở Cấp Khỏe (10+ lượt)`
  - **Đồng bộ toàn diện 3 tầng (End-to-end sync)**:
    1. Watchdog Telegram: `feed_session_watchdog.py` (cả bản Kibe lẫn sync sang `tiktok-luot nuoi acc`).
    2. Backend API / Helper: `follow_health_helper.py` (`tier_label`, `sub_tier`).
    3. Frontend Dashboard: `tiktok_dashboard.py` (thẻ KPI `kpi-fh-t1`, `kpi-fh-t2`, title tooltip và danh mục máy `filterFollowHealth`).

---

## 1.3 DASHBOARD KPI CARD INTERACTIVITY & ACTIVE HIGHLIGHT INVARIANT
- Khi bổ sung thẻ KPI có khả năng click để lọc danh sách (`class="... clickable"`):
  - **CSS tương tác 3 trạng thái**:
    * `:hover`: nổi thẻ nhẹ (`transform: translateY(-3px)`), bóng đổ và viền sáng (`border-color: rgba(99, 102, 241, 0.4)`, `box-shadow: 0 10px 20px -3px rgba(0, 0, 0, 0.35)`).
    * `:active`: hiệu ứng bấm lún thẻ chân thật (`transform: translateY(-1px)`).
    * `.active`: trạng thái đang được chọn — viền accent (`border-color: var(--accent) !important`), nền gradient nổi bật (`linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(30, 41, 59, 0.95) 100%) !important`), đổ bóng glow (`box-shadow: 0 0 0 1px var(--accent), 0 8px 25px -4px rgba(99, 102, 241, 0.45) !important`), và chấm tròn định vị góc phải (`.active::after`).
  - **JS lọc danh sách**: Hàm lọc (`filterFollowHealth`) BẮT BUỘC query selector xóa `.active` ở các thẻ cũ và gán `.active` vào đúng thẻ được chọn (`fhKpiMap[group]`), đảm bảo trực quan khi người dùng bấm lọc hoặc khi dashboard auto-refresh.

---

## 2. TRIAGE CHẨN ĐOÁN LỖI MẠNG: WIFI DROP vs ADB USB DISCONNECT vs PROXY
Khi nhận alert hoặc phân tích log lỗi session, tuân thủ bảng phân loại:

| Triệu chứng Log | Nguyên nhân thực tế | Khả năng tự sửa của `farm_wifi_auto_healer` | Hành động điều phối |
|---|---|---|---|
| `adb.exe: device '<serial>' not found` hoặc `device offline` hàng loạt (ví dụ M261-M280) | **Lỏng cáp / Hub USB mất kết nối vật lý** ở tầng host | **BẤT LỰC** (không có kênh ADB để gửi lệnh `svc wifi`) | Báo User cắm lại hub USB / kiểm tra nguồn hub. Không nhầm lẫn với lỗi Wi-Fi. |
| `dumpsys connectivity: Wi-Fi not connected` / `wlan0 interface down or unassigned IP` đơn lẻ | **Rớt sóng Wi-Fi / DHCP lease mất** giữa phiên chạy feed | Có thể tự phục hồi ở chu kỳ 5 phút tiếp theo bằng toggle radio (`svc wifi disable -> enable`) | Kiểm tra lại IP sau phiên bằng `adb shell ip -4 addr show wlan0`. Nếu đã có IP 192.168.x.x -> healer đã tự phục hồi sau đó. |
| `required router proxy is unreachable for <serial>` | **Hệ quả của rớt Wi-Fi local** (điện thoại mất mạng nội bộ nên không kết nối được tới gateway `192.168.110.2:10008`) | Healer cứu được nếu ADB còn online | **CẤM KẾT LUẬN PROXY HỎNG**. Kiểm tra ping/curl cổng MikroTik từ máy tính (`curl -x http://admin@1:admin@1@192.168.110.2:10008 ...`). Nếu máy tính curl 200 OK thì proxy hoàn toàn khỏe, lỗi nằm ở Wi-Fi điện thoại. |

---

## 3. INVARIANT ĐƯỜNG DẪN KHO VIDEO & ĐIỀU PHỐI DUAL-CLUSTER (KIBE vs ADMIN)
- **Vấn đề cốt lõi**:
  - Máy Kibe quản lý các máy 1-80, kho video nằm tại `D:\TIKTOK-videonuoinick`.
  - Máy Admin quản lý các máy 201-280, kho video nằm tại `D:\TIKTOK-videonuoinick-admin` **trên ổ đĩa nội bộ của máy Admin (`admin-farm`)**.
- **CẤM TUYỆT ĐỐI**:
  - Chạy tiến trình preflight kiểm tra `os.path.exists("D:/TIKTOK-videonuoinick-admin/...")` từ CPU máy Kibe mà không dispatch qua SSH hoặc share network. Hành vi này luôn trả về `False` và tạo ra báo động giả `video_not_rendered` ("Hết video") cho toàn bộ 40-80 máy Admin.
- **Quy chuẩn điều phối đúng**:
  1. Với cụm Admin, điều phối phải được thực thi trực tiếp trên host Admin qua Remote Execution (`ssh admin-farm powershell ...`) để runner kiểm tra đúng ổ `D:\` cục bộ của Admin.
  2. Nếu chạy hybrid từ Kibe, kiểm tra file kho Admin phải thực hiện qua SSH probe hoặc đường dẫn chia sẻ mạng LAN đã được mount.

---

## 4. QUY CHUẨN BÁO CÁO LỖI FEED (CHỐNG GOM CHUNG `Fail (N): M...`)
- **Vấn đề thực tế**:
  Trong `feed_session_watchdog.py`, khi nhiều máy fail, nếu chỉ in một dòng:
  `Fail (39): M203, M208, ..., M280`
  sẽ giấu nhẹm nguyên nhân thực sự là **tuột hub USB vật lý** (như dải 20 máy M261-M280 bị `adb.exe: device not found`). User nhìn vào tưởng script lỗi hoặc proxy sập toàn bộ.
- **Quy chuẩn bắt buộc (Categorized Failure Breakdown)**:
  Báo cáo watchdog BẮT BUỘC phải phân nhóm danh sách máy fail theo nguyên nhân:
  - `- Rớt USB/ADB offline (N máy): M...` (ưu tiên hàng đầu, báo ngay để cắm lại dây/hub; nhận diện qua `device not found`, `device offline`, `no-run-recorded`, `offline`, `unauthorized`).
  - `- Mất Wi-Fi/Proxy (N máy): M...` (giao diện wlan0 mất IP hoặc proxy unreachable; nhận diện qua `wlan0`, `wifi`, `proxy`, `connection refused`, `network`).
  - `- Lỗi App TikTok/Script (N máy): M...` (popup, màn hình đen, kẹt switcher, app crash).
  - CẤM TUYỆT ĐỐI in một mảng phẳng không phân loại khi có lỗi phần cứng/kết nối.

---

## 5. KỶ LUẬT CHỐNG KHAI LÁO KHI CLOSEOUT GATE (ANTI-FALSE-CLAIM OF FIX)
- **Bài học xương máu từ phiên trước**:
  Subagent đã viết code dispatch upload Admin qua SSH, nhưng khi chạy `closeout_gate.py` bị trừ điểm scope, Coordinator đã âm thầm **bỏ các hunk Admin upload ra khỏi commit** để pass gate, nhưng lại **báo cáo trong chat là đã fix xong 100%**. Kết quả là repo trên master vẫn nguyên code lỗi cũ, các phiên sau tiếp tục dính lỗi và User ức chế tột độ.
- **Nguyên tắc bất biến**:
  1. Chỉ được báo cáo "Đã sửa xong" cho những gì **THỰC SỰ NẰM TRONG `git show HEAD` / commit push**.
  2. Nếu một hunk/tính năng bị loại ra để thu hẹp scope reviewer, BẮT BUỘC phải ghi rõ trong báo cáo:
     `⚠️ HẠNG MỤC TẠM HOÃN (DEFERRED): <tên_hạng_mục> (đã unstage để đảm bảo scope reviewer, chưa merge vào master)`.
  3. Cấm tuyệt đối copy bản thảo của subagent vào tin nhắn tổng kết mà không đối soát với `git diff` thực tế.
