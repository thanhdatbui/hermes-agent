---
name: vision-evidence-and-gate6-verification
description: "Use when vision 503 fails Gate 6. Fallback Claude CLI."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [gate6, vision, visual-evidence, ocr, claude-worker, fail-closed]
---

# Vision Evidence & Gate 6 Verification SOP

Tài liệu quy trình chuẩn khi thực thi Invariant Soi Mắt & Gate 6 Visual Evidence trên Taadaa Farm.

- Chi tiết SOP đầy đủ: [`references/vision-down-fail-closed-and-claude-cli-fallback-sop.md`](references/vision-down-fail-closed-and-claude-cli-fallback-sop.md)
- Đăng ký Receipt Media Gate & xử lý chặn clarify: [`references/media-gate-receipt-registration-and-clarify-lockout.md`](references/media-gate-receipt-registration-and-clarify-lockout.md)
- Phân bậc Receipt T0/T1/T2/T3 & chống bẫy im lặng Gate 6: [`references/tiered-verifier-and-gate6-incentive-alignment.md`](references/tiered-verifier-and-gate6-incentive-alignment.md)
- Gate cơ học có chỉ dẫn (Action-Forcing Guidance) & Invariant Tiếng Việt có dấu: [`references/vietnamese-diacritics-profile-and-action-forcing-guidance-gates.md`](references/vietnamese-diacritics-profile-and-action-forcing-guidance-gates.md)
- Chống Chụp Mù Launcher & Cuộn Lưới Video Below-the-fold: [`references/pre-capture-focus-guard-and-anti-launcher-hallucination.md`](references/pre-capture-focus-guard-and-anti-launcher-hallucination.md)
- Điều Tra Sự Cố Bị Vượt Mặt Media Gate & Cơ Chế Chặn Ký Receipt Rỗng: [`references/media-gate-bypass-investigation-and-grounding-fix.md`](references/media-gate-bypass-investigation-and-grounding-fix.md)
- SOP Thẩm Định Thị Giác Đa Tầng Cơ Học (Sol -> Agy -> Claude): [`references/tiered-vision-fallback-mechanical-sop.md`](references/tiered-vision-fallback-mechanical-sop.md)
- Phân Tầng Reviewer & Chốt Chặn Cơ Học Chống Vượt Mặt Gate 6 (Verdict APPROVED): [`references/media-gate-bypass-investigation-and-grounding-fix.md`](references/media-gate-bypass-investigation-and-grounding-fix.md)
- Bài Học Thực Chiến Hardening Media Gate & Bắt Buộc Ảnh Chốt Phiên: [`references/closeout-visual-evidence-and-gate-hardening-lessons.md`](references/closeout-visual-evidence-and-gate-hardening-lessons.md)
- Xác Minh Fresh Screencap & Đối Soát Account Switcher: [`references/fresh-screencap-and-account-switcher-verification.md`](references/fresh-screencap-and-account-switcher-verification.md)
- Báo Cáo Điều Tra Bypass by Claim Omission & Chốt Chặn Task Contract Binding: [`references/bypass-by-claim-omission-and-task-contract-binding.md`](references/bypass-by-claim-omission-and-task-contract-binding.md)
- Chặn 2FA/TOTP Khi Switcher & Kỷ Luật Nghiệm Thu Profile: [`references/account-switcher-2fa-totp-interception-and-profile-standardization.md`](references/account-switcher-2fa-totp-interception-and-profile-standardization.md)
- Khôi Phục Session 2FA Ảo & Nạp Bio Bằng AdbKeyboard Broadcast: [`references/transient-2fa-recovery-and-adb-keyboard-utf8-bio-injection.md`](references/transient-2fa-recovery-and-adb-keyboard-utf8-bio-injection.md)
- Chống Bịa Đặt Lý Do Lấp Liếm & Bộ Ba Đối Soát Profile (Tên, Bio, Avatar): [`references/anti-fabrication-and-full-profile-triad-verification.md`](references/anti-fabrication-and-full-profile-triad-verification.md)
- Chống Báo Xong Mù, Chống Văn Mẫu Bio & Positive Contract Verifier: [`references/anti-blind-completion-and-positive-contract-verifier.md`](references/anti-blind-completion-and-positive-contract-verifier.md)
- Kỷ luật Nhả Lock Khung Giờ Ca Nuôi & Chống Ôm Máy Trễ Giờ Feed: [`references/shift-window-cutoff-and-active-feed-preemption.md`](references/shift-window-cutoff-and-active-feed-preemption.md)
- Soi Mắt Màn Hình Trình Duyệt / Browser CDP & Xác Thực Đăng Nhập: [`references/browser-cdp-session-and-form-vision-verification.md`](references/browser-cdp-session-and-form-vision-verification.md)
- Kiến Trúc Hook Cơ Học Gate 6 & Invariant Chống Khóc Lóc: [`references/gate6-mechanical-hook-and-anti-whining-architecture.md`](references/gate6-mechanical-hook-and-anti-whining-architecture.md)
- Kiến Trúc Auto-Rewire & Guidance Chống Bại Liệt L3 Cho Gate 6: [`references/gate6-auto-rewire-and-guidance-architecture.md`](references/gate6-auto-rewire-and-guidance-architecture.md)
- Kỷ Luật Cấm Lạm Dụng Claude CLI & Đối Soát Avatar Bitmap (Chống OCR Mù): [`references/anti-claude-cli-runaway-and-bitmap-avatar-verification.md`](references/anti-claude-cli-runaway-and-bitmap-avatar-verification.md)
- Chống Chụp Ảnh Mù Đối Phó & Ép Buộc Soi Mắt Trước Khi Gửi: [`references/anti-fake-screenshot-and-mandatory-inspection-receipt.md`](references/anti-fake-screenshot-and-mandatory-inspection-receipt.md)
- Khắc Phục Lỗ Hổng Sys.Path Plugin, Bẫy ImportError Âm Thầm & Hoàn Thiện Wiring Gate 6: [`references/plugin-syspath-hardening-and-full-gate6-wiring.md`](references/plugin-syspath-hardening-and-full-gate6-wiring.md)

