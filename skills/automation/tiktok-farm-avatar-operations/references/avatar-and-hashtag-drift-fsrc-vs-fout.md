# Đối Soát Avatar & Hashtag Drift: Bẫy Nhầm Lẫn Giữa F_out (Folder Render) và F_src (Folder Nguồn Gốc)

## 1. Bản Chất Sự Cố
Trên farm TikTok (1.280 tài khoản gồm 2 cụm Kibe 1..80 và Admin 201..280):
- Mỗi tài khoản chạy ở một máy `M` và một slot/Tik `Slot` (1..8).
- **Folder nguồn gốc ($F_{src}$)**: Thư mục chứa video gốc ban đầu trong `D:/video goc/`, được tính theo công thức cứng:
  * Cụm Kibe (Máy 1..80): $$F_{src} = (Slot - 1) \times 80 + M$$
  * Cụm Admin (Máy 201..280): $$F_{src} = (Slot - 1) \times 80 + (M - 200)$$
  *(Ví dụ: Máy 201 Slot 2 có $F_{src} = (2 - 1) \times 80 + (201 - 200) = 81$)*
- **Folder render/output ($F_{out}$)**: Thư mục chứa video sau render/dubbing trong `D:/TIKTOK-videonuoinick/` (Kibe) hoặc `D:/TIKTOK-videonuoinick-admin/` (Admin), tương ứng cột `Folder Video` trong Excel `Tik<Slot>.xlsx`.

## 2. Bẫy Nguy Hiểm & Dấu Hiệu Nhận Biết
1. **Lệch Avatar (Avatar Drift)**:
   - Khi tạo hoặc lấy avatar đại diện, nếu nhầm lẫn lấy từ `D:/video goc/<F_out>/avatar.jpg` thay vì `D:/video goc/<F_{src}>/avatar.jpg`, avatar sẽ bị sai lệch hoàn toàn so với nội dung video trên kênh.
   - *Ví dụ thực tế*:
     * Máy 6 Slot 5: $F_{out} = 45$, $F_{src} = (5-1)*80 + 6 = 326$. Video kênh là bé thiếu nhi Tuấn Phong/gia đình vui nhộn, nhưng folder 45 lại chứa ảnh avatar con mèo Ba Tư trắng $\rightarrow$ Kênh trẻ em hiển thị avatar con mèo!
     * Máy 63 Slot 3: $F_{out} = 499$, $F_{src} = (3-1)*80 + 63 = 223$. Video kênh là bạn nam tập gym cởi trần 6 múi, nhưng folder 499 lại chứa ảnh avatar nữ anime tóc tím $\rightarrow$ Kênh gym nam tính hiển thị avatar nữ!
2. **Lệch Niche & Hashtag (Hashtag Drift)**:
   - Tương tự, nếu bảng Excel hoặc script phân loại gán nhầm Keyword/Hashtag theo $F_{out}$ hoặc nhầm lẫn giữa dải folder, video tải lên sẽ mang hashtag rác (ví dụ video gym bị gán tag `#marketing`, video trẻ em bị gán tag `#thoitrang`).

## 3. Quy Trình Chuẩn Bị & Khắc Phục Avatar O(1)
1. **Tính toán chính xác $F_{src}$**:
   - $F_{src} = (Slot - 1) \times 80 + M$.
   - Kiểm tra các video trong `D:/video goc/<F_{src}>/` và thư mục frames `D:/video goc/<F_{src}>/.avatar_work/representative_frames/` để xác định đúng nhân vật/chủ thể chính của kênh.
2. **Crop Avatar Theo Chuẩn Invariant Của Farm**:
   - Kích thước: Chuẩn vuông `512x512` (hoặc `1080x1080`).
   - Tỷ lệ bố cục: Mặt ở khoảng 15–25% phía trên ($cy \approx 0.2 \times H$), khoảng trống đỉnh đầu (headroom) vừa đủ, **cấm cụt đầu**.
   - Kiểm tra bằng `browser_vision` tận mắt trước khi gửi hoặc upload.
3. **Đồng Bộ Hai Đầu Thư Mục**:
   - Copy file `avatar.jpg` chuẩn vào cả:
     * `D:/video goc/<F_{src}>/avatar.jpg`
     * `D:/video goc/<F_{out}>/avatar.jpg` (để mọi script dù đọc nhầm $F_{out}$ hay $F_{src}$ đều lấy đúng avatar).
