---
name: tiktok-channel-standardization
description: "Use when standardizing TikTok profiles (bio, pin, avatar)."
---

# TikTok Channel Standardization (5-in-1 Protocol)

## 🛑 NGUYÊN TẮC CỐT LÕI: PROPOSAL-FIRST (CẤM "LẢI NHẢI" KẾ HOẠCH BẰNG VĂN XUÔI)
- **Hành vi cấm kỵ (Anti-Pattern):** Khi nhận ảnh/yêu cầu chuẩn hoá kênh, Coordinator dừng lại gõ chữ phân trần dài dòng, phân tích hiện trạng rồi hỏi "anh có duyệt kế hoạch không" mà KHÔNG có sản phẩm hình ảnh cụ thể. User cực kỳ ghét việc này (*"Là sao nữa ava chuẩn bị lại đâu? Cứ lải nhải đéo làm mệt..."*). Hoặc quay cuồng chạy tool nội bộ đến cháy budget rồi hứa suông *"Em đang cắt..."* làm treo phiên (*"lí do mày treo từ 3h54 sáng tới h vẫn đéo gửi ảnh"*). Đặc biệt: **CẤM TUYỆT ĐỐI hỏi xin xác nhận lại khi User đã phát lệnh chốt/điều chỉnh** (ví dụ: *"Kênh 2 ok, Kênh 1 tạo ava khác"* ➔ BẮT BUỘC thi công Kênh 2 ngay lập tức và xuất ảnh Canvas Kênh 1 mới ngay trong turn; CẤM tóm tắt lại rồi hỏi 'anh có chốt không' khiến User bực bội: *"Làm chưa hay lại khóc lóc đòi tao xác nhận"*). **CẤM TUYỆT ĐỐI bại liệt hỏi lại khi User đã chọn phương án (ví dụ chọn số "4" hoặc PA cụ thể), kể cả sau khi phiên bị ngắt kết nối/reconnect, khiến User bức xúc: *"Tại sao đéo tiếp tục làm mà bại liệt đi hỏi"*. Khi User đã chốt số/phương án, đó là LỆNH THI CÔNG TUYỆT ĐỐI — BẮT BUỘC thi công dứt điểm ngay lập tức.** CẤM cố chấp sinh avatar ảo từ các video b-roll khi chưa đối soát kỹ avatar hiện hữu trên profile gốc khiến User chê (*"ava mày đưa như lồn ấy"*, *"đéo cái nào đúng cả"*).
- **Quy chuẩn bắt buộc (Proposal Canvas First):**
  0. **Kỷ luật Tiếng Việt có dấu chuẩn 100%:** Tuyệt đối CẤM nhả output không dấu cẩu thả (*"Toàn tiếng việt k dấu ấy"*). Mọi phản hồi tới User BẮT BUỘC viết bằng tiếng Việt chuẩn, đầy đủ dấu thanh, mạch lạc, rõ ràng.
  1. **Đối soát Avatar gốc & Khớp đúng Persona cốt lõi (Chống Ảo Giác Rác Ngữ Cảnh):** Trước khi sinh bất kỳ ảnh mới nào, BẮT BUỘC kiểm tra và trích xuất avatar hiện hữu trên profile TikTok (`user_avatar_512.jpg`) và soi mắt bằng `browser_vision`. **CẤM TUYỆT ĐỐI lấy file `avatar.jpg` trên ổ đĩa (`F_src`, `F_vid`) để suy diễn avatar thực tế của Profile:** File trên đĩa thường là ảnh thẻ nam/nữ cũ từ đợt reg nick hàng loạt ban đầu, KHÔNG phản ánh ảnh đại diện thật trên tài khoản. BẮT BUỘC dùng OpenCV crop vùng avatar trực tiếp từ ảnh chụp màn hình User gửi (trên giao diện TikTok Web Safari: tâm avatar thường nằm ở góc trên bên phải `cx ~ 501, cy ~ 206, r ~ 65-70` trên khung 591x1280; trên Android App: nằm ở góc trên bên trái `(75, 150)` hoặc giữa màn hình). Nếu avatar trên Profile đã là hình vẽ chibi/hoạt hình/anime nữ hoặc hình ảnh phù hợp Persona của kênh: BẮT BUỘC ưu tiên đề xuất GIỮ NGUYÊN avatar hiện tại, KHÔNG máy móc ép cắt ảnh video khiến User nổi giận (*"Lồn mẹ mày ảo giác ít thôi có đọc ảnh trc khi gửi tao k thế"*). CẤM TUYỆT ĐỐI bịa đặt mô tả Avatar gốc / dính rác ngữ cảnh ca cũ. Khi tạo avatar mới, BẮT BUỘC trích xuất từ các video chính chủ trên profile. Dùng `video_contact_sheet.py` soi 9 frames trong 1s để chọn clip chuẩn.
  - **BẪY NHẠI LẠI MÔ TẢ ẢO GIÁC TRANG PHỤC / CHỦ THỂ (BLIND COPY-PASTE HALLUCINATION TRAP):** Khi tạo bảng Proposal Canvas mới, Coordinator CẤM TUYỆT ĐỐI lười biếng bê nguyên mô tả text từ lượt chat trước (như nhại lại *"sơ mi trắng", "nữ sinh", "áo khoác dạo phố"* trong khi video thực tế là máy pha cà phê, ẩm thực, hoặc thú cưng). BẮT BUỘC dùng `browser_vision` mở trực tiếp từng ảnh crop avatar ra nhìn tận mắt xem vật thể/nhân vật là gì, màu sắc, bối cảnh ra sao trước khi viết chữ lên Canvas và trước khi soạn text gửi User (*"Sơ mi trắng cái con mẹ mày t đã ép llm đọc ảnh trc khi gửi r sao mày lười thế"*).
  - **BẪY NHẦM LẪN KHO F_SRC VS F_VID KHI SOI NGÁCH KÊNH (WORKBOOK RECONCILIATION TRAP):** Trong các file `Tik*.xlsx`, cột `F_src` đôi khi bị gán nhầm hoặc lưu thư mục nguồn cũ (ví dụ ghi `549` - cà phê), nhưng cột `F_vid` mới chính là thư mục video thực tế đã render và đăng lên kênh (ví dụ `551` - nữ sinh). Nếu chỉ nhìn `F_src` mà không đối soát lưới video thực tế trên web TikTok/profile, Agent sẽ bị dắt mũi sang ngách hoàn toàn sai và sinh avatar lạc quẻ khiến User bức xúc (*"ủa là nick này hay nick nào v?"*, *"chứ sao là nick gái mà mày cứ đòi làm caffe chi v"*). BẮT BUỘC đối soát đồng thời cả `F_vid`, lưới video trên screenshot của User và `F_src` trước khi kết luận ngách. Lưới video thật trên kênh và `F_vid` LUÔN THẮNG `F_src`. Khi video b-roll trên kênh quá xấu, tối hoặc không có góc chân dung đẹp, có thể chủ động dùng AI sinh ảnh chất lượng cao chuẩn ngách để bổ sung phương án.
  - **BẪY ĐƯA ẢNH THUMBNAIL DÍNH CHỮ SỐ, ICON RÁC VÀO CANVAS (DIRTY THUMBNAIL OVERLAY TRAP):** Khi trích xuất ảnh đề xuất từ video hoặc lưới video màn hình, CẤM TUYỆT ĐỐI đưa các ảnh thumbnail bị đè chữ số (như số view `849`, `1.194`), đè icon tam giác (`▷ 7`), dính watermark hoặc góc quay nghiêng/lưng không thấy mặt vào vòng tròn Avatar Proposal. User lập tức phản ứng cực kỳ gay gắt: *"ô cái địt mẹ mày gen ra mấy cái ava như cặc v mà dám đưa cho tao đó hả, t đã thiết kế gate ép mày đọc hình trc khi gửi mà"*. BẮT BUỘC dùng `browser_vision` mở từng ô ảnh ra kiểm tra tính toàn vẹn: chỉ chọn khung hình sạch 100% không dính text/icon đè, khuôn mặt chính diện rõ nét, ánh sáng tốt. Nếu cắt từ video gốc (`.mp4`), phải tua tới đúng giây không có text overlay.
  2. Crop chuẩn $512 \times 512$, tạo preview viền tròn TikTok (`make_circle_preview`). Nếu gặp lỗi C-extension OpenCV do venv xung đột, dùng `ffmpeg` trích xuất frame kết hợp Pillow độc lập để crop và resize chuẩn $512 \times 512$.
  3. Ghép thành bảng **Proposal Canvas** duy nhất (`D:/Taadaa/reports/standardization_previews/avatar_proposals_*.jpg`) chứa đủ phương án kèm tóm tắt toạ độ, niche, bio đề xuất, pin top. **Bắt buộc render chữ tiếng Việt bằng Pillow (`PIL.ImageDraw` + `ImageFont.truetype` font Arial/Tahoma):** Tuyệt đối CẤM dùng `cv2.putText` vẽ tiếng Việt có dấu vì làm vỡ font thành ký tự rác/loằng ngoằng bị coi là cẩu thả/ảo giác (xem Mục 46 trong references).
  4. Đăng ký vision receipt qua `guard_media_vision_gate.create_vision_receipt` hoặc lệnh `--record-vision` là bước cuối cùng trước khi gửi thẻ `MEDIA:`.
  5. **Bắt buộc thẻ `MEDIA:` dòng đầu tiên:** Phản hồi User BẮT BUỘC đặt thẻ `MEDIA:<đường_dẫn_tuyệt_đối>` ở ngay dòng 1. CẤM gõ văn bản mô tả phương án A, B, C, D mà bỏ quên thẻ ảnh khiến User phải hỏi `? Hình đâu`.
  - **Kỷ luật One-Shot End-to-End & Chống Cháy Ngân Sách T1:** Gom toàn bộ luồng trích frame, render canvas và đăng ký receipt vào 1 lệnh chạy duy nhất trong RAM (qua python base64 oneliner hoặc python inline). TUYỆT ĐỐI CẤM tạo hàng loạt file script tạm `tmp_*.py` bằng `write_file`/`patch` làm cháy ngân sách T1 của Coordinator (<= 10 files, <= 500 dòng), dẫn tới kẹt không xuất được thẻ `MEDIA:`.
  7. Khi User phản hồi điều chỉnh ("K1 tạo ava khác", "còn lại xử lý đi"): TUYỆT ĐỐI KHÔNG giải thích lại kế hoạch, phải xuất ảnh phương án mới ngay trong turn hoặc chạy thẳng các runner canonical trên thiết bị. Không để vòng lặp tool làm kẹt phiên.
  8. **Fallback nút "Sửa hồ sơ" Samsung S7 (75, 150):** Nếu runner `do_rename_canonical_runner.py` không bắt được nút qua OCR và bị kẹt ở `state=PROFILE`, tự động fallback tap vào icon bút chì góc trên bên trái `(75, 150)` để mở thẳng `ProfileEditActivity`.