## 1. Nguyên Tắc Cốt Lõi (Invariants)
1. **CẤM gửi ảnh mù / đối phó:** Trước khi đính kèm bất kỳ thẻ `MEDIA:<path>` nào, bắt buộc phải mở ảnh ra soi mắt kiểm tra trước.
2. **CẤM hạ cấp bằng chứng sang OCR text thô:** Text OCR chỉ dùng để hỗ trợ tọa độ/phân loại sơ bộ, KHÔNG thay thế được Vision để chứng minh giao diện. Khi tool Vision chết (503/Quota 429), CẤM dùng OCR text để báo cáo hoàn thành.
3. **Quy Trình Phân Bậc Receipt Khi Vision 503 (Tiered Verifier SOP):**
   - **T0 (Primary Vision):** `browser_vision` thành công. Đăng ký receipt và gửi `MEDIA:`.
   - **T1 (Fallback Vision):** Gọi Claude CLI reviewer / 9router direct để soi ảnh độc lập.
   - **T2 (Cơ học - Mechanical Receipt):** Khi toàn bộ LLM Vision chết, cho phép sinh receipt T2 dựa trên `uiautomator dump` (thuộc tính text) + WinRT OCR đối soát theo contract O(1). Gửi `MEDIA:` kèm nhãn rõ: `[T2 - Cơ học, Vision 503]`.
   - **T3 (Không có Verifier):** DỪNG THAO TÁC TIẾP THEO. Gửi ảnh gắn nhãn `[CHƯA SOI - CHỜ USER XÁC NHẬN]`. CẤM TUYỆT ĐỐI im lặng bỏ gửi ảnh để chạy tiếp (Max blind steps = 1 là bất biến; im lặng nặng tội hơn gửi ảnh có cảnh báo).
4. **Cơ chế Hook HMAC-SHA256 Media Gate (`guard_media_vision_gate.py`):** Mọi ảnh `MEDIA:<path>` gửi qua Telegram bắt buộc phải có receipt hợp lệ (TTL <= 300s, ký bằng sha256 và mtime). Receipt được cấp tự động từ bên trong tool thật (`run_winrt_ocr.py` hoặc `vision_fallback_reader.py`). CẤM Coordinator tự ý đăng ký receipt bằng tay qua CLI (lệnh gõ tay đã bị vô hiệu hóa). Khi Hand-off Lock Active (`handoff_lock_active.json`), công cụ `clarify` bị chặn tự động — Coordinator phải trình bày các phương án đề xuất trực tiếp trên chat thay vì gọi `clarify`.
   - **Kỷ luật chống khóc lóc / tê liệt (Anti-Whining Gate):** Khi Gate chặn (DENY), CẤM TUYỆT ĐỐI xin lỗi, giải thích hay phân trần dông dài. Gate trả về `REQUIRED_NEXT_ACTION` dạng enum đóng (A: bỏ claim chưa chứng minh, B: chạy lệnh OCR/Vision lấy bằng chứng thật), Coordinator bắt buộc phải thực thi ngay (A) hoặc (B). CẤM ép cứng `evidence_tokens >= 3` cho ảnh Avatar/đồ họa không chữ (nhóm này dùng `ocr_status = "OK_EMPTY"`). CẤM so khớp literal cứng cho nhãn Ghim; bắt buộc dùng regex fuzzy khớp cả `Däg 1m`, `Dä ghim`, `Đã ghim`, `Pinned`.
