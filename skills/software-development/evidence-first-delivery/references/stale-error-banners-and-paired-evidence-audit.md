# Stale Error Banners & Paired-Evidence Audit (Incident 2026-10-08)

## 1. Bối cảnh sự cố
Trong quá trình tự động hóa cập nhật thông tin bảo mật cho tài khoản Hotmail (`murtaghshandy156@hotmail.com`) trên GPM Browser:
- Script bắt nhầm mã màu CSS `#707070` làm OTP và điền vào form -> Microsoft trả về thông báo lỗi: *"That code didn't work. Check the code and try again."*.
- Script phát hiện lỗi, trích xuất lại đúng OTP thực tế (`041684`), nhập vào ô input và chụp ảnh Pre-submit (`canary_enter_real_otp_pre.png`).
- Do chưa submit lần 2, trên màn hình VẪN CÒN NGUYÊN dòng chữ đỏ *"That code didn't work"*.
- Coordinator gửi ảnh Pre-submit này cho User và khẳng định đã nhập xong mã, nhưng KHÔNG gửi kèm ảnh Post-submit ngay sau khi submit thành công.
- User phát hiện dòng chữ đỏ, bức xúc vì cho rằng agent "báo cáo láo / gửi ảnh đối phó".

## 2. Thẩm định độc lập từ Claude Code CLI (Root Cause Analysis)

### 2.1. Lỗi thiết kế Guard: Action-based vs State-based
- Cả Invariant Soi Mắt Đọc Ảnh và GATE 6 đều là guard định nghĩa theo hành động (*action-based*): chỉ kiểm tra xem agent có chụp đúng lúc không, ảnh có bị đen/trắng không.
- Guard thiếu kiểm tra ngữ nghĩa trạng thái (*state-based semantic check*): không đối chiếu xem nội dung chữ trong ảnh có mâu thuẫn trực tiếp với câu nói khẳng định thành công hay không.
- Guard được viết cho "happy path 1 lần thử", không có điều khoản cho "vòng lặp retry" (nơi form được điền lại nhưng banner lỗi của lần trước chưa biến mất).

### 2.2. Điểm mù nhận thức (Confirmation Bias)
- Agent biết mình đã sửa đúng hành động (đã bốc đúng OTP và điền vào ô).
- Khi soi ảnh, agent chỉ tìm đúng chi tiết xác nhận giả thuyết có sẵn (ô input có số đúng không) mà bỏ qua hoàn toàn các tín hiệu phủ định (banner đỏ, icon lỗi).
- Agent dùng nhận thức về hành động của mình để đè bẹp hiện thực khách quan trên màn hình.

### 2.3. Anti-Evidence & Stale Error Banner
- Ảnh Pre-submit trong lần thử lại trở thành "ảnh lưỡng tính": vừa chứa dữ liệu mới vừa chứa vết lỗi của lần thất bại trước.
- Không gửi ảnh Post-submit khiến người xem chỉ thấy duy nhất bằng chứng của lần thất bại.

## 3. Quy trình chuẩn hóa 4 bước (SOP)

1. **Pre-flight Sanitization:**
   - Trong vòng lặp retry, phải OCR toàn frame để kiểm tra xem còn vướng banner/toast lỗi cũ không.
   - So khớp ngữ nghĩa chuẩn hóa (case-insensitive, whitespace tolerant) với lỗi attempt N-1. Nếu khớp: cho phép gán nhãn `KNOWN_STALE_ARTIFACT: <nội dung>`. Nếu chuỗi lỗi mới: bắt buộc phân loại `NEW_ERROR`.
2. **Pre-submit Capture:**
   - Chụp khi input đã điền sạch sẽ và hợp lệ.
3. **Action & Post-submit Capture:**
   - Bấm submit và chụp ngay kết quả phản hồi trong <= 3s (trang chuyển hướng, popup đóng, banner thành công).
   - Giới hạn thời gian & Ngưỡng Escalation: Trạng thái chờ tối đa **<= 30 giây HOẶC <= 3 lần check UI (Whichever comes first)**. Chạm ngưỡng -> Dừng ngay, kích hoạt L3 BLOCKED, cấm loop lại chu kỳ mới trong bóng tối.