## Trigger & Scope
Áp dụng khi người dùng yêu cầu *"Chuẩn hoá kênh này"* hoặc *"Chuẩn hoá N kênh"* kèm ảnh chụp màn hình Profile TikTok.
Quy trình chuẩn hoá bao gồm trọn gói **5 hạng mục bắt buộc (5-in-1)**:
- **Avatar (Ảnh đại diện):** Khớp với giới tính/chủ thể video (ví dụ: video creator nam thì avatar bắt buộc là nam; video ẩm thực/nấu nướng thì avatar mang tính chất ẩm thực; cấm để avatar nữ cho kênh video nam). **Đặc biệt: Nếu Avatar hiện tại trên Profile đã khớp đúng Persona và ngách video (ví dụ: kênh mèo đã có avatar mèo trắng đồng bộ), BẮT BUỘC giữ nguyên avatar hiện tại làm mặc định, KHÔNG máy móc ép User chọn đổi avatar mới mà lập tức ưu tiên thi công ghim Top video nếu có clip view cao chưa ghim. Đối với các kênh ngách Thiên nhiên, Cây cảnh, Làm vườn, Bonsai, Nông nghiệp: BẮT BUỘC ưu tiên trích xuất hình ảnh cây cảnh, vườn ươm, hoa lá, đồi chè, thiên nhiên xanh mát làm avatar; TUYỆT ĐỐI CẤM ép crop mặt người làm vườn/lao động thô ráp hoặc nhầm sang hình vi khuẩn/kính hiển vi gây mất thẩm mỹ.**
2. **Tên hiển thị (Display Name):** Họ tên tiếng Việt chuẩn hoặc tên teencode tự nhiên của người dùng (ví dụ: `Ngọc TRinh` viết hoa chữ cái phong cách teencode/giới trẻ là **hoàn toàn bình thường và hợp lệ**; CẤM tự ý bẻ sang họ tên hành chính trừ khi User yêu cầu rõ), cấm số/hậu tố rác lúc reg. **CẤM tự ý tạo cờ `.manual_name_locked`** trừ khi User yêu cầu rõ (để bảo lưu quyền đổi tên sau 7 ngày cooldown của TikTok).
3. **Tiểu sử (Bio):** Bắt buộc 100% tiếng Việt có dấu, độ dài $\le 80$ ký tự, nhập qua AdbKeyboard UTF-8 Base64 bằng `do_rename_canonical_runner.py`. **Luôn chủ động lồng ghép lời kêu gọi follow (Call to Action - CTA) tự nhiên, phù hợp với ngách nội dung** (ví dụ: *"Follow kênh cùng vào bếp nhé! ✨"*, *"Follow Trinh xem mẹo bếp ngon nha!"*, *"Nhấn follow xem món ngon mỗi ngày!"*). Xoá sạch các nhãn rác từ đợt reg nick (`Đang hỗ trợ: WWF-UK`, donation badges). Khi User yêu cầu xoá bio / để trống bio ("đổi bio cho rỗng", "đổi bio cho rao", "xoá bio"): BẮT BUỘC chạy `do_rename_canonical_runner.py` kèm cờ `--clear-bio` để xoá sạch tiểu sử về rỗng (`+ Thêm tiểu sử`), tuyệt đối không tự bịa câu bio mới.
- **Ghim bài Top (Pin Top):** Chọn video có lượt xem cao nhất ($\ge 1.000$ views) và chạy `pin_top_videos.py` ghim lên ô số 1 trang cá nhân (nhãn đỏ *"Đã ghim"*). Nếu runner gặp lỗi `PIN_BUTTON_NOT_FOUND` do cây XML của Share sheet không bắt được node: fallback tap trực tiếp vào tọa độ tâm nút Ghim `(831, 1833)` trên màn hình 1080x1920, sau đó kéo vuốt làm mới profile để đối soát video top hoán đổi vị trí lên ô số 1 đầu trang cá nhân (xem Mục 24 trong references).
- **Kỷ Luật Khai Báo Nghiệm Thu Ghim Video:** Nếu trên thumbnail sau khi ghim không có nhãn đỏ "Đã ghim" rõ ràng trong OCR, CẤM TUYỆT ĐỐI đưa từ "nhãn đỏ Đã ghim" vào tin nhắn để tránh bị Gate `guard_media_vision_gate.py` chặn `UNGROUNDED_TEXT_CLAIM`. Phải mô tả trung thực theo vị trí và số view thực tế (xem Mục 26 trong references).
5. **Hashtag & Niche Reconciliation:** Kiểm tra nội dung video thực tế so với cột `Keyword` / `Hashtag` trong `Tik*.xlsx` (tránh bẫy lệch ngách: video đồ ăn nhưng bảng ghi 'Âm nhạc'). Cắm cờ `.manual_avatar_locked` và `.manual_hashtag_locked` tại cả 2 thư mục `F_src` (`D:/video goc/...`) và `F_vid` (`D:/TIKTOK-videonuoinick/...`), đồng thời cập nhật vào `manual_avatar_protected_folders.json` và `manual_hashtag_protected_folders.json`.