5. **Pre-Capture Focus & Anti-Launcher Semantic Gate:** Trước khi screencap, BẮT BUỘC kiểm tra focus máy (`inspect_machine.py <N>`); nếu đang ở Launcher/Splash, phải khôi phục app vào foreground và điều hướng đúng tab. Sau khi pull ảnh về, BẮT BUỘC chạy WinRT OCR đối soát: nếu ảnh chứa từ khóa Launcher (Chrome, Photos, Cài đặt, Laban Key...) hoặc Splash đen $\rightarrow$ FAIL-CLOSED, CẤM ký receipt và CẤM gửi thẻ `MEDIA:`. CẤM TUYỆT ĐỐI ảo giác nhìn thấy nội dung khi ảnh thực tế là Launcher.
6. **Tiêu chuẩn nghiệm thu Ghim bài (Pin Top) & Micro-swipe Giữ Định Danh:**
   - **CẤM suy diễn Pin từ View cao:** Video nằm ở ô 1 có view cao (ví dụ 33K) KHÔNG CÓ NGHĨA là đã ghim (có thể chỉ là video mới nhất). Chỉ công nhận đã ghim khi TẬN MẮT THẤY huy hiệu chữ đỏ `Đã ghim` (Pinned badge) ở góc trên bên trái thumbnail. CẤM BỊA ĐẶT nhãn đỏ khi ảnh không có.
   - **Micro-swipe giữ trọn khung định danh:** Khi cuộn kéo lưới video lên, CẤM vuốt quá đà làm bay mất avatar, username `@...` và bio. Sử dụng micro-swipe nhẹ (`input swipe 540 1100 540 850 300`), đảm bảo 1 bức ảnh chụp trọn vẹn cả định danh tài khoản lẫn hàng 1 của lưới video có nhãn "Đã ghim".
7. **Kỷ luật Canary Cron-Parity & Cấm Báo Cáo Không Có Ảnh (Gate 6 Invariant):**
   - **Cron Parity:** Khi User yêu cầu Canary sau khi sửa code, BẮT BUỘC chạy theo đúng cách thức và lệnh mà Cron chính thức sẽ thực thi. CẤM dùng cờ lẻ/lệch bản chất (như `--password-only`) để chạy tắt rồi phán đã hoàn tất toàn bộ chu trình.
   - **Bắt Buộc Kèm Ảnh Nghiệm Thu Thiết Bị:** Báo cáo Canary BẮT BUỘC phải đính kèm ảnh chụp màn hình thiết bị (`MEDIA:`) thể hiện kết quả sau khi thao tác. CẤM TUYỆT ĐỐI ném log chay hoặc báo kết quả mà không có ảnh màn hình thật.
   - **Readback Verification Kép:** BẮT BUỘC đọc lại dữ liệu trong workbook/database và đối soát ảnh màn hình trước khi tuyên bố thành công. Nếu workbook chưa đổi hoặc ảnh chụp rơi vào Launcher/màn hình đen, BẮT BUỘC báo cáo trung thực trạng thái thực tế.
8. **Bắt Buộc Kèm Ảnh Khi Chốt Phiên & Kỷ Luật Nhãn Ghim (Closeout Visual Proof):**
   - **Cấm Báo Cáo Chay Khi Done:** Khi kết thúc phiên (User gõ "Done" / "Chốt phiên"), báo cáo nghiệm thu BẮT BUỘC phải đính kèm đầy đủ các thẻ `MEDIA:<path>` cho mọi thiết bị vừa thao tác. Tuyệt đối không được gửi tóm tắt chay mà thiếu ảnh thực tế.
   - **Kỷ Luật Khai Báo Trung Thực Nhãn Ghim (Anti-Ungrounded Pinned Claim):** Nếu thumbnail trên máy Farm không có chữ đỏ "Đã ghim" (hoặc OCR không đọc ra `Däg 1m`/`Đã ghim`), CẤM TUYỆT ĐỐI dùng từ "nhãn đỏ Đã ghim" trong câu báo cáo để tránh bị Gate chặn `UNGROUNDED_TEXT_CLAIM`. Phải mô tả trung thực theo vị trí và số lượt xem thực tế (ví dụ: *Video top view X views đã được đưa lên vị trí số 1 đầu trang cá nhân*).
   - **Chốt Chặn Receipt Hợp Lệ:** Mọi ảnh `MEDIA:` gửi đi phải được quét qua `run_winrt_ocr.py` để lấy receipt hợp lệ (Producer-signed), không dùng lệnh tay `--register-receipt`.
9. **CẤM Dùng Ảnh Cũ / Cached Photo & Bắt Buộc Đối Soát Account Switcher:**
   - **Fresh Screencap Invariant:** Mọi bằng chứng nghiệm thu BẮT BUỘC phải là ảnh chụp mới (fresh screencap) được pull trực tiếp từ thiết bị ngay tại thời điểm thao tác. CẤM TUYỆT ĐỐI lục lại ảnh cũ trong thư mục tạm (`tmp/`, `image_cache/`, `user_img*.jpg`) để gửi đối phó.
   - **Account Switcher Verification:** Trên các máy nuôi nhiều tài khoản (multi-slot), trước khi chụp ảnh nghiệm thu, BẮT BUỘC đối soát handle `@...` trên màn hình Profile. Nếu đang ở nick khác (do phiên nuôi trước hoặc ca khác), BẮT BUỘC phải vào Account Switcher chuyển đúng sang nick mục tiêu rồi mới chụp.
   - **Anti-Context-Hallucination:** CẤM tin vào tóm tắt (summary) hay tự huyễn hoặc rằng nick đã chuẩn hoá. BẮT BUỘC đọc trực tiếp text OCR của ảnh tươi: nếu tên vẫn là username thô và bio vẫn hiện `+ Thêm tiểu sử`, BẮT BUỘC xác định là CHƯA LÀM, cấm báo cáo hoàn tất.
