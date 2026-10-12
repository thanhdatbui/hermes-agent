# Xử Lý Khi Closeout Gate Bị REJECTED / Dưới 85 Điểm

## 1. Kỷ Luật: CẤM DỪNG LẠI "KHÓC" HOẶC ĐẦU HÀNG Ở L3
- Khi `closeout_gate.py` trả về `Verdict: REJECTED` hoặc điểm < 85:
  * **CẤM TUYỆT ĐỐI** Coordinator dừng lại xin phép đóng phiên, ngụy biện "L3 BLOCKED" hay bỏ dở task.
  * Phải kiên trì bám đuổi và sửa chữa các lỗi chỉ ra trong `KEY FINDINGS` và `JUDGE NOTES` cho tới khi đạt `APPROVED (>= 85)`.

## 2. Các Lỗi Phổ Biến Khiến Reviewer Trừ Điểm Khắt Khe
1. **Coupling & Circular Import / Monkeypatching Hack**:
   - Production code không được dựa vào `sys.modules` hay sửa module động để pass test.
   - Luôn dùng Dependency Injection (truyền tham số cấu hình rõ ràng) hoặc đọc trực tiếp từ `os.environ`.
2. **Exception Handling Quá Rộng (`except Exception`)**:
   - Nuốt lỗi rộng khiến Reviewer nghi ngờ về khả năng ẩn giấu bug nghiêm trọng.
   - Luôn thu hẹp exception thành các lỗi cụ thể: `(urllib.error.URLError, urllib.error.HTTPError, OSError)`.
3. **Regex Lỏng Lẻo (Đặc biệt là OTP / Mã Xác Thực)**:
   - Regex 6 số đơn thuần `r"\b\d{6}\b"` dễ bắt nhầm mã màu CSS hex, số thập phân hoặc thẻ nội dung.
   - Bắt buộc kiểm tra ngữ cảnh (từ khóa `code`, `mã`, `otp`), lọc sender domain (`openai.com`, `chatgpt.com`), và lọc email cũ theo mốc thời gian `since`.
4. **Chống Purge Nhầm (False Positive Safety)**:
   - Loại bỏ các tín hiệu mơ hồ như "Lỗi xác thực" khỏi bộ marker deactivate.
   - Bảo đảm email rỗng không bao giờ khớp tài khoản.

## 3. Thang Leo Thang Sửa Chữa (Remediation Ladder)
- **Vòng 1 & 2 (Sol Repair / Worker Remediation)**:
  * Đọc `KEY FINDINGS` từ file log gate.
  * Dispatch Worker sửa tập trung các điểm coupling, regex, exception narrowing.
  * Bổ sung unit test focused chứng minh tính toàn vẹn (schema, timeout resilience, rotation).
- **Vòng 3+ (Strike 3 Reviewer Hand-off sang Claude CLI)**:
  * Khi bị từ chối 3-4 lần liên tiếp trên cùng scope_hash, kích hoạt ngay hand-off sang Claude CLI (`claude_quota_guard.py`).
  * Kiểm tra quota an toàn trước khi gọi (`python D:/Taadaa/tools/claude_quota_guard.py status`).
  * Ra lệnh cho Claude Code CLI đọc toàn bộ target files và test suite, tự sửa mã nguồn (self-remediation) đến khi đạt chuẩn production-grade.
  * Chạy lại `closeout_gate.py` nghiệm thu để đạt `Verdict: APPROVED (>= 85)`.

## 4. Kỷ Luật Git Commit & Push Sau Khi Được Duyệt
- **Tránh Lỗi Hook `pre-push.sh`**:
  * Khi `closeout_gate.py` đã trả về `APPROVED (>= 85)`, Coordinator cần `git add` đúng các files đã thẩm định và commit chuẩn `feat(...)` / `fix(...)`.
  * Không dùng `git push` trực tiếp nếu terminal guard của Coordinator chặn mặc định.
  * Ủy thác lệnh push qua Claude CLI (`python D:/Taadaa/tools/claude_quota_guard.py -p "Chạy git push origin main trong thư mục D:/Taadaa/tools và kiểm tra kết quả." --allowedTools "Bash(git *)" --dangerously-skip-permissions`) để hook pre-push xác nhận exit 0 và đồng bộ remote an toàn.