4. **Khóa Bảo Vệ Tránh Script Quét Đè (SSOT Protection)**:
   - Thêm cả 2 số folder ($F_{src}$ và $F_{out}$) vào danh sách `protected_folders` và mapping `accounts` trong CẢ 2 file registry:
     * `D:/Taadaa/data/manual_avatar_protected_folders.json`
     * `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`
5. **Cập Nhật Keyword & Hashtag SoT Trong Excel**:
   - Cập nhật lại cột `Keyword Video` và `Hashtag Pool` trong `Tik<Slot>.xlsx` (sheet active) và sheet `Hashtag theo Folder` đúng với chủ đề thực tế của video kênh (ví dụ: `Gym` cho nam cơ bắp, `Chăm sóc bé` cho trẻ em/gia đình).
   - Đặt cột `Avatar` trong `Tik<Slot>.xlsx` thành `PENDING` (thay vì `OK`) để bộ lọc `resolve_avatar_pending_machines.py` nhận diện máy cần up avatar mới.
   - **Khóa Cứng Chống Script Quét Đè (Hard-Lock Manual Hashtags Invariant)**: Khi operator đã fix tay hashtag/niche cho một kênh, bắt buộc kích hoạt `is_folder_avatar_protected(F_src)` trong cả 2 file `manual_avatar_protected_folders.json`. Script `sync_all_tik_keywords.py` khi quét qua các folder này BẮT BUỘC phải skip (`continue`), tuyệt đối không đè lại dữ liệu từ database trung tâm. Đồng thời cập nhật tận gốc cột `niche` trong database nguồn để ngăn ngừa tái phát vĩnh viễn.
6. **Kích Hoạt Hàng Đợi Database (avatar_replace_queue)**:
   - Cập nhật SQLite `D:/Taadaa/data/tiktok_tracker.db`:
     ```sql
     UPDATE avatar_replace_queue 
     SET status = 'PENDING', video_goc = '<F_src>', folder_video = '<F_out>', last_error = NULL, updated_at = datetime('now', 'localtime')
     WHERE may = <M> AND tik = <Slot>;
     ```
   - Điều này đảm bảo khi runner batch hoặc watchdog quét qua sẽ tự động nạp avatar lên thiết bị.

## 4. Bẫy False-Negative Khi Audit Niche (Audit Keyword Dictionary Blind-spot)
1. **Bản chất sự cố**: Sau các đợt chuẩn hóa hashtag diện rộng, một số tài khoản vẫn tiếp tục bị gán sai niche (ví dụ kênh bé thiếu nhi Mina nhưng bị gán tag `#gym #tapgym`).
2. **Nguyên nhân gốc rễ**:
   - Script audit (`audit_video_niche_mismatches.py`) sử dụng từ điển `NICHE_KEYWORDS` cố định nhưng thiếu các chủ đề chuyên biệt (ví dụ thiếu `chamsocbe`, `mevabe`, `giadinh`).
   - Mặc dù audio trích xuất từ video nhận diện rõ lời thoại/bài hát thiếu nhi, do không khớp với 10 từ khóa có sẵn nên `detected_niche` trả về `None`.
   - Tool mặc định quy ước `mismatch = False` khi `detected_niche is None`, dẫn đến bỏ sót tài khoản bị lệch và coi là hợp lệ.
3. **Quy tắc khắc phục**:
   - Bổ sung đầy đủ toàn bộ dải niche (đặc biệt `chamsocbe`, `giadinh`, `mevabe`) vào `NICHE_KEYWORDS`.
   - Khi `detected_niche is None` nhưng `current_niche` là các chủ đề dễ lệch (như `gym`, `gaixinh`, `oto`), bắt buộc đánh dấu `AUDIT_SUSPECT` để người hoặc LLM kiểm tra lại thay vì ngầm định `mismatch = False`.

## 5. Tra Cứu O(1) & Nghiệm Thu Thị Giác Tận Mắt (Gate 6 & Reverse Lookup)
1. **Tra Cứu Máy & Slot Từ Screenshot Người Dùng (Reverse Profile Lookup)**:
   - Khi người dùng gửi ảnh màn hình profile TikTok (có username/handle `@<name>`):
   - Truy vấn SQLite `D:/OneDrive/TaadaaData/tiktok_tracker.db` (hoặc `C:/Users/Kibe/iCloudDrive/Backup_OneDrive/TaadaaData/tiktok_tracker.db`):
     ```sql
     SELECT may, tik, username FROM account_mapping WHERE username LIKE '%<handle>%';
     ```
   - Đối soát số lượng video trong lưới 3x3 của ảnh với cột `Video Đã Đăng` trong `Tik<Slot>.xlsx` hoặc `taikhoan_run_safe_combined.xlsx` để chốt chặn chính xác 100% `(M, Slot)`.
   - Tính toán ngay $F_{src} = (Slot - 1) \times 80 + M$.