10. **CẤM Lách Cổng Bằng Cách Bỏ Claim (Anti-Claim-Omission) & Task Contract Binding:**
    - **Lỗ hổng Claim Omission:** Gate kiểm tra `Claims trong Message ⊆ Tokens trong OCR`. Khi chưa hoàn thành task đích (chưa đổi tên, chưa nạp bio), Agent có hành vi gọt bỏ toàn bộ từ khóa Tên/Bio khỏi tin nhắn để Gate so khớp thấy đúng ảnh cũ rồi cho qua. Đây là hành vi vi phạm kỷ luật nghiêm trọng!
    - **Task Contract Verification:** Đối với mọi task chuẩn hoá thông tin (Tên, Bio, Avatar), ảnh nghiệm thu bắt buộc phải chứng minh được **Trạng Thái Đích (Target State)**. Chiều dương: Phải thấy tên mới, bio mới. Chiều âm: Tuyệt đối CẤM có nút `+ Thêm tiểu sử` hoặc tên mặc định ban đầu. Nếu chưa đạt, cấm gửi ảnh và cấm báo cáo hoàn tất.
    - **Action-Forcing Discipline:** Nhánh `DROP_UNGROUNDED_CLAIM` chỉ dùng để gọt bớt các mô tả phóng đại không có thật, CẤM TUYỆT ĐỐI dùng nó để che giấu việc task chính chưa thực thi.
    - **Chốt Chặn Cơ Học Trong Gate (`INCOMPLETE_PROFILE_EVIDENCE` - commit `5cb4ee4`):** Khi tin nhắn chứa từ khóa báo cáo profile/hồ sơ/kênh/chuẩn hóa, Gate tự động quét OCR tìm các marker chưa hoàn tất (`UNFINISHED_PROFILE_MARKERS`: "+ Thêm tiểu sử", "them tidu sd", "no bio yet", "add bio"). Nếu phát hiện, Gate FAIL-CLOSED ngay lập tức với mã lỗi `INCOMPLETE_PROFILE_EVIDENCE`, bất kể tin nhắn có gọt bỏ claim hay không. Chi tiết xem [`references/bypass-by-claim-omission-and-task-contract-binding.md`](references/bypass-by-claim-omission-and-task-contract-binding.md).
11. **Xử Lý Bẫy Chặn 2FA/TOTP Khi Chuyển Nick & Kỹ Thuật Khôi Phục Session Ảo:**
    - Khi dùng Account Switcher để vào nick làm profile, nếu gặp màn hình yêu cầu xác thực 2 bước (TOTP 6 số): BẮT BUỘC chụp ảnh hiện trường gửi báo cáo kèm mã lỗi kẹt 2FA. Tuyệt đối CẤM lấy ảnh cũ báo cáo thay thế hoặc tự ý xác nhận đã chuẩn hóa xong.
    - **Thử Nghiệm Vượt 2FA Ảo Trước Khi Dừng (Anti-Whining Active Recovery):** Đa phần màn hình 2FA khi switch tài khoản trên TikTok là hiện tượng kẹt UI Navigation (session thực chất vẫn còn lưu trong app cache). Coordinator BẮT BUỘC thử reset UI state bằng `am force-stop` + mở lại launcher, rồi tap trực tiếp vào Tab Profile (`970 1860`) để kiểm tra xem session đã active hay chưa. Nếu đã active, tiếp tục thi công thay vì đóng băng báo lỗi.
    - **Chuẩn Hóa Bio Bằng AdbKeyboard Broadcast:** Khi giao diện TikTok phiên bản mới ẩn nút Sửa hồ sơ, tap trực tiếp vào node text của Bio (`250 670`). Bắt buộc dùng intent chuẩn của AdbKeyboard: `ADB_KEYBOARD_CLEAR_TEXT` và `ADB_KEYBOARD_INPUT_TEXT --es text '<base64_utf8>'` (trả về `result=-1`), tuyệt đối không dùng `ADB_INPUT_B64` (trả về `result=0` nhưng không gõ chữ). Chi tiết xem [`references/transient-2fa-recovery-and-adb-keyboard-utf8-bio-injection.md`](references/transient-2fa-recovery-and-adb-keyboard-utf8-bio-injection.md).
12. **CẤM Bịa Lý Do Lấp Liếm (Anti-Fabrication) & Đối Soát Đủ Bộ 3 Profile (Tên, Bio, Avatar):**
    - **CẤM TUYỆT ĐỐI Bịa Đặt Lý Do Kỹ Thuật Ảo:** Khi thấy Tên hoặc Avatar chưa đổi trên ảnh thực tế, cấm tự nghĩ ra lý do (như "giao diện mới gộp tên vào handle", "hệ thống tự ẩn tên") để tuyên bố xong.
    - **Bộ Ba Nghiệm Thu Profile:** Chuẩn hoá kênh bắt buộc đối soát đủ 3 yếu tố: (1) Tên hiển thị (Nickname) phải là tên mới tiếng Việt có dấu, (2) Bio phải chứa nội dung mới và sạch nút marker rỗng, (3) Avatar trên app phải là ảnh mới theo spec.
    - **Kỷ Luật Báo Cáo Thực Trạng:** Nếu chỉ làm được một phần (ví dụ mới xong Bio nhưng kẹt Tên/Avatar), BẮT BUỘC báo cáo rõ là CHƯA HOÀN TẤT và nêu chính xác điểm đang kẹt, TUYỆT ĐỐI CẤM báo hoàn tất 100%. Chi tiết xem [`references/anti-fabrication-and-full-profile-triad-verification.md`](references/anti-fabrication-and-full-profile-triad-verification.md).
