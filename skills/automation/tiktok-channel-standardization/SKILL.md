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
  - **Khai tử triệt để lỗi phun template kỹ thuật `Trạng thái: DEGRADED...` ra Telegram chat (Egress Bug Fix):** Khi tin nhắn có thẻ `MEDIA:` bị gate chặn (do receipt hết hạn hoặc OCR lệch), hàm `_blocked` trong `guard_media_vision_gate.py` từng có lỗi nghiêm trọng: đè toàn bộ tin nhắn bằng `render_degraded_template` khiến User chỉ thấy dòng text debug quái đản (*"Trạng thái: DEGRADED | Mã: UNVERIFIED_BY_VISION ... Bị điên à / mày bị clgt?"*). BẮT BUỘC gate chỉ bóc bỏ thẻ `MEDIA:` vi phạm để giữ nguyên 100% lời nhắn tự nhiên của Coordinator, TUYỆT ĐỐI CẤM để lọt mẫu debug này ra chat Telegram.
  - **Khai tử cờ cấp vé khống & Cơ chế cơ học O(1) chống lười biếng theo tư vấn Claude Sonnet:** CẤM Coordinator tự chạy `--record-vision` khống để lấy vé. Đã tích hợp luật tự động `DIRTY_AVATAR_EVIDENCE` trong `guard_media_vision_gate.py` (tự động REJECT nếu ảnh avatar dính số view/icon play do cắt ẩu từ video grid).
  - **Bẫy quên đính kèm ảnh nghiệm thu sau khi hoàn tất (Missing Proof Trap):** Khi User hỏi kết quả hoặc khi hoàn thành các bước trên máy, Coordinator phải chủ động gửi ngay ảnh chụp màn hình nghiệm thu thực tế Profile kèm thẻ `MEDIA:<path>` ngay trong turn, tuyệt đối CẤM chỉ nói miệng "đã xong" khiến User phải gắt: *"Hình sau khi làm xong trên nick đó đâu"*, *"Hình đâu???"*.
  - **BẪY BÁO CÁO LÁO KHI CHƯA CHẠY RUNNER UPLOAD AVATAR (AVATAR NOT UPLOADED TRAP):** Việc copy file `avatar.jpg` vào kho `F_vid`/`F_src` và cắm marker `.manual_avatar_locked` CHỈ LÀ CHUẨN BỊ TRÊN ĐĨA PC, HOÀN TOÀN CHƯA ĐỔI AVATAR TRÊN TIKTOK! Coordinator CẤM TUYỆT ĐỐI nhầm lẫn giữa việc lưu file trên đĩa với việc đã upload lên máy thật. BẮT BUỘC phải chạy `python D:/Taadaa/tools/run_upload_avatar.py --tik <TIK> --machine <M>` (tham số `--tik` là số nguyên như `7`), chờ runner báo `exit=0, verified=True`, sau đó chụp ảnh màn hình Profile thật, soi mắt thấy đúng ảnh tròn mới thì mới được báo cáo hoàn tất và gửi ảnh cho User (*"Là sao nữa có đổi ava lồn đâu"*, *"Chứ đụ mẹ hqua chốt hình này r mà"*, *"Sao mày đéo làm mà báo cáo láo lếu liên tục v"*).
  - **Kỷ luật xử lý lỗi Provider Upstream / Transient Error:** Khi gặp lỗi upstream `The model provider failed after retries...`, đây là lỗi mạng/provider tạm thời, KHÔNG phải lỗi hệ thống farm. Coordinator phải kiểm tra health `:20129`, giữ bình tĩnh và báo cáo trung thực, tuyệt đối không hoảng loạn hoặc viện cớ để bỏ dở nhiệm vụ.
  - **Bẫy Egress Hook UNGROUNDED_OVERRIDE / UNGROUNDED_TEXT_CLAIM khi gửi kèm MEDIA:** Khi gửi ảnh nghiệm thu màn hình Profile, CẤM viết các claim mang tính hành động chưa có trong OCR (như "đã cập nhật avatar", "ảnh chụp bạn nữ...") vì sẽ kích hoạt hook giật phanh và phun text `Trạng thái: DEGRADED | Mã: UNGROUNDED_OVERRIDE...` ra Telegram chat. BẮT BUỘC liệt kê đúng các token OCR thật của màn hình (Tên, Handle, Bio, views) và mô tả khách quan. Đồng thời lưu ý nâng TTL receipt lên 3600s và chụp/lấy fresh receipt ngay sau khi runner hoàn tất để tránh bị hết hạn (Xem chi tiết Mục 4 & 5 trong `auto-resume-and-evidence-discipline.md`).
  2. Crop chuẩn $512 \times 512$, tạo preview viền tròn TikTok (`make_circle_preview`). Nếu gặp lỗi C-extension OpenCV do venv xung đột, dùng `ffmpeg` trích xuất frame kết hợp Pillow độc lập để crop và resize chuẩn $512 \times 512$.
  3. Ghép thành bảng **Proposal Canvas** duy nhất (`D:/Taadaa/reports/standardization_previews/avatar_proposals_*.jpg`) chứa đủ phương án kèm tóm tắt toạ độ, niche, bio đề xuất, pin top. **Bắt buộc render chữ tiếng Việt bằng Pillow (`PIL.ImageDraw` + `ImageFont.truetype` font Arial/Tahoma):** Tuyệt đối CẤM dùng `cv2.putText` vẽ tiếng Việt có dấu vì làm vỡ font thành ký tự rác/loằng ngoằng bị coi là cẩu thả/ảo giác (xem Mục 46 trong references).
  4. Đăng ký vision receipt qua `guard_media_vision_gate.create_vision_receipt` hoặc lệnh `--record-vision` là bước cuối cùng trước khi gửi thẻ `MEDIA:`.
  5. **Bắt buộc thẻ `MEDIA:` dòng đầu tiên:** Phản hồi User BẮT BUỘC đặt thẻ `MEDIA:<đường_dẫn_tuyệt_đối>` ở ngay dòng 1. CẤM gõ văn bản mô tả phương án A, B, C, D mà bỏ quên thẻ ảnh khiến User phải hỏi `? Hình đâu`.
  - **Kỷ luật One-Shot End-to-End & Chống Cháy Ngân Sách T1:** Gom toàn bộ luồng trích frame, render canvas và đăng ký receipt vào 1 lệnh chạy duy nhất trong RAM (qua python base64 oneliner hoặc python inline). TUYỆT ĐỐI CẤM tạo hàng loạt file script tạm `tmp_*.py` bằng `write_file`/`patch` làm cháy ngân sách T1 của Coordinator (<= 10 files, <= 500 dòng), dẫn tới kẹt không xuất được thẻ `MEDIA:`.
  7. Khi User phản hồi điều chỉnh ("K1 tạo ava khác", "còn lại xử lý đi"): TUYỆT ĐỐI KHÔNG giải thích lại kế hoạch, phải xuất ảnh phương án mới ngay trong turn hoặc chạy thẳng các runner canonical trên thiết bị. Không để vòng lặp tool làm kẹt phiên.
  - **Fallback nút "Sửa hồ sơ" Samsung S7 (75, 150):** Nếu runner `do_rename_canonical_runner.py` không bắt được nút qua OCR và bị kẹt ở `state=PROFILE`, tự động fallback tap vào icon bút chì góc trên bên trái `(75, 150)` để mở thẳng `ProfileEditActivity`.
    9. **Cảnh giác bẫy Layout TikTok Web/Profile mới (Avatar góc trên bên phải):** Trên layout profile mới, Username và Tên nằm bên trái, avatar nằm ở góc trên bên phải `(880..1060, 150..310)` với vùng trống header rộng. CẤM nhầm khoảng trống tự nhiên này thành lỗi "trắng xóa".
    10. **Bẫy tap mù (75, 150) mở ô Search thay vì Edit Profile:** Trên layout mới, góc trên bên trái `(75, 150)` là icon Kính lúp (Search) chứ không phải nút Sửa hồ sơ. Tap mù vào đây sẽ làm bật bàn phím tìm kiếm và văng khỏi Profile. BẮT BUỘC dùng UI dump XML tìm text "Sửa hồ sơ" / "Edit profile" hoặc resource-id để click chuẩn xác.
    11. **Bẫy chụp vội khi vừa mở lại app (Feed Overlay nuốt touch):** Khi TikTok vừa mở lại, app luôn rơi vào Feed. Các overlay video ("Đọc hoặc viết bình luận", popup) sẽ nuốt sạch touch event tọa độ cố định. BẮT BUỘC dùng `open_profile_root` để thoát overlay Feed trước khi chuyển tab và chỉ screencap khi `is_profile_root == True`.
    12. **Bẫy xem trang Profile người khác (Guest Profile view):** Khi xem nhầm trang profile khách, góc trên bên trái sẽ có nút `<` (Back) và dưới avatar có nút màu đỏ "Follow" / "Nhắn tin" thay vì "Sửa hồ sơ". BẮT BUỘC bấm Back `keyevent 4` về root trước khi thao tác switcher.
    13. **Kỷ luật Watchdog Thực Chiến - Cấm Nói Mõm Hứa Suông:** Khi User bảo *"cài watchdog canh hết ca nuôi vào làm cho tao"*, BẮT BUỘC spawn background process thực tế với `notify_on_complete=True`. Không được để tiến trình chết ngầm do timeout subprocess ngắn rồi bỏ quên phiên khiến User bức xúc (*"Mẹ mày ns mõm xong đéo cài watchdog h 23h rồi còn đéo làm xong"*). Bắt buộc duy trì timeout toàn ca $\ge 3600s$, polling interval 15s.

