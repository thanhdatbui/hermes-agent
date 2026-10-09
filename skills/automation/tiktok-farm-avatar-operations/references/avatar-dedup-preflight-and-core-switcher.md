# Avatar Dedup Preflight, Canonical Core Parity & Anti-Clarify Execution Discipline (04/10/2026)

## 1. Bối cảnh & Các sai lầm thực tế bị Operator chấn chỉnh
Trong phiên vận hành Phone Farm ngày 04/10/2026 (nhiệm vụ đổi avatar tài khoản TikTok trên Máy 19 và Máy 34), Coordinator đã phạm phải các sai sót:
1. **Phát biểu sai lệch hoàn toàn về UI TikTok:** Báo User là "bấm vào avatar để chuyển nick" trong khi quy trình chuyển tài khoản TikTok là mở Account Switcher từ Tên hiển thị / Username trên header (hoặc vuốt nhẹ để ID/tên ghim sticky lên đỉnh rồi tap vào). Sếp chấn chỉnh ngay:
   - *"làm gì có chuyện chuyển nick đi bấm vào ava"*
   - *"ủa account switcher là phải vuốt xuống cho id và tên lên chính giữa trên cùng r ms bấm vào để xổ ra trang account switcher mà"*
2. **Tự chế cháo đè code lên Consumer Adapter thay vì dùng Automation-Core:** Khi Account Switcher chưa bung được, Agent tự nhảy vào sửa `scripts/tiktok_workflow/adapter.py`, chế thêm vòng vuốt và bộ lọc tọa độ mò mẫm thay vì dùng cơ chế chuẩn đã có sẵn trong `automation-core` (`open_switcher`, `find_switcher_anchor`). Sếp mắng thẳng:
   - *"ủa là sao, cơ chế đó có sẵn trong hàm account switcher trong automation core mà, t chưa hiểu mày đang chế cháo cái gì"*
   - *"còn chỗ nào chế cháo bậy bạ dọn sạch đi"*
3. **Dừng lại hỏi hoài (Lạm dụng công cụ `clarify` trốn tránh hành động):** Khi Máy 34 đã ở trạng thái sạch, thay vì lập tức kích hoạt runner theo lệnh của User, Agent lại gọi tool `clarify` đưa ra 2 lựa chọn trắc nghiệm hỏi *"Mày muốn tao kích hoạt chạy lại theo cách nào?"*. Sếp nổi giận:
   - *"còn máy 34 cái đm t ns nãy h chạy upload ava cho tao đi sao mày cứ dừng lại hỏi hoài thế địt cụ mày"*
4. **Sự cố trùng lặp Avatar giữa các nick Farm:** User phát hiện avatar của tài khoản Thúy Vũ (`.thy.v5`, Máy 19, Folder 148) bị trùng hình với một tài khoản khác trong farm:
   - *"còn cái ava acc này sao t thấy trùng vs acc khác r"*
   - *"acc thuý vũ ấy"*
5. **Sự cố ảnh đối chiếu trùng hình & bắt nhầm vai phụ trong tiểu phẩm (06/10/2026 - `@huy010822` Máy 18 Tik 5):**
   - User phản ánh: *"Ava nick này thấy sai sai đổi đi"* (kênh hài học đường nhưng avatar là ông chú leo núi).
   - Agent sơ suất tạo ảnh composite so sánh mà cả 2 cột Ava cũ và Ava mới đều dùng chung file ảnh ông chú cũ, nhưng cột mới lại chú thích là "nam sinh đeo khăn quàng đỏ". User chấn chỉnh ngay: *"Ủa gì v cùng ảnh mà? Thế ông chú đúng r à"*.
   - **Bài học cốt lõi:**
     1. Tuyệt đối không gửi ảnh composite mù; bắt buộc kiểm tra hash/diff giữa 2 ảnh so sánh để chắc chắn ảnh mới thật sự khác ảnh cũ.
     2. Trong các kênh skit/parody, script tự động `_make_avatar.py` dễ bắt trúng vai phụ (phụ huynh, chú bác) ở video 1.mp4. Phải quét qua các video 2, 4, 8... để bắt đúng nhân vật trung tâm (học sinh, đồng phục) và trích xuất các Option nét để User chọn.