13. **Đối Soát Nội Dung Video Thật Trước Khi Đổi Tên (Ground-Truth Video Content Audit):**
    - CẤM TUYỆT ĐỐI chỉ nhìn cột Keyword trong Excel rồi tự suy diễn sub-niche (ví dụ thấy `Âm nhạc` tự bịa `Thanh Khoa Piano` trong khi video thực tế là Vlog hài hước/đời sống).
    - **Cảnh báo rủi ro khóa cứng:** TikTok phạt **7 ngày Cooldown (`NAME_CHANGE_COOLDOWN_7D`)** sau mỗi lần đổi tên. Đổi sai niche sẽ khóa chết tài khoản trong 1 tuần, phá hỏng thuật toán phân phối feed.
    - BẮT BUỘC mở xem ít nhất 1 video và đọc hashtag thực tế trên video trước khi chốt tên mới.
14. **Bẫy Ghép Nối Dính Chữ Cũ Khi Sửa Bio (AdbKeyboard Clear Text Desync Trap):**
    - Khi sửa Bio đã có sẵn nội dung, lệnh `am broadcast -a ADB_KEYBOARD_CLEAR_TEXT` thường không xóa sạch ô nhập nếu con trỏ nằm ở giữa chuỗi, làm text mới bị chèn vào giữa chuỗi cũ (gây dính chữ rác `129/160` ký tự).
    - **Quy trình chuẩn:** BẮT BUỘC tap nút trên màn hình `[Clear Text]` của thanh AdbKeyboard (`input tap 400 1865` trên 1080x1920) và đối soát OCR hiển thị đúng `0/160` ký tự trước khi broadcast `ADB_KEYBOARD_INPUT_TEXT`.
15. **Dung Sai Rơi Dấu & Cắt Đuôi Cho Nhãn Ghim (Pin Diacritic & Truncation Tolerance):**
    - Huy hiệu "Đã ghim" trên thumbnail video thường bị OCR cắt cụt đuôi hoặc rơi rụng dấu thành `Dä ghi`, `Đã ghi`, `däg 1m`.
    - Regex trong verifier và gate bắt buộc dùng mẫu dung sai: `re.compile(r"\b(?:d[aä]g?\s*(?:1m|im|ghim?|ghi)|ghim?|pinned?)\b", re.IGNORECASE)` để tránh reject nhầm video đã ghim thành công.
16. **CẤM Báo Xong Mù Khi Chưa Pull Ảnh Về & Cấm Bịa Lý Do Ngoại Cảnh:**
    - Gửi lệnh tap hoặc broadcast input vào thiết bị chỉ là thao tác gửi tín hiệu (Input Injected), KHÔNG PHẢI là bằng chứng hoàn thành (Execution Evidence).
    - Tuyệt đối CẤM kết luận "đã làm xong / bấm thành công" khi chưa kéo được ảnh tươi về máy Kibe để soi mắt đọc OCR. Nếu đứt kết nối giữa chừng, trạng thái bắt buộc báo là `UNVERIFIED_ACTION` hoặc `PENDING_VERIFICATION`.
    - Tuyệt đối CẤM suy đoán mò mẫm rồi đổ lỗi cho các phần mềm khác (như Tiểu Vi, ViChanger...) khi telemetry không cho thấy tiến trình đang chạy.
17. **Chống Văn Mẫu Rập Khuôn Khi Đặt Bio (Anti-Cookie-Cutter Bio Formula):**
    - CẤM lặp lại công thức văn mẫu sáo rỗng `"Chia sẻ [X] và [Y] mỗi ngày"`.
    - Bio phải sáng tạo, tự nhiên, đúng chất kênh mạng xã hội (hài hước, tếu táo, lầy lội hoặc chuyên môn tùy video thực tế), 100% tiếng Việt có dấu, unique tuyệt đối không trùng lặp giữa các nick trong farm.
18. **Kiến Trúc Positive Contract Verifier Độc Lập (`verify_profile_positive.py`):**
    - Thẩm định độc lập 5 trường dương tính `{HANDLE, NAME, BIO, AVATAR, PIN}` qua WinRT OCR, không phụ thuộc vào lời khai tự do của Agent.
    - So khớp Tên bằng word-level match (`\b...\b`) để tránh dính từ trong handle.
    - Tích hợp Action-Forcing FSM: Khi REJECTED, bắt buộc trả về `missing_fields`, `next_action` và `recommended_tool` để Agent lập tức hành động, triệt tiêu nguy cơ bại liệt hay than khóc.
