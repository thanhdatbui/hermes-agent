---
name: evidence-first-delivery
description: Deliver verified visual evidence for UI, farm, or web ops.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [evidence, media, vision, ui, farm, delivery, verification]
    related_skills: [ui-evidence-first, verification-evidence, agent-verification-loop, session-close-protocol]
---

# Evidence-First Delivery

Use this class-level workflow whenever a task produces visual/UI/farm/browser evidence that will be shown to a user. The goal is not merely to attach a file; it is to prove that the artifact is the correct, fresh, legible evidence and that the assistant actually inspected it before delivery.

## Core contract

1. **Do not claim success from summaries alone.** Runner exit code, `verified=True`, worker self-report, a database flag, or a path printed in a log is not visual proof.
2. **Read before sending.** Before emitting any `MEDIA:<absolute_path>` token, open the exact image with `browser_vision` (or use WinRT OCR when vision is unavailable) and inspect it. Confirm:
   - the correct app/screen/action;
   - the correct account, device, or target;
   - the expected new state;
   - no Home/Launcher/lock screen, black/dozing capture, popup obstruction, clipping, stale content, or unreadable text.
   - **Chống Bẫy Ảo Giác Soi Mắt Mù & Bắt Buộc Cross-Check Token Đích (Anti-Hallucination Target Token Gate):**
     * **Nguy cơ nhức nhối:** Coordinator gọi `browser_vision` hoặc OCR trước khi gửi thẻ `MEDIA:` nhưng chỉ gọi "cho có lệ" (blind compliance), sau đó tự động suy diễn/bịa ra câu mô tả đúng theo kỳ vọng của task (ví dụ: kỳ vọng thấy Account Switcher nhưng ảnh thực tế lại là màn hình Tìm kiếm/Mua sắm hàng hóa "dầu ăn simply"). Khi User nhận ảnh sẽ lập tức chất vấn nặng nề: *"Mày nói mày xem hình rồi mà mày gửi tao cái hình như vậy đó hả"*.
     * **Quy tắc Cross-Check Token Cơ Học (Mandatory Token Cross-Check):** Trước khi xác nhận thành công và gắn thẻ `MEDIA:`, BẮT BUỘC phải đối soát trực tiếp các từ khóa đặc trưng của màn hình đích từ text OCR/Vision:
       - Với Account Switcher: BẮT BUỘC phải có các từ khóa như `"Chuyển đổi tài khoản"`, `"Thêm tài khoản"`, hoặc username đích.
       - Với Profile: BẮT BUỘC phải có `"Hồ sơ"`, `"Sửa hồ sơ"`, hoặc username đích.
     * **Cơ Chế Phủ Quyết Tức Thì (Out-of-Context Token Veto):** NẾU kết quả OCR/Vision chứa các token lạ/lệch ngữ cảnh nghiêm trọng (ví dụ: màn hình Search với `"Tìm kiếm"`, `"Bạn có thể thích"`, tên hàng hóa; hoặc màn hình Home Feed với `"Trang chủ"`, `"Đề xuất"`... khi đang cần nghiệm thu Profile/Switcher): BẮT BUỘC KHÓA CHẶN NGAY LẬP TỨC! CẤM gắn thẻ `MEDIA:` gửi cho User, CẤM phát ngôn tuyên bố thành công. Báo cáo trung thực hiện trường bị trượt màn hình và thực hiện điều hướng lại.
   - **Chống Bẫy Thẻ `MEDIA:` Bị Lọt Vào Khối Trích Dẫn Markdown (Blockquote) Khiến Telegram Không Gửi Ảnh (2026-10-10):**
     * **Căn nguyên kỹ thuật**: Hermes Gateway (`gateway/platforms/base.py`, hàm `_mask_protected_spans`) tự động quét và thay thế toàn bộ nội dung trong các dòng trích dẫn markdown (`^>.*$`) bằng khoảng trắng trước khi trích xuất media, nhằm tránh gửi nhầm các đường dẫn ví dụ.
     * **Hậu quả**: Nếu thẻ `MEDIA:<path>` bị đặt bên trong hoặc dính liền sau khối trích dẫn `>`:
       - Gateway sẽ bị mask che mất thẻ, `extract_media()` hoàn toàn KHÔNG nhận diện được file ảnh để upload lên Telegram.
       - Thẻ `MEDIA:<path>` không được bóc tách và bị in thẳng ra tin nhắn người dùng như một dòng text thô vô cảm. Người dùng không thấy ảnh đâu và lập tức phản ứng giận dữ: *"Mày gửi hình kiểu l gì vậy ai xem được!"*.
     * **BẮT BUỘC:** Thẻ `MEDIA:<path>` **PHẢI NẰM TRÊN MỘT DÒNG ĐỘC LẬP HOÀN TOÀN RIÊNG BIỆT, NẰM NGOÀI MỌI KHỐI TRÍCH DẪN (`>`), KHÔNG ĐƯỢC NẰM TRONG CODE BLOCK (` ``` `) HAY INLINE CODE (`` ` ``)**. Lời bình / xác nhận Vision phải dùng văn bản thường hoặc bullet list thường (`- `), TUYỆT ĐỐI KHÔNG dùng dấu `>` ở đoạn có thẻ `MEDIA:`.
   - **Chống Bẫy Đường Dẫn Windows Backslash (`\`) Gây Mất Ảnh Telegram:**
     Trong hệ thống Hermes Gateway (`BasePlatformAdapter.extract_media`), nếu đường dẫn file sau thẻ `MEDIA:` chứa dấu gạch chéo ngược Windows `\` (ví dụ: `MEDIA:D:\Taadaa\runtime\artifacts\...`), các chuỗi như `\a` (artifacts), `\r` (runtime), `\t` (tools/temp) rất dễ bị phân tích thành escape sequence (`\a` -> ASCII bell `\x07`, `\r` -> CR, `\t` -> TAB). Hậu quả: Gateway bóc tách ra đường dẫn hỏng không tồn tại trên đĩa, âm thầm hủy gửi media khiến User hoàn toàn không nhận được ảnh và chất vấn *"Chưa thấy hình!"*.
     **BẮT BUỘC:** Mọi đường dẫn file đính kèm sau thẻ `MEDIA:` trên môi trường Windows **BẮT BUỘC PHẢI DÙNG DẤU GẠCH CHÉO XUÔI (`/`)**, ví dụ: `MEDIA:D:/Taadaa/runtime/artifacts/image.png`, TUYỆT ĐỐI CẤM dùng dấu gạch chéo ngược `\`.
   - **Kỷ luật Cắt cận cảnh (Focused Crop) trên Màn hình Dài/Độ phân giải lớn & Chống Bẫy Cắt Quá Sát/Lẹm Chữ:**
     Khi chụp ảnh màn hình điện thoại (đặc biệt các máy dọc 1080x1920 hoặc màn hình cuộn), các dòng thông báo lỗi, toast message nhỏ, hoặc hộp thoại xác nhận ngắn rất dễ bị co rúm và biến mất khi Telegram nén ảnh toàn màn hình. Điều này khiến User nhìn vào tưởng là màn hình bình thường và chất vấn "có phải hình lúc lỗi đâu". BẮT BUỘC: Khi báo cáo lỗi hoặc trạng thái cụ thể của 1 component/form, **phải crop đúng vùng tiêu điểm (bounding box chứa thông báo lỗi/input box)** và gửi kèm ảnh zoom cận cảnh rõ nét để User thẩm định ngay lập tức bằng mắt mà không cần căng mắt phóng to.
     * **Chống Bẫy Cắt Quá Sát/Lẹm Chữ (Anti-Overcrop / Frame Integrity):** Crop tập trung KHÔNG ĐỒNG NGHĨA với việc xén sát sạt từng con chữ khiến ảnh mất viền, lẹm mép, vỡ tỷ lệ làm User không nhận ra màn hình gì (tránh bị phản ứng "mày chụp hình như cặc ấy"). BẮT BUỘC giữ nguyên toàn bộ thẻ/khung form (card container) với padding tối thiểu 20-40px xung quanh các trường nhập liệu, nút bấm và tiêu đề, hoặc gửi ảnh full-window chuẩn (1280x720) kèm ảnh crop đóng khung trọn vẹn để đảm bảo độ rõ nét và tính toàn vẹn của giao diện.
   - **Cơ chế Fallback Vision sang WinRT OCR (Chống Crash Provider/API Lạ):**
     Khi model Coordinator/Worker đang chạy là text-only hoặc proxy không hỗ trợ multimodal tensor trực tiếp, lệnh `browser_vision` có thể kích hoạt fallback sang auxiliary provider bên ngoài (như `antigravity`) và quăng lỗi `HTTP 404: No active credentials for provider`.
     **Quy tắc bất biến:** Trên môi trường Windows, WinRT OCR native (`windows-native-ocr`) là cơ chế thẩm định O(1) ngoại tuyến chuẩn mực nhất. Nếu `browser_vision` gặp lỗi mạng hoặc thiếu credentials, BẮT BUỘC dùng WinRT OCR trích xuất tọa độ + bounding box + text thực tế để đọc ảnh, tuyệt đối không được để lỗi của vision provider làm tắc nghẽn luồng thẩm định.
   - **Chống Bẫy Gửi Ảnh Nút Bấm Chưa Kích Hoạt (Pre-Action Button vs Post-Action Proof):**
     Khi thực hiện các hành động thay đổi trạng thái quan trọng (ví dụ: *Sign out everywhere*, *Đăng xuất khỏi mọi nơi*, *Xóa thiết bị*, *Revoke token*):
     * **CẤM TUYỆT ĐỐI** chỉ chụp ảnh màn hình có chứa dòng chữ/nút bấm đó (pre-action element) rồi tuyên bố đã hoàn thành! Người dùng sẽ chất vấn ngay: *"gửi hình có nút cho tao chi vậy, bấm xong nó có modal xác nhận hay sao chứ"*.
     * **Bắt buộc**: Phải click vào nút, chờ popup/modal dialog xác nhận (`[role=dialog]`) xuất hiện, click nút xác nhận hành động, và chụp ảnh modal kết quả hậu hành động (ví dụ: *"We've started signing you out / Chúng tôi đã bắt đầu đăng xuất bạn..."*).
     * Bằng chứng của một hành động (action) BẮT BUỘC là trạng thái kết quả hậu hành động (Post-action Result/Confirmation), không phải sự hiện diện của nút bấm trên giao diện.
   - **Chống Bẫy Gửi Ảnh Form Trống Đòi Mã (Empty Challenge Form vs Verified Submission):**
     Khi thực hiện các thao tác xác minh danh tính, 2FA, OTP, đổi mật khẩu:
     * **CẤM TUYỆT ĐỐI** chỉ gửi ảnh chụp form rỗng đang hiển thị ô nhập mã (ví dụ: màn hình *"Xác minh danh tính của bạn - Nhập mã được tạo bởi ứng dụng xác thực của bạn [Nhập mã]"*) rồi dừng lại hoặc tuyên bố đã xong! Người dùng sẽ chất vấn ngay: *"Tới đây đã nhập mã đâu"*.
     * Màn hình form rỗng chỉ chứng minh hệ thống đang chặn lại đòi mã, **HOÀN TOÀN KHÔNG CHỨNG MINH ĐÃ VƯỢT QUA**.
     * **Bắt buộc**: Phải điền mã vào ô input -> Chụp ảnh Checkpoint Pre-submit (đã điền mã) -> Bấm Submit -> Chụp ảnh Checkpoint Post-submit (màn hình chuyển tiếp hoặc đã vào Dashboard / Hồ sơ) để chứng minh mã hợp lệ và đã vượt qua cổng xác thực thành công.
   - **Chống Bẫy False-Success Session Cookie (Web/Browser Auth):** Tuyệt đối CẤM kết luận đổi mật khẩu / reset credential thành công chỉ vì màn hình sau đó hiển thị trang Profile / Dashboard! Trong browser, cookie phiên cũ (login bằng pass cũ) vẫn còn hiệu lực nên trang Profile tự động load lại mà không cần nhập mật khẩu mới. BẮT BUỘC kiểm chứng bằng hành động đối kháng (adversarial readback): **Clear toàn bộ cookie (`context.clear_cookies()`) hoặc mở browser ẩn danh mới hoàn toàn -> Nhập mật khẩu MỚI vào form login -> Phải đăng nhập thành công thì mới được phép công nhận kết quả.** Nếu Microsoft / dịch vụ báo *"Mật khẩu không đúng"* hoặc *"Tạm thời có lỗi"* thì đó là FAIL thực tế, CẤM báo thành công và CẤM lưu pass mới vào Master database / Excel!
   - **Chống Bẫy Phán Đoán Mù Qua API Khi Kiểm Tra Hộp Thư (Anti-Blind-API Invalidation):** Khi kiểm tra hộp thư nhận OTP / verify link bằng script API (IMAP, Graph API, Webhook), nếu API trả về rỗng hoặc lỗi: **CẤM TUYỆT ĐỐI phán đoán bằng miệng rằng "không có thư / dịch vụ chặn mail" nếu chưa chụp ảnh thực tế ứng dụng hộp thư (Outlook / Gmail / Webmail) gửi kèm `MEDIA:<path>`**. Thư xác thực (nhất là Web3, OTP nước ngoài) thường bị phân loại vào tab **"Khác" (Other)** hoặc **"Junk / Thư rác"**, hoặc API chỉ đọc thư mục Focused mặc định nên bỏ sót. Báo "không có mail" bằng lời nói suông mà không có ảnh chụp hộp thư chứng minh là vi phạm kỷ luật bằng chứng thị giác, gây mất phương hướng và lãng phí thời gian của người dùng.
   - **Kỷ Luật Chống Stale Error Banner (Vết Lỗi Cũ Khi Retry):**
     Khi thực hiện vòng lặp retry (ví dụ: nhập sai input/OTP -> hệ thống báo lỗi đỏ -> bốc lại mã đúng và điền lại), trên màn hình thường vẫn còn tồn tại banner/toast báo lỗi cũ của attempt trước do form chưa được re-submit.
     * **CẤM TUYỆT ĐỐI** dùng ảnh chụp form còn dính vết lỗi cũ làm bằng chứng Pre-submit hợp lệ gửi cho User mà không có cảnh báo.
     * **Quy tắc đối chiếu khách quan (Stale vs New Error Classification):**
       - So khớp ngữ nghĩa chuỗi lỗi OCR được với chuỗi lỗi ở attempt N-1 (dung sai khoảng trắng, chữ hoa/thường, dấu câu - case-insensitive normalized matching).
       - Nếu chuỗi lỗi khớp attempt N-1 (ví dụ cùng thông báo `That code didn't work`): Cho phép gán nhãn `KNOWN_STALE_ARTIFACT: <nội dung lỗi cũ> (Residue from attempt N-1, NOT reflective of current input)`.
       - Nếu chuỗi lỗi mang nội dung mới hoặc context khác: BẮT BUỘC coi là lỗi mới phát sinh (`NEW_ERROR`), CẤM lạm dụng nhãn stale để che giấu lỗi!
       - Xử lý tàn dư: Ưu tiên làm mới form hoặc chờ banner tự tắt trước khi chụp; nếu không thể, bắt buộc kèm nhãn trên.
   - **Bất Biến Đi Theo Cặp (Mandatory Pairing Invariant) & Ngưỡng Escalation Rõ Ràng:**
     Mọi thao tác thay đổi trạng thái UI (điền form, submit action, nút bấm quan trọng) **BẮT BUỘC PHẢI ĐI THEO CẶP trong cùng 1 báo cáo**:
     1. **Checkpoint Pre-submit:** Ảnh xác nhận dữ liệu đã điền vào ô input sạch sẽ.
     2. **Checkpoint Post-submit:** Ảnh xác nhận phản hồi thực tế của hệ thống ngay sau khi submit (trang chuyển hướng, popup đóng, banner thông báo thành công).
     * **CẤM TUYỆT ĐỐI** phát ngôn câu "đã xong / đã đổi thành công" nếu thiếu một trong hai ảnh trong cùng một tin nhắn! Thiếu Post-submit chỉ được báo ở thể tiến hành ("đang chờ kết quả submit"), không được dùng từ hoàn thành.
     * **Ngưỡng Escalation Rạch Ròi (Whichever Comes First):**
       - Trạng thái "đang chờ kết quả submit" bị giới hạn cứng bởi 2 điều kiện: **Tối đa 30 giây HOẶC tối đa 3 lần kiểm tra UI — TÙY ĐIỀU KIỆN NÀO ĐẾN TRƯỚC (Whichever comes first)**.
       - Khi chạm ngưỡng (hết 30s hoặc xong lần check thứ 3 mà trang vẫn loading/treo/không đổi): BẮT BUỘC DỪNG NGAY mọi thao tác UI trên tài khoản/máy đó, lập tức kích hoạt **L3 BLOCKED** kèm bằng chứng ảnh treo/log timeout, dừng hoàn toàn vòng lặp và chuyển sang task độc lập khác, CẤM tự ý loop lại chu kỳ 30s mới trong bóng tối!
   - **Quyền Phủ Quyết Của OCR Đa Ngôn Ngữ (Multilingual OCR-Overrides-Intent Veto):**
     Nếu nội dung OCR của ảnh đính kèm có chứa bất kỳ tín hiệu phủ định hoặc lỗi ngữ nghĩa nào (bất kể tiếng Anh, tiếng Việt hay ngôn ngữ khác, ví dụ: `That code didn't work`, `Error`, `Failed`, `Invalid`, `Try again`, `Mã không đúng`, `Thất bại`, `Không thể`, `Vui lòng thử lại`, `Lỗi`, `Chưa chính xác`, `Incorrect`, `Could not`, `Unsuccessful`...), OCR có quyền VETO tuyệt đối lên nhận thức của Agent.
     * CẤM TUYỆT ĐỐI phát ngôn khẳng định thành công dựa trên ý định chủ quan của mình ("agent biết agent đã nhập đúng").
     * Khi OCR phát hiện lỗi: Kết quả đánh giá BẮT BUỘC là FAIL hoặc STALE_FLAGGED, cấm claim SUCCESS cho đến khi có ảnh Post-submit sạch 100%.
   - **Mechanical Evidence Gate Độc Lập Bằng Code (Không Dựa Vào Tự Khai Báo):**
     Để triệt tiêu hoàn toàn điểm mù nhận thức và nguy cơ tự xác nhận khống (self-attestation / gaming), hệ thống trang bị công cụ kiểm chứng cơ học độc lập:
     `D:\Taadaa\tools\evidence_gate_verifier.py`
     * **Cơ chế cưỡng chế vật lý (Deterministic Verification Engine - V13 Production Standard):**
       - **Anti-Replay Temporal Order & Freshness:** Khóa cứng chống tấn công replay ảnh cũ! Yêu cầu `post_image` phải có mtime mới hơn `pre_image`, thời gian cách biệt giữa hai ảnh không vượt quá cửa sổ thao tác (`max_pair_interval <= 120s`), và tuổi thọ file ảnh không vượt quá `max_age <= 600s`.
       - **Fail-Closed Process-Liveness Atomic Claim Binding:** Triệt tiêu hoàn toàn race condition giữa các worker farm chạy song song! Sử dụng cơ chế Two-Phase Reservation có FileLock kết hợp kiểm tra sống còn của tiến trình hệ điều hành (`is_process_alive(pid)`). Nếu gặp lỗi quyền truy cập (`ERROR_ACCESS_DENIED`), hệ thống tuân thủ nghiêm ngặt nguyên tắc Fail-Closed (giả định tiến trình còn sống), bảo vệ tuyệt đối reservation không bị purge nhầm.
       - **Unconditional Mandatory Pairing:** Kiểm chứng mọi thao tác hành động BẮT BUỘC phải có cả cặp ảnh Pre-submit và Post-submit (trừ khi dùng cờ `--allow-single-inspection` cho tác vụ chỉ đọc).
       - **Anti-Bypass Distinct Image Check (SHA256):** Bắt buộc ảnh Pre-submit và Post-submit phải là hai file vật lý độc lập có mã băm SHA256 khác nhau (`pre_hash != post_hash`). CẤM TUYỆT ĐỐI truyền cùng 1 ảnh hoặc ảnh clone để lừa gate!
       - **RFC-Compliant Physical Artifact & Header Validation:** Kiểm tra trực tiếp file ảnh tồn tại trên đĩa, kích thước hợp lệ (>1KB, không đen/trắng rỗng), xác thực header chữ ký định dạng ảnh chuẩn RFC (PNG, JPEG, và WEBP với RIFF container structure ở offset 8-12).
       - **Synchronized 1-to-1 Affirmative Positive Success Evidence Gating:** Đồng bộ 100% từ khóa nhận diện trigger và từ khóa kiểm chứng marker (`COMMON_SUCCESS_MARKERS`). Khi có yêu cầu hoặc claim chứa từ khóa hoàn tất, verifier BẮT BUỘC phải phát hiện tín hiệu thành công thực sự trên ảnh post-submit (`positive_indicators_found`). Nếu không phát hiện tín hiệu thành công, verifier sẽ GATE CỨNG với verdict: `FAIL_NO_POSITIVE_EVIDENCE`. Khi dùng `--allow-single-inspection` (không có post-image thực sự, ví dụ tác vụ headless read-only), scan dương tính (`positive_indicators_found`) đọc OCR của chính ảnh pre-submit làm văn bản bằng chứng hiệu lực (`effective_ocr`) — KHÔNG được coi "post-submit" là bắt buộc phải tồn tại để tính năng này hoạt động. Scan phủ quyết lỗi (veto) trong chế độ này vẫn dựa trực tiếp trên `pre_ocr` qua nhánh xử lý riêng ở bước resolve stale-vs-clean, không đi qua `effective_ocr`.
       - **True Atomic Single-Transaction Audit Persistence (Zero Divergence Guaranteed):** Toàn bộ quy trình ghi file JSON, commit block vào sổ cái append-only `audit_chain.jsonl`, và giải phóng reservation được thực thi đồng bộ trong MỘT GIAO DỊCH NGUYÊN TỬ DUY NHẤT dưới FileLock. Nếu bất kỳ bước nào lỗi, file tạm bị xóa, không ghi block nào vào sổ cái, và verdict trở thành `FAIL_AUDIT_PERSISTENCE_ERROR`. Cam kết toán học 100% không bao giờ xảy ra phân rã giữa sổ cái và giá trị trả về!
       - **Word-Boundary Regex & NFC Normalization:** Chuẩn hóa Unicode NFC đối xứng và sử dụng Regex Word Boundaries (`\b`) cho toàn bộ danh sách veto keywords, triệt tiêu hoàn toàn false-positive (không bị match nhầm từ ghép) và false-negative (không bị lệch Unicode tiếng Việt).
       - **Accurate OCR Engine Handling:** Phân biệt chính xác giữa lỗi thực thi OCR (exit code != 0) và màn hình sạch/trắng không có chữ (stdout rỗng với exit code == 0).
       - **Escalation Bound Enforcement:** Cưỡng chế cơ học thời gian và số lượt (elapsed > 30s HOẶC attempts >= 3 -> trả về `ESCALATE_L3_BLOCKED`).
       - Trả về JSON machine-readable: `{"verdict": "PASS" | "FLAGGED_STALE_RESOLVED" | "VETO_REJECT" | "ESCALATE_L3_BLOCKED" | "FAIL" | "FAIL_NO_POSITIVE_EVIDENCE" | "FAIL_AUDIT_PERSISTENCE_ERROR" | "FAIL_LOCK_TIMEOUT", "reason": "...", "block_hash": "...", "audit_file": "...", "audit_persisted": true}`.
     * **Quy tắc bàn giao:** Trong tin nhắn bàn giao kết quả UI, Coordinator BẮT BUỘC phải chạy script verifier này và trích xuất kết quả:
       `EVIDENCE_GATE: PASS | Verified by D:/Taadaa/tools/evidence_gate_verifier.py | Clean evidence confirmed`.
     * Nếu `evidence_gate_verifier.py` trả về `VETO_REJECT`, `FAIL`, `FAIL_NO_POSITIVE_EVIDENCE`, `FAIL_AUDIT_PERSISTENCE_ERROR`, `FAIL_LOCK_TIMEOUT` hoặc `ESCALATE_L3_BLOCKED` -> Hệ thống tự động khóa chặn phát ngôn thành công, buộc Coordinator phải dừng lại báo cáo lỗi thật hoặc chuyển sang L3 BLOCKED.
     * Chi tiết kiến trúc Two-Phase Reservation, Process-Liveness và Hash-Chained Audit: xem `references/mechanical-evidence-gate-architecture.md`.
3. **Send native media, not a path.** Put `MEDIA:<absolute_path>` on its own line, never inside a Markdown code fence. A folder path, a bare file path, or a link to a run directory is not evidence delivery.
4. **State what was seen.** The user-facing report must contain a short visual-readback sentence, e.g. “Vision thấy Profile của đúng handle; avatar mới đã hiện trong vòng tròn; không có popup che.” Do not send an image with a content-free “done”.
5. **One checkpoint per state-changing UI step.** For UI/browser/farm operations, keep blind steps to at most one. Capture and deliver the required checkpoint after each state-changing action; capture pre-submit and post-submit around forms.
6. **Headless & screenless devices (Routers, Switches, Linux daemons, DBs, APIs).** Lack of a display does NOT exempt an operation from the evidence gate. For headless systems, evidence is **Read-Back Stdout** (actively querying the device to dump current configuration/IP/service status, e.g. `uci get network.wan.username` or active IP). Exit code 0, worker dispatch status, or absence of errors is NOT proof.
7. **Physical Action Gate (Bất biến thao tác vật lý).** Any instruction directing the user to perform physical, real-world interventions (unplugging/plugging network cables, power cycles, hard reboots, swapping SIMs/ports) MUST be gated behind `VERIFIED_SUCCESS`. It is strictly forbidden to instruct physical action while a task is still running, unverified, or failed. Always quote the read-back proof in the physical instruction.

## Artifact selection and integrity

- Bind evidence to the exact run, machine/serial, account, attempt, and timestamp. Do not substitute a later screenshot, another machine’s artifact, a launcher screenshot, or an image from a different retry.
- Prefer the canonical runner artifact (`avatar-uploaded-confirmed.png`, matching `ui.xml`, `summary.txt`, `report.json`) over ad-hoc screenshots.
- Validate file existence, freshness, readable image structure, minimum size, and allowed artifact roots. Reject missing, stale, undersized, corrupt, black, white/solid-color, or out-of-scope files.
- For multi-step flows, preserve capture-before-teardown: screenshot and readback first, then HOME/force-stop/cleanup.
- When retrying a failed send, use a cache-busting filename and changed byte stream; do not rely on Telegram reusing a path/file ID.

## Mechanical delivery gate

The delivery layer should validate outbound completion claims before the platform adapter sends them:

- Completion claims must carry valid `MEDIA:` evidence.
- Reject bare paths, code-fenced media tokens, missing files, stale files, wrong roots, invalid images, and evidence that does not satisfy the run context.
- The gate must be active even when the caller omits optional evidence context. Optional context must default to the safest fail-closed context, not disable validation.
- Record structured telemetry for every validation/block: event name, timestamp, platform, chat/target, valid flag, reason, and evidence paths. A warning log alone is not sufficient for auditability.
- Keep ordinary non-completion conversation usable, but do not let wording paraphrases create an escape hatch for a visual operation’s final report. Prefer task-type context plus completion heuristics rather than a tiny keyword list.

## Visual content quality

For profile/avatar/farm work, verify the semantic content, not just image statistics:

- Profile/Account Switcher/Save Surface must be the target screen.
- The target handle/name and new avatar/content must be visible.
- Do not accept Home, Settings-only, an unrelated profile, a stale switcher, or a generic launcher image as proof.
- A screenshot that is technically non-black but visually irrelevant is still invalid.
- For avatar replacement, prove a real change from the old state and report source synchronization, queue state, runner result, and visual Profile verification separately.

## Failure handling

- If vision/OCR cannot inspect the exact artifact, report `UNPROVEN` or `INSUFFICIENT EVIDENCE`; do not attach it “for completeness”.
- If the mechanical gate rejects delivery, preserve the rejection reason and structured event. Fix the evidence or the delivery contract; never bypass the gate by moving the path into prose, a code block, or a second text message.
- Do not loop silently. A failed UI attempt requires an immediate error checkpoint; after three consecutive failures on one account/device, stop that UI loop and report the evidence-backed blocker.
- Separate observed facts from hypotheses. Quote OCR/log text when diagnosing a screenshot; do not invent a root cause from an exit code.

## Closeout and review

For code changes implementing evidence delivery, run focused offline tests and then the canonical closeout reviewer with the exact target-file allowlist. Do not use `--skip-test` when tests exist. If the reviewer rejects, remediate the exact findings (especially missing context enforcement, missing structured telemetry, or shallow delivery-flow coverage) and rerun until `APPROVED` with score >=85. Keep unrelated dirty files out of the candidate diff.

## User-facing style

The user prefers direct Vietnamese, concise status, and actual native images rather than folder links or path dumps. Lead with the result, then list only the evidence and blocker that change the decision. Never make the user ask “hình đâu?” after a UI operation.

- **Kỷ Luật Phản Hồi Khi User Bức Xúc Về Alert / Lỗi Hệ Thống ("Clgt", "Dlgt"):**
  * **CẤM TUYỆT ĐỐI**: Trả lời dài dòng, liệt kê dàn trải các bước kỹ thuật rườm rà, phân bua cơ chế hook bảo vệ, hoặc thanh minh phòng thủ.
  * **VÀO THẲNG BẢN CHẤT 3 Ý TẬP TRUNG**:
    1. **Con số thực chất**: Tách bạch rõ tỷ lệ thành công của từng khâu (Feed vs Follow vs Upload) để User thấy bản chất hệ thống không gãy toàn diện.
    2. **Sự cố cá biệt cốt lõi**: Nêu đúng nguyên nhân gốc rễ (ví dụ: máy kẹt ở switcher anchor do layout TikTok, không phải mất phiên / văng acc).
    3. **Hiện trạng an toàn**: Khẳng định thiết bị đã giải phóng lock an toàn, dữ liệu nguyên vẹn, sẵn sàng cho ca tiếp theo.

## Avatar-only scope and false-policy refusal guard

When the requested mutation is only “đổi avatar”, bind the run to an **avatar-only scope lock**:

1. Do not change display name, username, bio, links, or any other profile field unless the user explicitly requests that field in the same task. A successful name edit is still a task failure if the user asked only for an avatar.
2. A generic model/tool refusal claiming that an ordinary avatar replacement violates policy is not an evidence-based platform blocker. Treat it as a transient refusal, state plainly that the refusal was incorrect, and continue only through the normal bounded UI flow after revalidating the live target.
3. Before every state-changing tap, verify the current app/activity, exact handle, and fresh screen capture. Never reuse coordinates from a stale screenshot after the device has drifted to Home, Messaging, another app, or another account.
4. Capture and verify the selected-photo checkpoint before tapping Next, then capture and verify the crop/confirmation checkpoint before Save, then reopen the exact Profile and verify the new non-placeholder avatar. Exit code 0, a successful ADB tap, a runner `verified=True`, or an old report image is not completion evidence.
5. If the final screen is unrelated, the avatar is unchanged, or the exact profile proof is missing, report `UNPROVEN`/`BLOCKED` and name the observed activity. Do not “repair” the report by mutating another profile field.
6. If an unrelated mutation already occurred, disclose it immediately as an out-of-scope side effect; do not bury it in implementation details or imply the avatar task succeeded.

Use `references/avatar-only-scope-and-false-policy-refusal.md` for the incident-derived checklist and evidence matrix.

- **Chống Bẫy Báo Cáo Xong Bằng Text Suông (Zero-Image Text Report Trap - 2026-10-10):**
  * **CẤM TUYỆT ĐỐI** kết thúc tác vụ, hoàn thành đổi pass/2FA/login hoặc thi công xong mà chỉ trả lời bằng văn bản thuần (text suông) mà KHÔNG đính kèm thẻ `MEDIA:<path>` ngay trong tin nhắn!
  * Người dùng cực kỳ dị ứng và coi là vi phạm kỷ luật nặng nề nếu bot "lại tiếp tục làm xong đéo gửi hình".
  * Mọi phát biểu kết luận hoàn tất (kể cả hoàn thành kỹ thuật hay thành công một phần) BẮT BUỘC phải đi kèm ít nhất 1 ảnh chụp màn hình chứng minh đích thật (bảng đối soát Excel, màn hình 2FA TikTok, hoặc Switcher tài khoản).
  * **Cơ chế Chốt chặn Cơ học Tầng Hook (`transform_llm_output`)**: Can thiệp chặn trực tiếp tại plugin guard (`farm-coordinator-guard`): nếu câu trả lời của Coordinator chứa khẳng định hoàn thành tác vụ UI/Farm mà thiếu thẻ `MEDIA:` hoặc ảnh chưa được soi mắt qua WinRT OCR / browser_vision -> FAIL-CLOSED chặn và ghi đè bằng cảnh báo đỏ vi phạm kỷ luật.
  * Xem thêm: `references/claude-cli-evidence-first-gate-audit-and-text-only-report-trap-20261010.md` cho 5 lỗ hổng Claude CLI chỉ ra khi thẩm định Evidence-First Gate (regex hẹp, thiếu đối chiếu OCR ngữ nghĩa, nhận diện soi mắt lỏng lẻo, regex MEDIA cứng nhắc, fail-open).

- **Chống Bẫy Dùng Màn Hình Feed Làm Bằng Chứng Login Thành Công (Feed vs Profile/Switcher Login Proof Trap - 2026-10-10):**
  * **CẤM TUYỆT ĐỐI** gửi ảnh màn hình Home Feed (video lướt trang chủ) rồi tuyên bố đăng nhập TikTok thành công! Người dùng sẽ phản ứng gay gắt ngay: *"Đây là màn feed thì lấy gì chứng minh login thành công. Đụ mẹ mày có xem hình trước khi gửi tao không vậy"*.
  * **Bản chất**: Video Home Feed chỉ chứng minh app TikTok đang mở và đang phát video, **HOÀN TOÀN KHÔNG CHỨNG MINH ĐƯỢC TÀI KHOẢN ĐÍCH ĐÃ ĐĂNG NHẬP HAY CHƯA** (TikTok có thể xem video ẩn danh hoặc đang ở phiên của một nick khác hoàn toàn).
  * **BẮT BUỘC ĐIỀU HƯỚNG LẤY BẰNG CHỨNG ĐÍCH**: Sau khi vượt qua OTP/mật khẩu, script/coordinator BẮT BUỘC phải chuyển sang tab **Hồ sơ (Profile)** và/hoặc mở **Account Switcher**:
    1. **Màn hình Hồ sơ (Profile)**: Phải hiển thị rõ ràng `@<username>` đích, tên hiển thị, các chỉ số Đang follow/Follower/Thích.
    2. **Màn hình Account Switcher (Chuyển đổi tài khoản)**: Phải hiển thị danh sách tài khoản kèm dấu tích xanh chọn trúng tài khoản đích.
  * Chỉ khi có 1 trong 2 màn hình này (được kiểm chứng qua OCR/Vision thấy đúng username đích) thì mới được phép công nhận và tuyên bố login thành công.

- **Chống Bẫy Nhầm Lẫn Bằng Chứng 2FA Với Màn Hình Switcher/Profile (2FA Screen vs Switcher/Profile Trap - 2026-10-10):**
  * **CẤM TUYỆT ĐỐI** gửi ảnh Account Switcher (danh sách tài khoản) hoặc trang Hồ sơ (Profile) rồi tuyên bố đã bật 2FA thành công! Người dùng sẽ phản ứng gay gắt ngay: *"Cái t cần là chứng minh có 2fa r chứ gửi linh tinh gì v"*.
  * **Bản chất**: Ảnh Switcher hoặc Profile chỉ chứng minh tài khoản đã được nạp và lưu phiên trên thiết bị, **HOÀN TOÀN KHÔNG CHỨNG MINH ĐƯỢC TRẠNG THÁI BẢO MẬT 2FA CỦA TÀI KHOẢN ĐÓ**.
  * **BẮT BUỘC ĐIỀU HƯỚNG VÀO MÀN HÌNH BẢO MẬT ĐÍCH**: Sau khi hoàn thành thao tác bật 2FA hoặc xác nhận tài khoản đã có 2FA, BẮT BUỘC phải chụp thực tế màn hình **"Xác minh 2 bước" (Two-step verification)** trong *Cài đặt và quyền riêng tư > Bảo mật*:
    1. Tiêu đề hiển thị rõ: **"Xác minh 2 bước đang bật"**.
    2. Phương thức **"Trình xác thực" (Authenticator): Bật** (kèm checkbox/dòng trạng thái active).
    3. Phương thức **"Email": Bật** (kèm email hiển thị dạng mask).
  * Chỉ khi có ảnh chụp màn hình cài đặt 2FA này (được kiểm chứng qua OCR/Vision thấy rõ dòng *"Xác minh 2 bước đang bật"* và *"Trình xác thực: Bật"*), mới được phép công nhận kết quả và gửi kèm thẻ `MEDIA:<path>`.

- **Chống Bẫy Báo Cáo Thiếu Chặng Trong Quy Trình Đa Bước (Anti-Omitted-Step Report Trap - 2026-10-10):**
  Khi thực hiện các quy trình tự động hóa đa bước (ví dụ: chuỗi bảo mật Hotmail/TikTok: *1. Add 2FA -> 2. Đổi mật khẩu -> 3. Sign out everywhere -> 4. Relogin 2FA -> 5. KMSI / Dashboard*):
  * Người dùng cực kỳ dị ứng và coi là thất bại nghiêm trọng nếu báo cáo thiếu ảnh của bất kỳ chặng nào ("bước đăng nhập lại hình ảnh chứng minh đâu, bước add 2fa đâu?", "sao cứ làm đéo đủ v").
  * **BẮT BUỘC:** Khi quy trình gồm N chặng logic, báo cáo nghiệm thu phải cung cấp đầy đủ N ảnh chụp bằng chứng cho đủ N chặng trong **CÙNG MỘT TIN NHẮN TỔNG HỢP**.
  * CẤM TUYỆT ĐỐI viện cớ "tài khoản đã có 2FA từ trước nên bỏ qua", "đã vào profile là coi như relogin xong", hoặc chỉ gửi 1-2 ảnh đại diện rồi dừng lại. Thiếu bất kỳ chặng nào là CHƯA HOÀN THÀNH. Nếu tài khoản đã có sẵn tính năng (ví dụ đã bật 2FA), bắt buộc phải chọn tài khoản mới chưa từng cài để chứng minh trọn vẹn toàn bộ các chặng từ đầu đến cuối.

- **Chống Bẫy Ghép Ảnh (Collage Bypass) & Strict Per-Claim Per-User Binding (2026-10-11):**
  * **Cạm bẫy:** Coordinator đính kèm nhiều ảnh (Ảnh A chứa username `@user_a` trong Switcher nhưng không có 2FA; Ảnh B là màn hình 2FA đang bật của `@user_other` nhưng không có tên `@user_a`). Hoặc trong tuyên bố đa claim (*"Nick @user_a đã đăng nhập và bật 2fa"*), nếu gate chỉ kiểm tra username khớp bất kỳ claim nào thì ảnh Switcher của `@user_a` và ảnh 2FA của `@user_other` vẫn qua mặt được gate!
  * **BẮT BUỘC:** Với **MỖI username** và **MỖI claim_type** xuất hiện trong tuyên bố, bắt buộc phải có **ÍT NHẤT 1 ẢNH THỎA MÃN ĐỒNG THỜI** cả tên username lẫn nội dung hành động hợp lệ (2FA ON / Switcher / Mật khẩu mới). Không có ảnh đơn lẻ nào chứa đủ cả hai -> FAIL-CLOSED chặn đứng ngay lập tức!
  * **Chống Bẫy Vừa Bật Vừa Tắt (Dual-Condition Veto):** Nếu ảnh chứa bất kỳ biến thể tắt nào (`2fa: off`, `xác minh 2 bước: tắt`, `trình xác thực: tắt`, `vô hiệu hóa`), ảnh đó bị phủ quyết (VETO) 100%, không được tính là bằng chứng 2FA hợp lệ kể cả khi có dòng chữ "đang bật" ở tiêu đề.
  * **Chặn Đứng HTML Spoofing & Localhost/Data URL:** Cấm dùng `browser_vision` trên file cục bộ `.html` / `.htm`, `http://127.0.0.1`, `http://localhost`, `data:` do agent tự render để làm giả bằng chứng thị giác. Cờ HTML phải được chuẩn hóa bỏ query/fragment và reset khi chuyển sang web thật.
  * **Bẫy Form Trống & Excel Không Phải Bằng Chứng Đổi Mật Khẩu:** Form nhập mật khẩu trống chưa submit (`đặt lại mật khẩu`, `mật khẩu mới`) và Bảng đối soát Excel chỉ chứng minh giao diện/sheet, KHÔNG chứng minh đổi pass thành công. Bằng chứng đổi mật khẩu hoàn tất bắt buộc là ảnh màn hình thiết bị TikTok thật chứa chỉ báo thành công sau submit (`đã đổi mật khẩu`, `mật khẩu đã được đổi`, `đổi mật khẩu thành công`, `đã cập nhật mật khẩu`).
  * **Bỏ Ngoại Lệ Dấu Hỏi Lỏng Lẻo:** Mọi câu hỏi có chứa tuyên bố hoàn thành đều bắt buộc phải kèm ảnh bằng chứng thị giác, không để lọt qua ngoại lệ `?`. Phủ định chỉ được tính khi đứng ngay sát trước động từ claim.
  - **Fail-Closed Tuyệt Đối Khi Thiếu SHA-256:** Thiếu hash lúc OCR hoặc hash tính lại từ đĩa rỗng/lệch ➔ Lập tức đánh dấu `unverified`/`tampered` và chặn xuất bản.
    - **Bẫy Mất Dấu Vết Soi Mắt Khi Dùng `browser_navigate(file:///...)` + `browser_vision` (Guard Path-Tracking Desync):**
      * **Căn nguyên kỹ thuật**: Hook kiểm tra cơ học `Evidence-First Gate` trong hệ thống quét tham số công cụ để xác nhận ảnh đính kèm đã qua kiểm chứng trước khi cho phép xuất bản thẻ `MEDIA:<path>`.
      * **Hậu quả nếu bỏ sót**: Nếu Agent mở ảnh bằng `browser_navigate(url="file:///D:/path/to/img.png")` nhưng trong `browser_vision(question="...")` lại chỉ truyền câu hỏi chung chung (không chứa đường dẫn file), hook sẽ KHÔNG bóc tách được file path từ `browser_vision`. Khi phát hiện thẻ `MEDIA:D:/path/to/img.png` ở tin nhắn ra, gate lập tức kích hoạt chặn FAIL-CLOSED: `🛑 [EVIDENCE FIRST GATE — UNVERIFIED MEDIA]... Chưa qua WinRT OCR hoặc browser_vision`.
      * **BẮT BUỘC**: Khi gọi `browser_vision`, tham số `question` **BẮT BUỘC PHẢI CHỨA RÕ RÀNG ĐƯỜNG DẪN TUYỆT ĐỐI CỦA ẢNH** (ví dụ: `browser_vision(question="Kiểm tra D:/Taadaa/.../image.png: xác nhận...")`), hoặc phải chạy WinRT OCR trực tiếp lên file path để hook ghi nhận audit trail hợp lệ 100%.

## References

- `references/evidence-first-gate-v4-3-adversarial-audit-lessons.md` — **[MỚI 11/10/2026]** Đúc kết 9 vòng thẩm định đối kháng với Claude Code CLI: Khóa chặt Collage Bypass qua Strict Per-Image Binding, Dual-Condition 2FA Veto, Anti-HTML Spoofing, loại bỏ Excel khỏi claim mật khẩu, và kỷ luật kiểm thử Hermetic 100% bằng `tempfile` và SHA-256 thật.
- `references/claude-cli-evidence-first-gate-audit-and-text-only-report-trap-20261010.md` — **[MỚI 10/10/2026]** Bài học thẩm định kỷ luật từ Claude Code CLI (58/100): Chốt chặn cơ học `Evidence-First Gate` qua hook `transform_llm_output`, 5 lỗ hổng chí tử (regex hẹp, lỏng lẻo OCR, thiếu mtime, regex MEDIA cứng nhắc, fail-open) và quy tắc dọn sạch pass láo `AUTH_BLOCKED` về `None` trong file Excel.
- `references/telegram-media-tag-formatting-and-blockquote-masking-pitfall-20261010.md` — **[MỚI 10/10/2026]** Cạm bẫy định dạng thẻ `MEDIA:` trong Hermes Gateway: Cơ chế `_mask_protected_spans` che khuất `MEDIA:` nằm trong/sau blockquote (`>`), lỗi lộ text thô trên Telegram Desktop, và quy tắc bất biến đặt `MEDIA:` trên dòng độc lập ngoài quote.
- `references/closeup-crop-and-legible-evidence-delivery-20261008.md` — **[MỚI 08/10/2026]** Kỷ luật Crop Cận Cảnh Bằng Chứng UI (Zoomed Focus Crop) & Chống Ảo Giác Ảnh Mù Toàn Màn Hình: CẤM chỉ gửi ảnh dọc 1080x1920 bị co nhỏ trên Telegram làm mờ chữ; bắt buộc crop vùng trọng tâm (input + nút + dòng lỗi) để mắt nhìn thấy ngay, và cơ chế ẩn bàn phím ảo trước khi chụp.
- `references/mechanical-evidence-gate-architecture.md` — kiến trúc chi tiết Mechanical Evidence Gate Engine (V12 Perfect Integrity): Process-Liveness Atomic Reservation, Zero-Divergence Fail-Closed persistence, Anti-Replay Claim Binding, và Cryptographic Hash-Chained Audit Ledger (`audit_chain.jsonl`).
- `references/mechanical-evidence-gate.md` — đặc tả kỹ thuật và kiến trúc Mechanical Evidence Gate Engine (V9 Enterprise): chống Replay attack qua ràng buộc thời gian (mtime < 120s), Anti-same-file SHA-256, Zero Self-Attestation, Affirmative Success Evidence, và Append-only Cryptographic Hash-Chained Audit Ledger (`audit_chain.jsonl`).
- `references/stale-error-banners-and-paired-evidence-audit.md` — phân tích nguyên nhân gốc rễ sự cố báo cáo bằng chứng thị giác (Stale Error Banners, bẫy retry loop, Mandatory Pairing, OCR-Overrides-Intent Veto và thẩm định độc lập từ Claude Code CLI).
- `references/native-media-visual-readback-and-mechanical-gate.md` — incident-derived implementation and review lessons for native Telegram media, mandatory vision readback, fail-closed delivery, structured telemetry, and closeout remediation.
- `references/headless-devices-readback-and-physical-action-gate.md` — guidelines for headless device read-back evidence (routers/network/DB), anti-hallucination barriers, and gating human physical actions (cables/reboots) behind verified success.
- `references/avatar-replacement-screenshot-triage.md` — O(1) account identification from a profile screenshot, source-frame avatar QA, mapped-path synchronization, queue/PENDING semantics, and live device-lock handling for avatar replacement.