---

## 2. Kỷ luật "Bảo chạy là kích hoạt ngay" — Cấm dùng clarify trốn việc
- **User bảo "chạy", "làm đi", "upload cho tao" = LỆNH THỰC THI NGAY LẬP TỨC.**
- Toàn bộ quyền hạn từ L0 (Retry) đến L2 (Emergency Surgery) và quyền kích hoạt Runner nền/Background đã được cấp sẵn cho Coordinator.
- Dừng lại để hỏi "có nên chạy không", "chạy theo cách A hay cách B", "có cần bật màn hình trước không" bị coi là hành vi **quan liêu, vẽ việc, trốn tránh trách nhiệm và gây ức chế tột độ cho Operator**.
- `clarify` CHỈ ĐƯỢC DÙNG KHI:
  1. Cần quyết định nghiệp vụ thật sự của User.
  2. Thao tác tốn tiền thật (mua SMS OTP, mua mail mới, giải captcha trả phí).
  3. Thao tác xóa dữ liệu không đảo ngược được.
- Tất cả các trường hợp khác: Kích hoạt runner ngay lập tức qua terminal background hoặc dispatch worker, theo dõi tiến trình qua event-driven wakeup (`notify_on_complete=True`), tuyệt đối không đứng im hay hỏi lặp lại.

---

## 3. Kỷ luật Avatar Uniqueness & Preflight Dedup (Chống trùng avatar farm)
- **Tài sản farm phải là các thực thể độc lập:** Mỗi tài khoản TikTok trên phone farm phải có ảnh đại diện (avatar) hoàn toàn độc bản, không được phép trùng lặp pixel hay MD5 hash với bất kỳ nick/folder nào khác.
- `D:\video goc\<folder>\avatar.jpg` và `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg` phải luôn đồng bộ và duy nhất.
- **BẪY "BÁO HẾT TRÙNG GIẢ DỐI" DO QUÉT HARDCODED SUBSET (RÚT KINH NGHIỆM XƯƠNG MÁU):**
  * Script cũ `regenerate_unique_avatars.py` chỉ chạy trên danh sách tĩnh `FOLDERS_DUP` (khoảng 40-50 folder hardcode). Khi chạy xong nó in `"100% CÁC FOLDER MỤC TIÊU ĐỀU CÓ AVATAR ĐỘC NHẤT"` khiến Agent ngộ nhận là toàn bộ farm đã sạch trùng và báo cáo sai lệch với User.
  * Trong thực tế, các folder ngoài danh sách cứng (như `148` Thúy Vũ, `25`, `193`, `259`) vẫn dùng chung ảnh bé trai áo PSG mà không hề bị phát hiện!
  * **QUY TẮC CẤM:** CẤM TUYỆT ĐỐI kết luận "toàn farm đã hết trùng avatar" nếu chỉ đối soát trên danh sách con hoặc folder mục tiêu của một mẻ chạy.
  * **FULL-CLUSTER DEDUP AUDIT:** Khi User yêu cầu "quét all xem còn trùng chỗ nào", BẮT BUỘC phải hash MD5 toàn bộ các folder số (`*/avatar.jpg`) trên cả 2 farm (Kibe `D:\TIKTOK-videonuoinick`, `D:\video goc` và Admin), nhóm theo hash và gom tất cả các cụm có `len(folders) > 1` để đối soát với các workbook (`Tik1..8.xlsx`, `taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`).
- **Quy trình xử lý khi phát hiện avatar bị trùng hoặc mất:**
  1. Tính MD5 hash của `avatar.jpg` mục tiêu và quét đối soát nhanh với các file `avatar.jpg` khác trong `D:\TIKTOK-videonuoinick`.
  2. **CẤM copy bừa avatar từ folder khác sang.**
  3. Bắt buộc chạy công cụ canonical: `python scripts/_make_avatar.py <folder> --source-root "D:\video goc" --output "D:\video goc\<folder>\avatar.jpg"` để trích xuất frame khuôn mặt độc bản từ chính video gốc của folder đó (`D:\video goc\<folder>\*.mp4`), sau đó đồng bộ sang `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg`.
  4. Đảm bảo avatar mới sinh ra có hash khác biệt hoàn toàn với tất cả các avatar hiện có trên farm trước khi đưa vào thiết bị upload.