---

## 1. Tra Cứu Toạ Độ Farm O(1) Từ Ảnh
- **Bắt buộc:** Từ `@username` trên ảnh, đọc trực tiếp qua tra cứu O(1) song song cả 2 cụm Kibe và Admin:
  - `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` và `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx` (`Accounts` sheet) ➔ `May`, `Device ID` (Serial ADB). Lưu ý: Nick trên cụm Admin (Máy $\ge 200$) nằm hoàn toàn trong thư mục `admin/`!
  - `D:\OneDrive\TaadaaData\kibe\Tik*.xlsx` và `D:\OneDrive\TaadaaData\admin\Tik*.xlsx` (`TaiKhoan` sheet) ➔ `F_vid` (Cột D), `F_src` (Cột E), `Keyword/Niche` (Cột F), `Hashtag` (Cột G).
- **CẤM:** Quét đĩa diện rộng (`os.walk`, recursive glob, `find`) để tìm file. Nếu không thấy ở cụm `kibe`, lập tức kiểm tra cụm `admin` trước khi tìm kiếm khác.
- **Python OpenCV / PIL Runtime Guard:** Môi trường Python 3.12 của hệ thống có thể bị xung đột numpy C-extension từ venv. Khi viết script trích xuất frame/render canvas, luôn chèn tiền tố nạp môi trường chuẩn:
  ```python
  import sys
  sys.path = ["D:/Taadaa/python-envs/automation/Lib/site-packages"] + [p for p in sys.path if "hermes-agent" not in p]
  import cv2
  ```

