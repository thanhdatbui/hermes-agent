# Hướng Dẫn Vận Hành & Kiến Trúc: Autonomous AI Recovery Agent (Code-First & Background Spawn)

## 1. Tổng Quan Kiến Trúc
Hệ thống AI Auto-Recovery tự động hóa giải phóng sự cố cho farm 80 máy TikTok theo nguyên tắc **Autonomous (Tự chủ 100%)** và **Code-First (Viết code trước - Chạy hàm vừa code thay tay)**.

## 2. Bẫy Kỹ Thuật (Pitfalls) Đã Khắc Phục
1. **Bẫy Telegram Bot API Self-Message:**
   - Khi script gửi tin nhắn alert (Tin nhắn 1) bằng `TELEGRAM_BOT_TOKEN`, Telegram Bot API coi đó là tin nhắn gửi ra và **tuyệt đối không gửi lại event trong `getUpdates`** cho chính bot đó để chống lặp vô hạn.
   - Do đó, không thể dùng Hermes Gateway long-polling để "lắng nghe" tin nhắn của chính mình.
   - **Giải pháp chuẩn:** Khi `send_farm_machine_alert()` gửi xong Tin nhắn 1 ➔ Lập tức `subprocess.Popen` kích hoạt ngầm `python -m ai_recovery.agent` độc lập không làm nghẽn tiến trình farm chính.

2. **Bẫy "Bấm Tay ADB / Fake AI":**
   - Tuyệt đối CẤM dùng if/else đoán lỗi hay bắn lệnh ADB thô (`input tap`) trực tiếp lên máy kẹt rồi mới viết code sau.
   - Nếu bắn lệnh ADB trước, máy thoát kẹt làm **mất hiện trường lỗi**, không còn môi trường thực tế để kiểm chứng đoạn code vừa viết.

## 3. Quy Trình 5 Bước Thực Thi Chuẩn Xác Trong `ai_recovery/agent.py`
1. **Pre-check Hiện Trường (Lock & dHash):**
   - Acquire Per-Device Lock (TTL 5 phút).
   - So khớp ảnh hiện trường (`screen_verifier.matches_alert` qua dHash Hamming distance). Nếu người dùng đã bấm tay hoặc màn hình tự đổi thì dừng lại.
2. **AI Suy Luận Ngữ Cảnh (`vision_client.py`):**
   - Nạp ảnh hiện trường + cây UI XML lên Model Vision (`ag/claude-opus-4-6-thinking`).
   - Phân tích bản chất kẹt và sinh đoạn code rule/handler mới cho runner (`feed_swipe_smoke.py` / `benign_popup.py`).
3. **Plan-Review Audit (`plan_reviewer.py`):**
   - Nạp code patch lên Model Review (`gpt-5.6-terra` combo plan-review max).
   - Bắt buộc nhận `VERDICT: APPROVED` mới thực hiện patch code vào repo (`code_patcher.py`).
4. **Test Trực Tiếp Trên Máy Đang Kẹt:**
   - Kích hoạt chính hàm vừa code chạy thử trên máy đang lỗi tại hiện trường.
   - Chụp lại màn hình sau khi chạy (`live_after`): Xác minh ảnh có thay đổi (`_images_differ`) xác nhận đã giải phóng thành công.
5. **Kiểm Thử Hồi Quy, Commit & Báo Cáo:**
   - Chạy test suite `pytest` xác nhận không có lỗi hồi quy.
   - `git commit` & `git push origin master` đồng bộ toàn farm.
   - Gửi Tin nhắn 2 (*Hướng sửa & Kết quả*) vào Telegram Farm Alerts:
     ```text
     🛠️ [AI AUTO-RECOVERY - MÁY XX]
     • Hướng sửa: <Giải thích lỗi kỹ thuật & code đã vá>
     • Kết quả: 🟢 THÀNH CÔNG — màn hình đã thay đổi sau lệnh ADB
     • Code patch: ✅ Đã commit <handler_name> -> <target_file> SHA <sha>
     • pytest: 28 passed in 19.93s
     • (Nếu đúng ý bạn im lặng bỏ qua, cần sửa cách khác hãy nhắn lại)
     ```