2. **Soi Mắt Kiểm Tra Khung Tròn Profile (Invariant LLM Soi Mắt)**:
   - Dùng `browser_navigate(url="file:///D:/video goc/<F_src>/avatar.jpg")` và `browser_vision` để trực tiếp kiểm tra ảnh đại diện có đúng là nhân vật xuất hiện trong các video trên kênh hay không.
   - Tạo ảnh mô phỏng khung tròn profile TikTok: vẽ mask hình tròn tâm `(w//2, h//2)`, bán kính $R = \min(w, h)//2$, làm tối 70% vùng nền ngoài vòng tròn.
   - Lưu ra `tmp_<name>_avatar_preview.jpg` và mở qua `browser_navigate` + `browser_vision` để xác nhận tận mắt: mặt ở trục giữa, đỉnh đầu không bị cắt, cằm và vai vừa vặn trong vòng tròn trước khi gửi thẻ `MEDIA:` cho người dùng.
3. **Kỷ Luật Dispatch Worker Khi Hết Ngân Sách T1 Coordinator**:
   - Khi Coordinator đã đạt giới hạn ghi T1 (5 files / 200 dòng): BẮT BUỘC dispatch Worker qua `delegate_task`.
   - Để tránh vi phạm `OUT OF REPO WHITELIST` (chỉ cho phép `D:/Taadaa`), không khai báo file ngoài (`D:/OneDrive/...`) vào trường `FILE:`.
   - Bọc toàn bộ thao tác đồng bộ file, cập nhật SQLite và cập nhật Excel vào một script entrypoint duy nhất trong `D:/Taadaa/tools/<script>.py`.
   - Soạn `OLD_STRING` và `NEW_STRING` trong `<<< ... >>>` với tổng dòng thay đổi `<= 30 dòng` (`DIFF_BUDGET`) để Worker vá và chạy script kiểm chứng focused.
   - **Bắt buộc Gate 4 Fail-Fast & Chuẩn Định Dạng Test**:
     * Prompt EDIT bắt buộc chứa nguyên văn: `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT) và trả về anchor + proposed contract, cấm đốt hết budget để mò file rồi fail im lặng.`
     * Định dạng `FOCUSED_TEST`: Chuẩn `python -m pytest <file.py>::<test_node> -q` hoặc `python -m py_compile <file.py>`.
   - **Đồng Bộ Registry Đôi (Dual Registry Synchronization)**:
     * Cả 2 file `D:/Taadaa/data/manual_avatar_protected_folders.json` và `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json` đều là SSOT cho `manual_avatar_guard.py`. Khi khóa avatar thủ công, bắt buộc đồng bộ cả 2 nơi.
     * Vì Worker bị khóa Scope Lock theo từng file riêng lẻ (`FILE: <path>`), nếu Worker báo dừng do Scope Lock Breach khi cố sửa file thứ 2, Coordinator phải dispatch lượt kế tiếp với scope file thứ 2 hoặc thực hiện qua script tool nội bộ.
   - **Phòng Chống Treo Closeout Gate Do Diff Phình To (CRLF Churn Timeout)**:
     * Khi chạy Closeout Gate (`closeout_gate.py`), nếu repo có file bị convert CRLF/LF diện rộng (ví dụ >100KB diff), Sol High (:20129) sẽ bị timeout đọc sau 300s.
     * Bắt buộc kiểm tra `git status` và `git diff --stat`, unstage các file rác CRLF (`git restore --staged <file>`), chỉ stage và chỉ định đúng `--files <target_file>` để diff review đạt chuẩn O(1) <= 30 dòng, giúp gate hoàn thành duyệt trong vài giây.
   - **Kỷ Luật Phân Loại Closeout Khi User Nói "Done" / "Chốt Phiên" (Operational Scope vs Code Candidate)**:
     * Khi nhiệm vụ chỉ là vận hành dữ liệu farm (crop avatar, cập nhật OneDrive Excel, cập nhật SQLite `avatar_replace_queue`, cập nhật JSON registry local):
     * Phiên này thuộc phân loại `RUNTIME_CONFIG / FARM_OPERATION` (`NO_CODE_CANDIDATE`).
     * CẤM TUYỆT ĐỐI tự ý kéo repo Git ra stage các file dirty lưu cữu từ phiên khác (như `top_left_pencil.py` hay `post_evening_avatar_watchdog.py`) rồi chạy `closeout_gate.py`. Việc này vi phạm ranh giới phiên, gây reject điểm số hoặc timeout giả tạo.
     * Áp dụng `task-scope-and-closeout`: Xuất ngay `SESSION CLOSEOUT RECEIPT` ghi nhận `session_class: RUNTIME_CONFIG`, `commit_required: false`, `gate_status: NOT_APPLICABLE`, chốt phiên an toàn với đầy đủ bằng chứng thị giác `MEDIA:`.