---

## 2. Các Lệnh Thi Công Canonical (Background Bulkhead Discipline)
- **Lưu ý Device Bulkhead Gate 5:** CẤM chạy runner điều khiển thiết bị ở foreground với `timeout > 60s`. BẮT BUỘC dùng `terminal(command=..., background=True, notify_on_complete=True)` rồi `process(action='wait', timeout=60)`.
- **Cập nhật Bio có dấu:**
  ```bash
  python D:/Taadaa/tools/do_rename_canonical_runner.py --machine <N> --serial <SERIAL> --username <USER> --bio "<BIO_TIẾNG_VIỆT>" --bio-only
  ```
- **Ghim bài Top:**
  ```bash
  python D:/Taadaa/tools/pin_top_videos.py --machine <N> --serial <SERIAL> --account <USER> --min-views 1000
  ```
- **Khóa Avatar & Hashtag:**
  ```python
  # Copy file avatar chuẩn vào F_src và F_vid
  # Touch .manual_avatar_locked và .manual_hashtag_locked tại cả F_src và F_vid
  # Ghi nhận folder vào D:/Taadaa/data/manual_avatar_protected_folders.json & manual_hashtag_protected_folders.json
  ```
- **Kiểm tra Device Lock Ca Nuôi Nick:** Trước khi chạy `--wait-lock`, kiểm tra `cat C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json`. Nếu máy đang được giữ bởi feed session reservation, nạp sẵn file/marker trên đĩa và báo nhường lịch nuôi nick an toàn, không treo chờ quá 300s.