4. **Evidence Integrity Gate (Khóa chốt phát ngôn):**
   - **Mandatory Pairing:** CẤM phát ngôn câu khẳng định hoàn tất/thành công nếu thiếu một trong hai: Pre-submit VÀ Post-submit trong cùng 1 tin nhắn.
   - **Multilingual OCR-Overrides-Intent Veto:** Nếu OCR của ảnh gửi đi có chứa từ khóa phủ định/lỗi (Anh, Việt...: `That code didn't work`, `Error`, `Failed`, `Mã không đúng`, `Thất bại`...), OCR có quyền VETO tuyệt đối — CẤM khẳng định thành công.
   - **Mechanical Evidence Gate (`evidence_gate_verifier.py`):** Triệt tiêu self-attestation bằng code gate độc lập kiểm tra tệp ảnh, log OCR, keyword veto, và tính toàn vẹn của cặp ảnh pre/post.
   - **Self-As-First-Reader Check:** Tự thẩm định từ góc nhìn người ngoài không biết code: "Nếu chỉ nhìn ảnh này và đọc câu này, người ta có thấy mình đang nói dối không?". Nếu có -> DỪNG LẠI NGAY.

## 4. Công cụ kiểm chứng cơ học (Mechanical Evidence Gate V7 Bulletproof)
- Script: `D:\Taadaa\tools\evidence_gate_verifier.py`
- Kiểm tra độc lập cơ học (Zero Self-Attestation):
  - Tự động gọi native WinRT OCR đọc ảnh trực tiếp trên đĩa, cấm truyền chuỗi OCR giả từ caller.
  - **Triệt tiêu hoàn toàn self-attestation:** Loại bỏ hoàn toàn tham số chuỗi lỗi do agent tự khai báo (`--prev-error` bị cấm và xóa bỏ). Mọi trạng thái lỗi cũ (Stale error) CHỈ ĐƯỢC CHẤP NHẬN khi được chứng minh bằng file audit log attempt N-1 có chữ ký mật mã HMAC-SHA256 hợp lệ nằm trong thư mục chuẩn `D:/Taadaa/runtime/audit`.
  - **Kiểm tra file ảnh vật lý & Header:** Xác thực file ảnh tồn tại trên đĩa, dung lượng hợp lệ (> 1KB, không đen/trắng rỗng), và chữ ký định dạng header (PNG, JPEG, WEBP).
  - **Anti-Bypass Distinct Image Check (SHA256):** Bắt buộc ảnh Pre-submit và Post-submit phải là hai file vật lý độc lập có mã băm SHA256 khác nhau. CẤM TUYỆT ĐỐI truyền cùng 1 file ảnh hoặc clone để lừa gate!
  - **Word-Boundary Regex & NFC Normalization:** Chuẩn hóa Unicode NFC đối xứng và sử dụng Regex Word Boundaries (`\b`) cho toàn bộ danh sách veto keywords, triệt tiêu hoàn toàn false-positive (không bị match nhầm từ ghép) và false-negative (không bị lệch Unicode tiếng Việt).
  - Bắt buộc kiểm tra file ảnh Post-submit khi phát ngôn chứa từ khóa hoàn tất/thành công (MANDATORY_PAIRING_VIOLATION).
  - Cưỡng chế thời gian và số lần thử: `elapsed_seconds > 30.0` HOẶC `attempt_count >= 3` (whichever comes first) -> trả về `ESCALATE_L3_BLOCKED` (chạy sau bước kiểm tra ảnh vật lý hợp lệ).
  - **Tamper-Evident Audit Trail Persistence:** Tự động ghi log audit JSON bền vững vào `D:/Taadaa/runtime/audit/evidence_gate_<timestamp>_<uuid>_<verdict>.json` (lưu SHA256 của cả 2 ảnh, chữ ký HMAC-SHA256 chống làm giả, cờ `audit_persisted: true` và ghi log stderr nếu fail).
- Trả về JSON chuẩn machine-readable: `{"verdict": "PASS" | "VETO_REJECT" | "FLAGGED_STALE" | "ESCALATE_L3_BLOCKED" | "FAIL", "reason": "...", "audit_file": "...", "audit_persisted": true, "hmac_signature": "..."}`.
- Bắt buộc đính kèm artifact trong báo cáo bàn giao UI:
  `EVIDENCE_GATE: PASS | Verified by D:/Taadaa/tools/evidence_gate_verifier.py | Clean evidence confirmed`.