## 6. Quy Trình "Chuẩn Hoá 3 Món" (Ava - Hashtag - Pin) & Thao Tác Cụm Admin Remote
1. **Tiêu Chí Rà Soát 3 Món Chuẩn Farm**:
   - **Ghim Video (Pin Top)**:
     * **Ngưỡng cứng farm:** Chỉ ghim video có lượt xem $\ge 1.000$ views (tối đa 3 video).
     * Nếu tất cả video trên profile đều $< 1.000$ views (ví dụ: 59, 90, 105, 387): **BẮT BUỘC GIỮ NGUYÊN, KHÔNG GHIM**. Báo cáo rõ số view từng clip cho user.
   - **Avatar Mới (Ava)**:
     * Cột `Avatar` trong `Tik<Slot>.xlsx` thường bị ghi nhầm "OK" từ trước dù nick vẫn mang avatar mặc định reg (tranh truyện, sách comic "THE MASK/HERO", hoặc ảnh sàn nhà/sỏi đá do script tự cắt nhầm frame).
     * Bắt buộc dùng `ag_cli ask` hoặc `browser_vision` soi mắt kiểm chứng thực tế.
     * Trích xuất frame nhân vật mới từ video nguồn/render, crop chuẩn ngũ quan & headroom 512x512, tạo marker `.manual_avatar_locked` tại cả 2 đầu thư mục.
   - **Niche & Hashtags**:
     * Kiểm tra nội dung video đã đăng trên profile và kho video đang chờ render (`F_out`) xem có khớp với `Keyword Video` và `Hashtag Pool` trong `Tik<Slot>.xlsx` hay không.
     * Nếu lệch (ví dụ kho video là Biệt thự / Kiến trúc nhưng Excel ghi Ẩm thực), bắt buộc chuẩn hóa lại Excel và tạo marker `.manual_hashtag_locked`.

2. **Kỹ Thuật Thao Tác Remote Cụm Admin (Máy 201..280)**:
   - **Môi trường Python & OpenCV**:
     * Python mặc định của hệ thống trên Admin (`Python 3.11.9`) không có `cv2` (`ModuleNotFoundError`).
     * Môi trường Python chuẩn có đầy đủ OpenCV/automation trên Admin:
       `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe`.
   - **Thực thi script Python đa dòng qua SSH Windows**:
     * Lệnh truyền script Python nhiều dòng qua SSH `-c "..."` dễ bị shell Windows nuốt dấu nháy hoặc ngắt dòng làm lỗi cú pháp.
     * **Cú pháp chuẩn Base64**:
       ```python
       py = r"D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe"
       cmd = ["ssh", "-o", "BatchMode=yes", "admin-farm", f"{py} -c \"import base64; exec(base64.b64decode('{b64_str}').decode())\""]
       ```
   - **Chống Tràn Ngân Sách Ghi T1 Của Coordinator**:
     * Coordinator có giới hạn ghi cứng (5 files / 200 lines). Không tự ý viết nhiều script dò tìm tạm bợ trong `D:/Taadaa/tmp/`.
     * Tận dụng các CLI read-only có sẵn (`python D:/Taadaa/tools/inspect_machine.py <M>`, `python D:/Taadaa/tools/remote_admin_adb.py -s <serial> ...`, `python D:/Taadaa/tools/admin_ssh.py "dir ..."`).
     * Khi cần sửa code tự động hóa phức tạp, bắt buộc lập Patch Contract $O(1)$ và dispatch Worker theo Tiered Workflow.