---

## 3. Nghiệm Thu Thực Tế (Visual Evidence Gate 6 & WinRT Backslash Mandate)
- **Account Verification & Profile-Guaranteed Capture Protocol:**
  - **CẤM TUYỆT ĐỐI chụp mù từ Feed:** Khi TikTok khởi động lại sau khi đổi avatar/bio, app luôn vào tab Trang chủ (Feed). Cú tap mù `(970, 1880)` thường bị các lớp phủ video overlay ("Đọc hoặc viết bình luận", popup, live) nuốt mất khiến màn hình kẹt lại ở Feed.
  - **Phương pháp mở Profile chuẩn xác nhất (Runner FSM First):** Sau khi upload avatar hoặc cập nhật bio, BẮT BUỘC chạy `do_rename_canonical_runner.py --machine <N> --serial <SERIAL> --username <USER> --name "<NAME>"`. Runner này tích hợp sẵn FSM nhận diện `state == FEED`, tự động tap lại nút Hồ sơ `(972, 1857)` cho đến khi đạt `state == PROFILE` và tự động lưu ảnh chụp màn hình chuẩn vào `D:\Taadaa\reports\m<N>_<USER>_rename_confirmed.png`.
  - **Kiểm tra OCR đối soát Feed vs Profile trước khi gửi:** Trước khi đính kèm thẻ `MEDIA:`, BẮT BUỘC chạy `run_winrt_ocr.py` và kiểm tra text OCR:
    * Màn hình Profile hợp lệ: BẮT BUỘC chứa các token `Hồ sơ` (hoặc `H6 sd`), `Follower`, `@username`, Tên hiển thị.
    * Màn hình Feed (BỊ CHẶN): Chứa các từ `LIVE`, `Đề xuất`, `Tìm kiếm`. Nếu thấy các từ này, BẮT BUỘC DỪNG LẠI, CẤM gửi ảnh Feed đối phó cho User.
  - **Đánh thức màn hình trước khi chụp:** Nếu màn hình Samsung S7 bị tắt/chuyển sang AOD (ảnh đen 26KB), chạy `python D:/Taadaa/tools/inspect_machine.py <N>` để đánh thức màn hình sáng (`Màn hình: ON (Awake)`) trước khi chụp.