## Trigger & Scope
Áp dụng khi người dùng yêu cầu *"Chuẩn hoá kênh này"* hoặc *"Chuẩn hoá N kênh"* kèm ảnh chụp màn hình Profile TikTok.
Quy trình chuẩn hoá bao gồm trọn gói **5 hạng mục bắt buộc (5-in-1)**:
- **Avatar (Ảnh đại diện):** Khớp với giới tính/chủ thể video (ví dụ: video creator nam thì avatar bắt buộc là nam; video ẩm thực/nấu nướng thì avatar mang tính chất ẩm thực; cấm để avatar nữ cho kênh video nam). **Đặc biệt: Nếu Avatar hiện tại trên Profile đã khớp đúng Persona và ngách video (ví dụ: kênh mèo đã có avatar mèo trắng đồng bộ), BẮT BUỘC giữ nguyên avatar hiện tại làm mặc định, KHÔNG máy móc ép User chọn đổi avatar mới mà lập tức ưu tiên thi công ghim Top video nếu có clip view cao chưa ghim. Đối với các kênh ngách Thiên nhiên, Cây cảnh, Làm vườn, Bonsai, Nông nghiệp: BẮT BUỘC ưu tiên trích xuất hình ảnh cây cảnh, vườn ươm, hoa lá, đồi chè, thiên nhiên xanh mát làm avatar; TUYỆT ĐỐI CẤM ép crop mặt người làm vườn/lao động thô ráp hoặc nhầm sang hình vi khuẩn/kính hiển vi gây mất thẩm mỹ.**
2. **Tên hiển thị (Display Name):** Họ tên tiếng Việt chuẩn hoặc tên teencode tự nhiên của người dùng (ví dụ: `Ngọc TRinh` viết hoa chữ cái phong cách teencode/giới trẻ là **hoàn toàn bình thường và hợp lệ**; CẤM tự ý bẻ sang họ tên hành chính trừ khi User yêu cầu rõ), cấm số/hậu tố rác lúc reg. **CẤM tự ý tạo cờ `.manual_name_locked`** trừ khi User yêu cầu rõ (để bảo lưu quyền đổi tên sau 7 ngày cooldown của TikTok).
3. **Tiểu sử (Bio):** Bắt buộc 100% tiếng Việt có dấu, độ dài $\le 80$ ký tự, nhập qua AdbKeyboard UTF-8 Base64 bằng `do_rename_canonical_runner.py`. **Luôn chủ động lồng ghép lời kêu gọi follow (Call to Action - CTA) tự nhiên, phù hợp với ngách nội dung** (ví dụ: *"Follow kênh cùng vào bếp nhé! ✨"*, *"Follow Trinh xem mẹo bếp ngon nha!"*, *"Nhấn follow xem món ngon mỗi ngày!"*). Xoá sạch các nhãn rác từ đợt reg nick (`Đang hỗ trợ: WWF-UK`, donation badges). Khi User yêu cầu xoá bio / để trống bio ("đổi bio cho rỗng", "đổi bio cho rao", "xoá bio"): BẮT BUỘC chạy `do_rename_canonical_runner.py` kèm cờ `--clear-bio` để xoá sạch tiểu sử về rỗng (`+ Thêm tiểu sử`), tuyệt đối không tự bịa câu bio mới.
- **Ghim bài Top (Pin Top):** Chọn video có lượt xem cao nhất ($\ge 1.000$ views) và chạy `pin_top_videos.py` ghim lên ô số 1 trang cá nhân (nhãn đỏ *"Đã ghim"*). Nếu runner gặp lỗi `PIN_BUTTON_NOT_FOUND` do cây XML của Share sheet không bắt được node: fallback tap trực tiếp vào tọa độ tâm nút Ghim `(831, 1833)` trên màn hình 1080x1920, sau đó kéo vuốt làm mới profile để đối soát video top hoán đổi vị trí lên ô số 1 đầu trang cá nhân (xem Mục 24 trong references).
  - **Bẫy Unpin làm trôi video top cũ khỏi màn hình (Unpin Off-Screen Drift Trap):** Khi profile đã đủ 3 bài ghim và cần tráo video view cao hơn vào, hoặc khi unpin video top cũ để repin đưa về Ô số 1 theo cơ chế LIFO của TikTok: nếu video đó được đăng từ lâu, việc unpin sẽ lập tức đẩy video đó trôi xuống sâu dưới nếp gấp màn hình (off-screen). Nếu runner chỉ đọc các tile trên viewport đầu, nó sẽ không thấy video top vừa unpin (`cand is None`) và fallback repin nhầm video view thấp hơn đang hiển thị! BẮT BUỘC: (1) Luôn unpin video view thấp nhất trước để giải phóng slot (tránh lỗi kịch trần 3 bài ghim); (2) Khi cần ghim lại video top nằm sâu phía dưới, thực hiện vuốt cuộn màn hình (`swipe 540 1600 540 1000 300`) để định vị đúng tile video top đó trên UI dump rồi mới bấm PIN; (3) Sau khi PIN xong, kéo vuốt lên đỉnh trang cá nhân (`swipe 540 500 540 1500 300`) 2 lần + sleep 2s để làm mới profile, đảm bảo video top chiếm đúng Ô số 1 (trên cùng bên trái) theo đúng cơ chế LIFO (xem Mục 73 trong references).
  - **BẪY ĐIỀU KHIỂN NHẦM MÔI TRƯỜNG KHI STANDARDIZE CỤM ADMIN (MÁY >= 200) & BẪY QUÁ 24H TREO PHIÊN CÂM NÍN (Mục 74):**
    * **Phân định môi trường thực thi (Local Kibe vs Admin Remote):** Các máy cụm Admin (Máy $\ge 200$, ví dụ M212) kết nối qua ADB server tại `192.168.110.119:5037`. Chạy trực tiếp các runner điều khiển như `do_rename_canonical_runner.py` trên môi trường local Kibe mà không trỏ remote ADB host sẽ khiến runner không kết nối được màn hình thật, kẹt ở `state=UNKNOWN (splash/dang tai)` liên tiếp rồi abort. BẮT BUỘC thi công máy Admin thông qua `admin_ssh.py` hoặc truyền remote ADB daemon (`--adb-server 192.168.110.119:5037` / tự động thêm `-H 192.168.110.119` khi `MACHINE_ID >= 200`). Đồng thời dùng `tools/remote_admin_adb.py -s <serial> shell input keyevent 224` để đánh thức màn hình Admin trước khi chạy FSM.
    * **Kỷ luật truy tìm Task sau 24h (Chống đoán mò lạc đề):** Khi User hỏi ngắn gọn tiến độ một task cũ (*"làm xong session này chưa"*, *"xong chưa"*): CẤM TUYỆT ĐỐI đoán mò sang các repo dirty khác (Dashboard, OmniRoute...). BẮT BUỘC đọc ảnh đính kèm/ảnh reply gần nhất qua WinRT OCR / `browser_vision` để trích xuất đúng `@username` và toạ độ máy trước khi trả lời (*"Mày bị ngáo à! Hay quá 24h bị xoá hết cache session r"*).
    * **BẪY ẢO GIÁC "PA 1 = GIỮ NGUYÊN AVATAR" KHI CHƯA ĐỐI SOÁT BITMAP THỰC TẾ (AVATAR NOT UPLOADED TRAP):**
      - **Hiện tượng lỗi:** Khi User bảo *"pa 1 trong hình"* hoặc chọn số PA, Coordinator lười biếng nhớ lại mô tả suông cũ hoặc tự suy diễn "PA 1 là giữ nguyên avatar profile", dẫn đến việc chỉ đổi Tên & Bio rồi vội vã báo cáo hoàn tất mà **HOÀN TOÀN CHƯA ĐỔI AVATAR TRÊN THIẾT BỊ THẬT**, khiến User nổi giận (*"Đã đổi ava đâu"*).
      - **Bắt buộc đối soát Bitmap:** CẤM TUYỆT ĐỐI suy diễn "giữ nguyên avatar". BẮT BUỘC trích xuất vòng tròn avatar thực tế trên Profile hiện tại và so sánh trực quan với ảnh PA mà User đã chọn trên Proposal Canvas. Nếu hình trên thiết bị khác với hình User chọn (ví dụ: trên máy là ảnh nam đeo kính, còn PA 1 là ảnh nữ áo tập tank top): **BẮT BUỘC PHẢI CHẠY PIPELINE NẠP AVATAR LÊN THIẾT BỊ THẬT**.
    * **QUY TRÌNH NẠP AVATAR CHUẨN TRÊN CỤM ADMIN (MÁY >= 200):**
      1. **Khử Port 5038 Tranh Chấp WinUSB:** Nếu các máy Admin báo `device not found` hoặc rớt kết nối, kiểm tra và giải phóng ngay cổng 5038 trên Admin host (`192.168.110.119`):
         ```bash
         python D:/Taadaa/tools/admin_ssh.py "python -c \"import subprocess, os; xw=r'C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe'; subprocess.run([xw, '-P', '5038', 'kill-server']) if os.path.exists(xw) else None\""
         ```
      2. **Đồng Bộ File Avatar Lên Cả 2 Host:**
         - Copy file avatar chuẩn $512 \times 512$ vào kho local: `D:\TIKTOK-videonuoinick\<F_vid>\avatar.jpg`.
         - Dùng `sync_avatar_to_admin.py` đẩy sang kho Admin: `D:\TIKTOK-videonuoinick-admin\<F_vid>\avatar.jpg`.
         - Cắm marker `.manual_avatar_locked` và cập nhật protected registries JSON.
      3. **Reset Cột Avatar Trong Workbook:** Trong `D:\OneDrive\TaadaaData\admin\Tik*.xlsx`, set cột `Avatar` của dòng máy đó về rỗng (`None`) để runner không bị bypass.
      4. **Kích Hoạt Runner Upload Trên Admin Host:**
         ```bash
         python D:/Taadaa/tools/admin_ssh.py --timeout 300 "python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <TIK> --machine <M>"
         ```
         Chờ runner báo `exit=0, verified=True` (`AVATAR_SMOKE_SUCCESS`).
      5. **Nghiệm Thu Sau Upload:** Dùng `do_rename_canonical_runner.py` vào lại Profile, thực hiện vuốt kéo làm mới (`swipe 540 500 540 1400 300`), dừng chờ 6–8s cho CDN load bitmap, chụp màn hình và soi mắt qua `browser_vision` xác nhận vòng tròn avatar đã thực sự đổi mới trước khi gửi ảnh cho User.
    * **Kỷ luật chống treo phiên câm nín:** Khi runner gặp lỗi `UNKNOWN` hoặc kẹt ADB, BẮT BUỘC báo cáo ngay hiện trường thực tế (`inspect_machine.py <N>`) và trạng thái BLOCKED, CẤM TUYỆT ĐỐI im lặng biến mất bỏ mặc task treo qua ngày.
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
  - **Cổng Chống Màn Hình Trắng Xóa Do CDN Chưa Load (Mandatory Pull-To-Refresh & 6-8s Delay Gate):** Khi vừa upload avatar xong hoặc vừa vào Profile, app TikTok cần thời gian fetch hình ảnh từ server CDN về cache. Lưới video và avatar thường ở trạng thái placeholder trắng xóa / xám rỗng. BẮT BUỘC: (1) Thực hiện vuốt kéo làm mới `swipe 540 500 540 1400 300`, (2) Dừng chờ đúng 6–8 giây cho CDN tải xong toàn bộ bitmap, (3) Kiểm tra vùng avatar (`img[150:600, 700:1050]`), nếu màu trung bình `mean > 240` (mảng trắng tinh) hoặc `std < 10`: CẤM TUYỆT ĐỐI chụp gửi User vì ảnh chưa load, bắt buộc chờ thêm hoặc refresh lại. (Xem chi tiết Mục 65 trong references).
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
  - **Quick Probe Timeout <= 60s cho run_winrt_ocr:** Hook `HARD GATE #5 - DEVICE BULKHEAD` coi mọi lệnh `run_winrt_ocr.py` là lệnh tương tác thiết bị/chụp màn hình. CẤM gọi foreground mà không đặt timeout (mặc định timeout=None sẽ bị giật phanh chặn đứng). BẮT BUỘC đặt rõ `timeout=30` hoặc `timeout=60` khi gọi `terminal(...)` để lấy receipt nhanh, hoặc dùng `background=True, notify_on_complete=True`.
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
     - **Kỷ Luật "Cài Watchdog Thực Chiến - Cấm Nói Mõm Hứa Suông":** Tuyệt đối CẤM hứa hẹn miệng *"Em đã cài watchdog..."* mà không thực sự spawn background process hoặc để tiến trình crash ngầm do timeout subprocess ngắn làm trễ nải công việc đến đêm muộn (*"Mẹ mày ns mõm xong đéo cài watchdog h 23h rồi còn đéo làm xong"*). Watchdog bắt buộc có timeout toàn ca $\ge 3600s$, polling interval 15s, tự động switch đúng nick (thử cả `@username` có chấm và không chấm nếu switcher báo `ACCOUNT_VERIFY_MISMATCH`), kéo làm mới và chờ CDN load đủ 8s trước khi chụp nghiệm thu. (Xem chi tiết Mục 66 trong references).