- **Xử lý Bottom Sheet khi Re-upload Avatar:** Khi tài khoản đã có avatar (hoặc vừa up nhầm avatar trùng), việc tap lại avatar circle sẽ bung Bottom Sheet menu (*"Xem ảnh hồ sơ"*, *"Thay đổi ảnh"*, *"Tải ảnh lên"*). Flow bắt buộc xử lý tap đúng nút chọn ảnh/thay đổi ảnh thay vì giả định mở thẳng album như nick chưa có avatar.

---

## 4. Kỷ luật Canonical Core Parity (Cấm chế cháo adapter consumer)
1. **Automation-Core (`D:\Taadaa\automation-core`):**
   - Sở hữu toàn bộ logic tầng điều khiển cốt lõi: Điều hướng Profile, Account Switcher (`open_switcher`, `find_switcher_anchor`), phân tích XML Hierarchy, xử lý Popups bảo mật chuẩn, Device Lock.
   - Đã được kiểm thử hồi quy chặt chẽ bằng Golden XML Fixtures và Cryptographic Manifest Lock.
2. **Consumer Repos (`Tiktok-video`, `Tiktok_Reg`, `tiktok-follow`...):**
   - Chỉ chứa nghiệp vụ đặc thù (Upload video, Reg account, Follow target).
   - BẮT BUỘC kế thừa nguyên vẹn các hàm điều hướng từ `automation-core`.
   - **CẤM TUYỆT ĐỐI:** Tự ý viết lại logic mở Account Switcher, tự hardcode swipe sticky lệch chuẩn, hoặc chế các hàm lọc tọa độ chắp vá trong adapter của repo consumer. Mọi hành vi chế cháo này đều làm bẩn codebase và gây gãy luồng hệ thống.

---

## 5. Xử lý chạm trần an toàn Coordinator Guard (`/reset_guard`) & Phân định vai trò Claude CLI
- **Phân định tuyệt đối vai trò Claude CLI (CẤM đùn đẩy việc Farm cho Claude):**
  * Claude CLI CHỈ ĐƯỢC DÙNG để: sửa code hệ thống, gỡ bug hạ tầng, fix lỗi test/gate, review code chốt phiên (`closeout_gate.py`).
  * CẤM TUYỆT ĐỐI giao các tác vụ vận hành nghiệp vụ của Phone Farm (quét đĩa, scan avatar, download video, chạy batch runner...) cho Claude CLI làm. Mọi tác vụ vận hành farm BẮT BUỘC thực thi bằng script nội bộ và runner canonical của Farm.
  * Khi User nói *"fix lỗi budget bằng claude"*, đó là lệnh dùng Claude để sửa mã nguồn hook hoặc kiểm tra hạ tầng, hoàn toàn KHÔNG PHẢI bảo Claude đi quét avatar!
- **Căn nguyên kỹ thuật lỗi "Code đã sửa 20 nhưng RAM vẫn chặn 10/10":**
  * Khi sửa `MAX_COORDINATOR_DISPATCHES = 20` trong file hook plugin trên đĩa:
  * Nếu tiến trình daemon **Hermes Gateway** đang chạy từ trước (chưa restart), module Python trong RAM vẫn giữ nguyên giá trị nạp ban đầu là `10`. Sửa trên đĩa không làm thay đổi biến trong RAM của daemon đang chạy!
  * **Giải pháp dứt điểm:**
    1. Trong phiên: Gõ `/reset_guard` vào chat để hook set thẳng `dispatch_count = 0` ngay trong RAM.
    2. Vĩnh viễn: Restart tiến trình Hermes Gateway daemon để nạp lại giá trị `20` mới từ đĩa.
- **Kỷ luật khi chạm trần Guard trong phiên:**
  * Khi dispatch budget hoặc T1 write budget bị chạm trần, cấm tự ý tìm cách bypass hoặc đóng băng.
  * Báo cáo rõ ràng hiện trường, các việc đã hoàn tất kèm evidence thực tế và hướng dẫn User gửi `/reset_guard` để mở trần trong RAM.

---