- Bắt buộc kéo ảnh Profile sau khi cập nhật về máy (chỉ chụp khi màn hình ON và runner đã vào Profile, tránh ảnh đen 12KB):
  ```bash
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> shell screencap -p /sdcard/profile_final.png
  python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <SERIAL> pull /sdcard/profile_final.png D:/Taadaa/reports/<FILE>.png
  ```
- **WinRT OCR Backslash Mandate & TTL Expiry:**
  - BẮT BUỘC dùng đường dẫn native Windows `D:\Taadaa\reports\<FILE>.png` (dùng slash `/` sẽ bị lỗi pointer null trong BitmapDecoder PowerShell):
    ```bash
    python D:\Taadaa\tools\run_winrt_ocr.py "D:\Taadaa\reports\<FILE>.png"
    ```
  - **Fresh Receipt Invariant (TTL 180s):** Vision receipt chỉ có hiệu lực trong 180 giây (3 phút). Phải chạy `run_winrt_ocr.py` ngay trong lượt turn chuẩn bị gửi thẻ `MEDIA:`. CẤM chạy OCR từ nhiều turns trước rồi để receipt hết hạn làm kích hoạt `[CONTRADICTION_GATE_TRIGGERED] verdict: NO_RECEIPT`.
- **Quy Tắc Chống Báo Cáo Láo Avatar & Kỷ Luật CẤM LẠM DỤNG CLAUDE CLI:**
  - **CẤM TUYỆT ĐỐI** tin vào log `verified=True` / `AVATAR_SMOKE_SUCCESS` của runner nếu chưa đối soát thị giác trực tiếp trên avatar circle sau khi upload. Runner cũ hay tap mù vào Tile 1 (thường là ảnh screenshot cũ chứa avatar cũ), gây hiện tượng "báo cáo láo" làm User nổi giận (*"Xong cái địt mẹ mày đã thay ava acc 1 đâu... Con mẹ mày lại báo cáo láo"*).
  - **Lệnh CẤM TUYỆT ĐỐI lạm dụng Claude CLI làm nạng chống lưng:**
    * Claude CLI là tài nguyên đắt đỏ, tiêu tốn hạn mức (quota 5h/tuần) quý giá của tài khoản User.
    * **CẤM Coordinator tự tiện gọi `claude -p`** để làm "cặp mắt đi mượn" cho các việc vặt: soi ảnh, crop ảnh, đo tọa độ pixel, chọn ô ảnh trong thư viện, thẩm định chất lượng thay vì dùng script local (*"r fix script chưa? chứ tự nhiên gọi claude cli? t có yêu cầu mày gọi hả?"*).
    * CHỈ ĐƯỢC PHÉP gọi Claude CLI khi: (1) Được User ra lệnh trực tiếp bằng từ khóa rõ ràng ("gọi claude cli", "dùng claude"), hoặc (2) Strike-3 Reviewer Hand-off chính thức theo `HERMES_SUBAGENT_RULES.md` khi Sol Repair không thể giải quyết.
  - **Bắt buộc FIX TRIỆT ĐỂ trong mã nguồn Runner (`state_machine.py`):**
    * Thay vì nhảy vào làm tay chắp vá rồi gọi Claude CLI soi hộ, BẮT BUỘC sửa triệt để thuật toán trong mã nguồn runner (`commit d9cc3db` trong `Tiktok-video`): tại `_select_avatar_from_download`, tích hợp `_avatar_picker_visual_match` so khớp trực quan tự động từng tile ảnh với `expected_path` (ngưỡng similarity $\ge 0.35$). Runner sẽ tự động định vị đúng tile ảnh nguồn thay vì tap mù ô đầu tiên.
  - **Lỗ hổng Hook OCR Mù Bitmap Avatar & Đối soát Hình Học OpenCV Local:**
    * Hook `guard_media_vision_gate.py` chỉ kiểm tra text OCR. Khi trang cá nhân có đủ chữ (Tên, Handle, Bio), Hook cấp vé `PASS` dù hình trong vòng tròn avatar vẫn là hình cũ!
    * Do đó, để đối soát avatar thật: BẮT BUỘC dùng **OpenCV local** (`cv2`) cắt vùng vòng tròn avatar `(800..980, 250..420)` trên ảnh Profile và tính độ tương đồng Correlation/SSIM với file `avatar.jpg` nguồn. TUYỆT ĐỐI CẤM gọi Claude CLI soi hộ và CẤM chỉ nhìn text OCR để kết luận avatar đã đổi.
  - **Luồng upload chuẩn:** Trên Profile tap bút chì `(75, 150)` ➔ "Thay đổi ảnh" `(539, 579)` ➔ "Tải ảnh lên" `(224, 1637)` (né triệt để popup "Hoạt động không có sẵn") ➔ Định vị đúng ô ảnh mục tiêu trong Gallery bằng visual match ➔ Tap `Tiếp (1)` `(921, 1843)` ➔ Tap `Lưu` `(792, 1794)` ➔ Đợi 10s CDN ➔ Tap Back `(80, 140)` về Profile.