---

## 5. Tài Liệu Bổ Trợ
- Chi tiết các bẫy thường gặp (lệch ngách, lệch avatar, badge WWF-UK, lỗi viết hoa, post-pin account drift, TTL receipt expiry, UNGROUNDED_OVERRIDE claim tokens, compaction amnesia, kẹt profile do tap mù bio, bại liệt đi hỏi lại, báo tiến độ thuần text kích hoạt MISSING_MEDIA_EVIDENCE, cháy ngân sách T1 khi tạo script tạm, tra cứu cụm Admin >= 200, bẫy rác ngữ cảnh ca cũ & crop lệch avatar web, vỡ font cv2.putText trên Canvas, đọc nhầm file avatar trên đĩa thay vì soi ảnh screenshot gốc, dính marker cấm VISUAL_CLAIM_MARKERS khi hỏi bằng tiếng Việt, lười soi mắt nhại lại mô tả ảo giác trang phục ca cũ, bẫy tự bịa ngách gái xinh khi kho là máy pha cà phê, terminal guard block & tool timeouts, copy_user_img O(1), kỷ luật Safe Feed Session JIT Queue & guard chặn python -c, bẫy ảo giác avatar kho game UI icon nhãn tách cà phê, giải pháp tự sinh ảnh AI Pollinations.ai khi clip video xấu, trích xuất candidate trực tiếp từ lưới video desktop screenshot bằng Pillow O(1) khi máy kẹt feed lock, soạn Bio chuẩn CTA kêu gọi follow, bẫy màn hình AOD 26KB Samsung S7, bẫy chụp lộn màn hình Feed thay vì Profile & giải pháp Profile-Guaranteed Capture Protocol, bẫy cắt trúng khung hình mid-motion xấu miệng méo/mắt nhắm & ảo giác mô tả avatar profile, bẫy lách gate bằng lệnh khống --record-vision & checklist checkpoint thị giác 4 điểm, bẫy chụp màn hình trắng xóa do CDN/cache chưa load & cổng kiểm tra chống trắng xóa, kỷ luật cài watchdog thực chiến cấm nói mõm hứa suông, bẫy quay cuồng poll log process bị buffer, bẫy gõ lệnh tay ADB bị Hard Gate #5 chặn kèm giao thức Python verifier chuyển tab Profile, bẫy ảo giác nhầm chữ "Follow" trong Bio CTA thành nút đỏ của khách ghé thăm, bẫy gian lận đóng dấu khống --record-vision & cơ chế cơ học O(1) chống lười biếng theo tư vấn Claude Sonnet, và bẫy bại liệt não sau reconnect & kỷ luật auto-resume tiếp tục làm việc dở dang): [`references/standardization-drift-and-pitfalls.md`](references/standardization-drift-and-pitfalls.md) (Xem chi tiết Mục 32, 33, 34, 35, 36, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72 & 73 (Bẫy Unpin làm trôi video top cũ khỏi màn hình & quy trình đưa video top về Ô số 1 LIFO)).
- **Kiến trúc O(1) kiểm định tự động Avatar chống lười biếng & khai tử tự cấp vé khống (Tư vấn Claude Sonnet):** [`references/claude-avatar-governance-o1.md`](references/claude-avatar-governance-o1.md).
- **Kỷ luật đẩy Avatar lên thiết bị thật & Chống báo cáo láo / thiếu ảnh nghiệm thu:** [`references/avatar-execution-and-proof-mandate.md`](references/avatar-execution-and-proof-mandate.md).
- **Kỷ luật gửi ảnh nghiệm thu thực tế & xử lý dứt điểm auto-resume không bại liệt:** [`references/auto-resume-and-evidence-discipline.md`](references/auto-resume-and-evidence-discipline.md) (Xem Mục 1, 2, 3, 4, 6 & Mục 7: Chống hứa mồm không tool, chống bại liệt khóc lóc phân trần, bắt buộc code/test/deploy dứt điểm).
- **Cơ chế ghim bài LIFO & Xử lý trôi video top khi unpin (Off-Screen Recovery):** [`references/lifo-pin-ordering-and-offscreen-recovery.md`](references/lifo-pin-ordering-and-offscreen-recovery.md).

---

## 6. Kiến Trúc Chuẩn Hoá Bài Ghim Định Kỳ (Event-Driven Pin Standardization via Web Dashboard)
- **Quy tắc thiết kế theo chỉ thị User (Tách biệt Read vs Write):**
  - **Tầng Đọc (Read - Headless Web):** Tận dụng tính năng cắn đề xuất có sẵn trên TikTok Farm Web Dashboard (`tiktok_account_tracker.py` / `tiktok_tracker.db`). Engine tracker tự động gắn cờ `trending = True` (khi $\Delta\text{Follower} \ge 20$ hoặc $\Delta\text{Heart} \ge 50$).
  - **CẤM TUYỆT ĐỐI kẹp logic chuẩn hoá bài ghim vào ca nuôi (Feed Session):** Thao tác mở video $\to$ bấm Chia sẻ $\to$ Ghim/Bỏ ghim trong lúc nuôi nick rất dễ làm vỡ state machine của Feed, vướng popup bản quyền/livestream nuốt touch, làm crash hoặc delay ca nuôi toàn farm.
  - **CẤM TUYỆT ĐỐI quét mù trên thiết bị S7:** Không bật màn hình từng máy S7 chạy dump XML định kỳ chỉ để kiểm tra xem có video nào view cao không. 95% máy không có video cắn đề xuất, quét mù làm chai pin, nóng máy và tranh chấp USB/lock.
  - **Tầng Ghi (Write - JIT Execution trên S7 qua `trending_pin_watchdog.py`):**
    * Watchdog đọc danh sách nick `trending` từ database snapshot mới nhất, đối soát toạ độ máy/serial qua `taikhoan_run_safe.xlsx`.
    * Kiểm tra `device-locks`: Nếu máy đang bận ca nuôi $\to$ giữ hàng đợi, tự động nhường lịch an toàn.
    * Khi máy rảnh $\to$ gọi `pin_top_videos.py --machine <N> --account <USER>` chớp nhoáng (<= 30s) để hoán đổi video cắn view lên Ô số 1, sau đó tắt màn hình về Sleep.
    * Ghi nhận trạng thái vào `D:/Taadaa/data/trending_pin_state.json` với cooldown 12h để chống spam xử lý lặp lại trên cùng một nick.
    * Chuẩn Silent Watchdog: Chỉ gửi thông báo về Telegram khi có video được ghim/đảo ghim thành công; khi không có thay đổi thì hoàn toàn im lặng.