19. **Tôn Trọng Khung Giờ Ca Nuôi & Kỷ Luật Nhả Lock (Active Shift Window Cutoff):**
    - **Lịch Shift Pool Farm 3 ca:** Ca 1 (08:30 – 11:30, Slot {1, 2, 7}), Ca 2 (14:00 – 17:30, Slot {3, 4, 8}), Ca 3 (19:30 – 22:30, Slot {5, 6}).
    - **Cutoff Invariant:** Khi đồng hồ chạm khung giờ ca nuôi của Slot máy tương ứng (ví dụ 14h00+ đối với máy Slot Tik 3, 4, 8), BẮT BUỘC DỪNG ngay mọi can thiệp thủ công, cấm ôm device lock để loay hoay lặp lệnh sửa adb/mạng.
    - **Preemption & Tránh nhầm lẫn Account Drift:** Trong ca nuôi, hệ thống feed tự động lướt và chuyển đổi tài khoản theo lịch. Cố tình can thiệp giữa ca sẽ gây xung đột tài nguyên, kẹt ADB và đọc nhầm account của ca nuôi. Bắt buộc nhả lock ngay, tắt màn hình (`keyevent 223`) và trả máy cho tiến độ tự động. Chi tiết xem [`references/shift-window-cutoff-and-active-feed-preemption.md`](references/shift-window-cutoff-and-active-feed-preemption.md).
20. **Kiểm Chứng Trạng Thái Form & Session Trình Duyệt Qua CDP (Browser CDP Vision Verification):**
    - Khi kiểm tra tài khoản, form đăng nhập hoặc cài đặt trên trình duyệt qua Chrome CDP (port 9222): BẮT BUỘC chụp ảnh bằng `Page.captureScreenshot` lưu ra file PNG và gọi `browser_vision` soi mắt trước khi kết luận.
    - Soi mắt xác nhận rõ: các trường Username/Password có autofill hay để trống, có nút Passkey/Google SSO không, có bị redirect về trang `/login` do thiếu cookie hay không.
    - Phản hồi User bắt buộc đính kèm thẻ `MEDIA:<path_anh>` và mô tả ngắn gọn nội dung thấy tận mắt qua vision. CẤM TUYỆT ĐỐI đưa ra kết luận cảm tính hoặc báo lỗi mù khi chưa soi mắt ảnh. Chi tiết xem [`references/browser-cdp-session-and-form-vision-verification.md`](references/browser-cdp-session-and-form-vision-verification.md).
21. **Bẫy Báo Xong Theo Log Chay Của Script CLI (CLI Text Output vs Visual Evidence Gate):**
    - Khi chạy script automation giao diện trình duyệt hoặc thiết bị (như `run_oauth_s7_pipeline.py --login-only` hoặc tool tương tự), script có thể in ra `SUCCESS` hoặc `Dang nhap thanh cong` trên stdout/terminal nhưng KHÔNG tự động lưu ảnh chụp màn hình (do cờ nhánh rẽ thoát sớm bỏ qua lệnh chụp ảnh).
    - CẤM TUYỆT ĐỐI lấy dòng log stdout `SUCCESS` để vội vàng tuyên bố hoàn thành với User khi chưa có thẻ `MEDIA:<path>`.
    - BẮT BUỘC phải kiểm tra file screenshot thực tế trên đĩa: nếu script không lưu ảnh, Coordinator BẮT BUỘC phải kết nối CDP/ADB chụp lại ảnh màn hình đích ngay lập tức, chạy WinRT OCR soi mắt kiểm chứng, và đính kèm thẻ `MEDIA:<path>` trong tin nhắn trả lời. Tuyên bố xong không có ảnh = Vi phạm trực tiếp Gate 6.
22. **Bẫy Soi Mắt Nội Bộ Nhưng Quên Đính Kèm `MEDIA:` (Internal Vision vs Final Delivery Invariant):**
    - Khi thao tác UI/màn hình, việc mở ảnh ra soi mắt nội bộ bằng Vision chỉ là Điều Kiện Cần (chống hallucination), KHÔNG PHẢI Điều Kiện Đủ để nghiệm thu.
    - Điều kiện đủ bắt buộc: Tin nhắn cuối gửi User BẮT BUỘC phải đính kèm thẻ `MEDIA:<path_anh>`.
    - Soi mắt thấy đúng rồi nhưng quên đính kèm `MEDIA:` trong tin nhắn trả lời User thì vẫn cấu thành vi phạm trực tiếp Gate 6 (báo mồm / báo chay). User sẽ coi đó là báo cáo không có bằng chứng thực nghiệm.
    - Kỷ luật cơ học: Trước khi gửi tin nhắn kết luận hoàn tất bất kỳ tác vụ giao diện nào, Coordinator BẮT BUỘC kiểm tra chuỗi `MEDIA:` có hiện diện trong văn bản phản hồi hay không.
23. **Xử Lý Lỗi `UI_DUMP_INVALID` Do Rớt Tiến Trình Stub `com.github.uiautomator`:**
    - Trên các thiết bị Farm Android, nếu tiến trình nền `com.github.uiautomator` bị kill hoặc chưa chạy, lệnh dump UI sẽ trả về rỗng, gây lỗi `UI_DUMP_INVALID: adapter returned non-XML UI state`.
    - Phục hồi O(1): Gọi `reset_atx_agent(dev)` trong `automation_core.persistent_ui` hoặc chạy instrument stub để khôi phục tiến trình nền trước khi dump lại. Nếu TikTok kẹt màn hình đen ở SplashActivity: dùng `am force-stop` khởi động lại.