- Soi mắt kiểm tra trước khi gửi:
  - Đúng Username, Tên hiển thị chuẩn.
  - Avatar chính trên Profile đã đổi đúng chủ thể mới (nam đeo kính / nữ nấu ăn).
  - Bio tiếng Việt có dấu đầy đủ, sạch đuôi WWF-UK.
  - Video Top có nhãn đỏ "Đã ghim".
- Đăng ký receipt qua `guard_media_vision_gate.py` trước khi đính kèm `MEDIA:<path>` gửi User.

---

## 4. Kỷ Luật "Canh Ca Nuôi Nick Xong Xử Lý" (Feed Session Queue Monitoring)
- Khi User chỉ thị *"Canh ca nuôi xong xử lý 2 acc trong phiên đi"* hoặc *"mày cài watchdog canh hết ca nuôi vào làm cho tao"*:
  1. Giám sát PID tiến trình nuôi nick toàn farm (`run_tiktok.py --mode multi-machine-feed-session`), kiểm tra `C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json` và `serial_<S>.lock.json`.
  2. Với máy đã nhả lock (trạng thái FREE): lập tức giành JIT lock hoặc chạy canonical runner để thi công dứt điểm (update bio, pin top, switch đúng profile để capture evidence).
  3. Với máy còn trong ca nuôi:
     - Chuẩn bị sẵn 100% dữ liệu trên đĩa (avatar $512\times512$, marker `.manual_avatar_locked`, `.manual_hashtag_locked`, sửa file Excel, đăng ký protected folders).
     - **Chủ động cài đặt background watchdog script:** Viết script watchdog chuyên dụng (như `watchdog_m<N>_standardization.py`) polling vòng lặp kiểm tra PID/lock file (sleep 15s), bọc lệnh wake screen, cập nhật Bio UTF-8, upload avatar canonical, capture profile và run WinRT OCR lấy fresh receipt.
     - **Khởi chạy nền an toàn không chặn luồng chat:** Chạy watchdog bằng `terminal(command="python D:/Taadaa/tools/watchdog_m<N>_standardization.py", background=True, notify_on_complete=True)` để hệ thống tự động thức dậy thi công và báo cáo kết quả kèm thẻ `MEDIA:` ngay khi máy nhả lock, cấm ngồi chờ thụ động hoặc hỏi đi hỏi lại.