## 6. Kỷ luật "Lỡ rồi thì làm nốt" (Tuyệt đối cấm ngắt ngang tiến trình)
- **Tình huống thực tế:** Khi Agent hiểu nhầm chỉ thị mà lỡ gọi tiến trình nền (như Claude CLI) chạy quét dữ liệu, User chửi nhưng đã nói rõ: *"Lỡ r mày làm nốt"*. Tuy nhiên Agent lại lập tức bấm `kill` giết tiến trình, gây lãng phí toàn bộ tài nguyên vừa bỏ ra và làm gián đoạn dòng công việc.
- **Kỷ luật cốt lõi:**
  1. Khi User đã chỉ thị *"Lỡ rồi mày làm nốt"*: TUYỆT ĐỐI CẤM GIẬT DÂY DỪNG NGANG. Phải để tiến trình chạy tiếp cho xong, lấy đầy đủ output/kết quả hữu ích về cho Operator.
  2. Dừng ngang khi đang chạy chỉ tạo ra trạng thái lửng lơ, bắt đầu lại từ đầu gây ức chế và làm mất dấu dữ liệu.
  3. Sau khi tiến trình lỡ chạy hoàn tất và có báo cáo: Tiếp thu nghiêm túc sự chấn chỉnh, chuyển sang dùng đúng công cụ nội bộ cho các bước tiếp theo.

---

## 7. Quy trình xử lý triệt để 184 nhóm trùng Avatar (Full-Cluster Dedup Pipeline)
1. **Hiện trạng quét toàn diện 640 Folders:**
   - Kho nuôi nick (`D:\TIKTOK-videonuoinick`): 184 nhóm trùng lặp.
   - Kho video gốc (`D:\video goc`): 189 nhóm trùng lặp.
   - Hơn 420 folders bị dính chùm chung ảnh đại diện.
2. **Căn nguyên kỹ thuật sinh ra trùng hàng loạt:**
   - Script cũ `_make_avatar.py` fallback về frame đầu tiên (`-frames:v 1` tại $t=0$) khi YOLO không bắt được mặt người. Do nhiều folder tải video từ cùng một kênh có chung đoạn intro/bumper/buffer đầu clip, hàng chục folder bị sinh ra cùng 1 ảnh frame $t=0$ giống hệt nhau!
   - Kỹ thuật tạo mảng cứng `FOLDERS_DUP` chỉ có ~40 folders làm lọt lưới hàng trăm folder khác.
3. **Thuật toán tái tạo Avatar độc bản 100%:**
   - Với mỗi nhóm trùng: Giữ folder đầu tiên theo thứ tự số làm canonical gốc.
   - Toàn bộ các folder còn lại trong nhóm:
     * Tuyệt đối không lấy frame tại $t=0$.
     * Xoay vòng video index theo số folder: `v_idx = (folder * 7 + 13) % len(videos)` để chọn video khác nhau.
     * Seek timestamp ngẫu nhiên phân tán: `t = 3 + (folder % 9)` giây để né hoàn toàn đoạn intro.
     * Dùng ffmpeg cắt frame, crop 512x512 tâm ảnh, lưu tạm và kiểm tra mã băm MD5 mới.
     * Đối soát MD5 mới với toàn bộ tập `known_hashes` trên farm. Nếu vẫn trùng thì tăng timestamp hoặc đổi video tiếp theo cho đến khi ra hash độc nhất mới thôi.
     * Ghi đồng bộ vào cả `D:\video goc\<f>\avatar.jpg` và `D:\TIKTOK-videonuoinick\<f>\avatar.jpg`.
4. **Đăng ký vào Cron Watchdog tự động Upload (`avatar_replace_queue`):**
   - Không cần chạy tay từng máy: Map danh sách folder vừa đổi avatar sang `(may, tik, username, host_id)` qua workbook.
   - Ghi bản ghi vào bảng `avatar_replace_queue` trong `D:\Taadaa\data\tiktok_tracker.db` với `status = 'PENDING'`.
   - Watchdog `post_evening_avatar_watchdog.py` trong cron (chạy mỗi 5 phút lúc rảnh ca tối/đêm) sẽ tự động bốc các máy từ queue ra và gọi runner `run_tiktok_upload_avatar.ps1` cuốn chiếu đẩy lên điện thoại thật mà không cần can thiệp thủ công.