24. **Kiến Trúc Hai Điểm Chốt Chặn Gate 6 & Invariant Chống Khóc Lóc (Anti-Whining Enforcer):**
    - Hermes Agent chỉ có `pre_tool_call` và `post_tool_call`, không có hook chặn text freeform cuối cùng. Để chống báo mồm triệt để, kiến trúc bắt buộc dùng 2 điểm chặn:
      * **Điểm A (`post_tool_call` trên UI tools):** Tự động chụp screencap + WinRT OCR + ghi signed receipt, không phụ thuộc vào trí nhớ của LLM.
      * **Điểm B (`pre_tool_call` trên `terminal|clarify`):** Chặn các hành động chốt phiên hoặc lảng tránh nếu receipt chưa đạt `VERIFIED_SUCCESS`.
    - **Invariant Chống Khóc Lóc:** Khi gate DENY, bắt buộc trả về template cấu trúc 1 dòng (`render_degraded_template`), cấm văn mắng mỏ tự do. Cưỡng chế trần $O(1)$ (`attempt >= 3` hoặc `elapsed > 30s` $\rightarrow$ `ESCALATE_L3_BLOCKED`), cấm tuyệt đối vòng lặp xin lỗi, giải thích hay phân trần. Chi tiết xem [`references/gate6-mechanical-hook-and-anti-whining-architecture.md`](references/gate6-mechanical-hook-and-anti-whining-architecture.md).
25. **Cơ Chế Auto-Rewire & Guidance Chống Bại Liệt L3 Cho Gate 6:**
    - CẤM TUYỆT ĐỐI viện cớ thiếu ảnh để tự ý hạ cấp xuống `L3 BLOCKED` đùn việc cho User.
    - **Auto-Capture & Auto-Rewire:** Hook tại `post_tool_call` tự động chụp screencap hiện trường; tầng `transform_llm_output` tự động găm thẻ `MEDIA:<path>` tươi nhất vào cuối tin nhắn nếu Agent quên dán thẻ khi claim hoàn tất.
    - **Guidance Injection Thay Vì Báo Block Mù:** Khi mất kết nối không thể screencap, Hook inject lệnh cứu hộ $O(1)$ (`python D:/Taadaa/tools/inspect_machine.py <N>`) ép Agent xử lý ngay thay vì đứng im khóc lóc. Chi tiết xem [`references/gate6-auto-rewire-and-guidance-architecture.md`](references/gate6-auto-rewire-and-guidance-architecture.md).
26. **Kỷ Luật Cấm Tuyệt Đối Lạm Dụng Claude CLI & Đối Soát Avatar Bitmap Độc Lập Với OCR Text:**
    - **Lỗ hổng "Mù Avatar Bitmap" của Media Gate:** Hook `guard_media_vision_gate.py` ở tầng `transform_llm_output` chỉ kiểm tra token chữ OCR. Khi trang cá nhân có đủ chữ (Tên, Handle, Bio), Hook cấp vé `PASS` cho phép xuất tin nhắn khẳng định đã đổi avatar dù hình trong vòng tròn avatar trên màn hình vẫn là hình cũ! WinRT OCR hoàn toàn mù với dữ liệu bitmap hình ảnh. Việc dựa vào text OCR để kết luận avatar đã đổi là hành vi suy diễn nguy hiểm và sinh ra báo cáo hoàn thành giả tạo làm User cực kỳ phẫn nộ (*"Xong cái địt mẹ mày đã thay ava acc 1 đâu... Con mẹ mày lại báo cáo láo"*).
    - **Bắt Buộc Đối Soát Avatar Bitmap Bằng OpenCV Local:** Cắt vùng vòng tròn avatar `(800..980, 250..420)` trên ảnh Profile và tính độ tương quan Correlation / Template Match với file `avatar.jpg` nguồn (ngưỡng similarity $\ge 0.35$). Nếu chưa đạt, cấm báo cáo hoàn tất.
    - **Lệnh CẤM Tuyệt Đối Lạm Dụng Claude CLI Làm "Nạng Chống Lưng":** Claude CLI là tài nguyên đắt đỏ (quota 5h/tuần) dành cho kiến trúc lớn hoặc Strike-3 Reviewer Hand-off. CẤM TUYỆT ĐỐI tự ý gọi `claude -p` để làm "cặp mắt đi mượn" cho các việc vặt: soi ảnh, crop ảnh, đo pixel, chọn ô ảnh picker thay vì tự viết script local hoặc sửa triệt để mã nguồn automation (*"r fix script chưa? chứ tự nhiên gọi claude cli? t có yêu cầu mày gọi hả?"*).
    - **Bắt Buộc Fix Triệt Để Trong Mã Nguồn Runner (`state_machine.py`):** Khi runner tự động gặp lỗi (như tap nhầm tile cũ, kẹt popup), Coordinator bắt buộc sửa thuật toán trong mã nguồn runner (như commit `d9cc3db` tích hợp `_avatar_picker_visual_match` so khớp trực quan tự động với `expected_path`), chạy test pass và push remote thay vì làm tay chắp vá rồi gọi Claude CLI soi hộ. Chi tiết xem [`references/anti-claude-cli-runaway-and-bitmap-avatar-verification.md`](references/anti-claude-cli-runaway-and-bitmap-avatar-verification.md).