---

## 5. Tài Liệu Bổ Trợ
- Chi tiết các bẫy thường gặp (lệch ngách, lệch avatar, badge WWF-UK, lỗi viết hoa, post-pin account drift, TTL receipt expiry, UNGROUNDED_OVERRIDE claim tokens, compaction amnesia, kẹt profile do tap mù bio, bại liệt đi hỏi lại, báo tiến độ thuần text kích hoạt MISSING_MEDIA_EVIDENCE, cháy ngân sách T1 khi tạo script tạm, tra cứu cụm Admin >= 200, bẫy rác ngữ cảnh ca cũ & crop lệch avatar web, vỡ font cv2.putText trên Canvas, đọc nhầm file avatar trên đĩa thay vì soi ảnh screenshot gốc, dính marker cấm VISUAL_CLAIM_MARKERS khi hỏi bằng tiếng Việt, lười soi mắt nhại lại mô tả ảo giác trang phục ca cũ, bẫy tự bịa ngách gái xinh khi kho là máy pha cà phê, terminal guard block & tool timeouts, copy_user_img O(1), kỷ luật Safe Feed Session JIT Queue & guard chặn python -c, bẫy ảo giác avatar kho game UI icon nhãn tách cà phê, giải pháp tự sinh ảnh AI Pollinations.ai khi clip video xấu, trích xuất candidate trực tiếp từ lưới video desktop screenshot bằng Pillow O(1) khi máy kẹt feed lock, soạn Bio chuẩn CTA kêu gọi follow, bẫy màn hình AOD 26KB Samsung S7, bẫy chụp lộn màn hình Feed thay vì Profile & giải pháp Profile-Guaranteed Capture Protocol, bẫy cắt trúng khung hình mid-motion xấu miệng méo/mắt nhắm & ảo giác mô tả avatar profile, bẫy lách gate bằng lệnh khống --record-vision & checklist checkpoint thị giác 4 điểm): [`references/standardization-drift-and-pitfalls.md`](references/standardization-drift-and-pitfalls.md) (Xem chi tiết Mục 32, 33, 34, 35, 36, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63 & 64).