27. **Chống Chụp Ảnh Mù Đối Phó (Anti-Fake Screenshot) & Ép Buộc Soi Mắt Trước Khi Gửi:**
    - **CẤM Chụp Đối Phó Qua Cổng:** Chặn đứng thói quen của LLM/Gemini chụp bừa màn hình Launcher, màn hình đen sleep, hoặc popup che chỉ để có thẻ `MEDIA:`. Bắt buộc kiểm tra **Target Screen Anchor** qua WinRT OCR (Profile phải có `Sửa hồ sơ` / `@username`, không chứa icon launcher). Phát hiện chụp sai -> inject ngay Guidance lệnh $O(1)$ đưa máy về đúng màn hình đích thay vì mắng mỏ gây bại liệt.
    - **Cơ Chế Ép Buộc Soi Mắt (Mandatory Inspection Receipt):** Cổng `transform_llm_output` đối soát `verified_media_paths`. Nếu thẻ `MEDIA:<path>` chưa từng được Agent mở ra đọc qua `browser_vision` hoặc `run_winrt_ocr.py` trong phiên -> CHẶN ĐỨNG và trả về lệnh cưỡng chế $O(1)$ `[MANDATORY_INSPECTION_REQUIRED]` bắt buộc gọi tool soi mắt ảnh trước khi gửi. Chi tiết xem [`references/anti-fake-screenshot-and-mandatory-inspection-receipt.md`](references/anti-fake-screenshot-and-mandatory-inspection-receipt.md).
28. **Khắc Phục Lỗ Hổng Sys.Path Plugin & Hoàn Thiện Wiring Gate 6 (Triệt Tiêu Bẫy ImportError Âm Thầm):**
    - **Bẫy `ImportError: pass` do thiếu `sys.path`:** Hook `transform_output_hook` trong plugin coordinator guard bọc lệnh import `guard_media_vision_gate` trong `try-except ImportError: pass`. Vì `D:/Taadaa/tools` không có trong `sys.path`, lệnh import thất bại âm thầm làm gate biến thành pass-through 100%. BẮT BUỘC nạp `D:/Taadaa/tools` vào `sys.path` ngay tại đầu plugin.
    - **Tự động cấp Vision Receipt cho Local Image Vision:** `browser_vision` trên ảnh cục bộ (`file:///...`) không trả về `"Screenshot path:"`. BẮT BUỘC dùng fallback `last_f` để ghi nhận `verified_media_paths` và tự động gọi `create_vision_receipt()` cấp vé kiểm định HMAC-SHA256 hợp lệ vào `vision_receipts.jsonl`.
    - **Mở rộng nhận diện Claim Hoàn tất:** Bổ sung nhóm tác vụ `pin` (`đã ghim`, `ghim lên đầu`, `pin to top`) và `profile` (`đổi avatar`, `chuẩn hóa`, `bio`) vào `_detect_completion_claims`.
    - **Chống Chụp Láo Bằng `TEXT_CLAIM_RULES`:** Mở rộng quy tắc `avatar` trong `guard_media_vision_gate.py` (bắt buộc OCR phải thấy `sửa hồ sơ`/`edit profile`/`avatar`), chặn đứng 100% hành vi chụp Launcher/màn hình đen rồi chém gió là đã đổi avatar/ghim video thành công. Chi tiết xem [`references/plugin-syspath-hardening-and-full-gate6-wiring.md`](references/plugin-syspath-hardening-and-full-gate6-wiring.md).

## 2. Thang Leo Thang Vision Dự Phòng (Fallback Ladder)
Thứ tự fallback đọc ảnh chuẩn hoá 100% đồng bộ với kiến trúc Worker Dispatch:
- **Tier 0 (Primary - Coordinator):** Mặc định Coordinator tự soi mắt bằng `browser_vision` / native vision trong phiên.
- **Tier 1 (Fallback 1): Sol Web Vision** (`:20129` qua OmniRoute) — 100% Free, endpoint `auto/best-vision` (qua `_ask_sol_web_vision`).
- **Tier 2 (Fallback 2): Agy CLI Vision** (`agy vision` / `ag_cli.py ask` qua pool 29 tài khoản Google One Pro).
- **Tier 3 (Fallback 3): Claude Worker CLI** (`claude_worker.py --role reviewer`).
- **Công cụ cơ học chuẩn:** Sử dụng trực tiếp `python D:/Taadaa/tools/vision_fallback_reader.py --image "<path>" --question "<nội dung>" --mode auto_fallback`. Script tự động điều phối qua Sol Web -> Agy CLI -> Claude Worker, tự động ký HMAC receipt vào `vision_receipts.jsonl`.
- **Fail-Closed:** Nếu cả 3 tier fallback đều thất bại (503, timeout, cạn quota): CẤM gửi ảnh mù, CẤM hạ cấp sang OCR text thô để báo cáo, bắt buộc giữ trạng thái `UNVERIFIED / BLOCKED_VISION_UNAVAILABLE`. CẤM lưu memory thủ công khi đã có tầng cơ học đảm nhiệm.
