# Strike 3 Reviewer Hand-off & Bổ Sung Telemetry Vượt Ngưỡng 85đ Closeout Gate

## 1. Bối cảnh & Cột Mốc Điểm 84/100 (Phiên Ngày 17/10/2026)

Trong quy trình chốt phiên tự động của Taadaa Farm qua `closeout_gate.py` (Reviewer Sol High trên `:20129`), một trong những cạm bẫy nguy hiểm nhất là **Vòng lặp cày điểm vô tận (Score Chasing Infinite Loop)**:
- Điểm số tiệm cận ngưỡng đạt nhưng bị chặn lại: Lần 1 đạt **75/100**, Lần 2 đạt **78/100**, Lần 3 đạt **84/100** (ngưỡng đạt là $\ge 85$).
- Khi trượt 3 lần liên tiếp trên cùng `scope_hash`, `closeout_gate.py` kích hoạt tín hiệu cưỡng chế cơ học:
  ```text
  [REVIEWER_HANDOFF_TRIGGERED: 3 consecutive rejections reached for scope_hash=9cc75ace8bc57eb7. Coordinator/Worker/Sol Repair MUST STOP guessing/repairing and hand the keyboard to the Reviewer (Claude CLI) to self-remediate, strictly scoped to: ...]
  ```

---

## 2. Kỷ Luật Tuyệt Đối Khi Kích Hoạt Strike 3 Reviewer Hand-off

1. **DỪNG MỌI HÀNH ĐỘNG SỬA MÒ (STOP GUESSING):**
   - Coordinator, Worker và `sol_repair.py` BẮT BUỘC DỪNG NGAY LẬP TỨC việc đoán mò hoặc tạo patch vòng thứ 4.
   - Không được phép nỗ lực "sửa thêm 1 tí" để nịnh reviewer vì các sửa đổi vụn vặt này thường tiếp tục bị trừ điểm kiến trúc/telemetry.
2. **BẮT BUỘC CHUYỂN GIAO CHO CLAUDE CLI (CLAUDE SELF-REMEDIATE):**
   - Chạy lệnh bàn giao tự động:
     ```bash
     python D:/Taadaa/tools/claude_worker.py --role worker --workdir "<repo>" --max-turns 15 --timeout 300 "Directly edit in place in the current repository without creating any worktrees. Do not touch other uncommitted files. Sửa các test và telemetry trong <files> theo findings của Closeout Gate: <findings>..."
     ```
   - Cung cấp toàn bộ `key_findings` và `judge_notes` của Sol High vào prompt của Claude CLI để Claude tự đọc diff, tự sửa code và tự viết bổ sung test.
3. **CẤM DÙNG CLARIFY ĐỂ HỎI CÓ TIẾP TỤC CHỐT PHIÊN KHÔNG:**
   - Trong quá trình chạy Closeout Gate, nếu gặp test fail hoặc reviewer reject, CẤM TUYỆT ĐỐI gọi `clarify` để hỏi user "Bạn có muốn tiếp tục tiến hành chốt phiên không?".
   - Hành vi này vi phạm nguyên tắc vận hành chủ động (Anti-Paralysis Invariant). Remediation loop là nhiệm vụ nội bộ bắt buộc phải tự động xử lý cho đến khi đạt `APPROVED` hoặc có bằng chứng `BLOCKED` vật lý thực tế.

---

## 3. 5 Hạng Mục Telemetry & Error Handling Quyết Định Giúp Vượt Ngưỡng 85đ

Qua phân tích các lần thẩm định từ 75 -> 78 -> 84đ của Sol High, các điểm cốt lõi để đạt điểm tối đa ở cột **Telemetry & Observability (15đ)** và **Test Evidence (25đ)** gồm:

### 1) Triệt tiêu bẫy nuốt ngoại lệ im lặng (Silent Exception Swallowing Trap)
* **Sai lầm phổ biến**: Dùng `try ... except Exception: return []` hoặc `pass` trong các hàm adapter/OCR. Reviewer coi đây là lỗi nghiêm trọng vì nó che giấu sự cố hạ tầng (screencap rỗng, WinRT crash, ADB pipe gãy, timeout) thành trạng thái `unknown`.
* **Chuẩn hóa**: Bắt buộc ghi log có cấu trúc đo thời gian và chỉ rõ nguyên nhân:
  ```python
  started = time.monotonic()
  try:
      ...
  except Exception as exc:
      reason = "timeout" if self._error_kind(exc) == "timeout" else "ocr_error"
      logger.warning("ocr_screen_failed reason=%s serial=%s elapsed=%.3f error_type=%s",
                     reason, self.serial, time.monotonic() - started, type(exc).__name__)
      return []
  ```

### 2) Xác thực chữ ký nhị phân ảnh (Magic Bytes Assertion)
* **Sai lầm phổ biến**: Chỉ kiểm tra kích thước sơ bộ `if not png or len(png) < 100:`. Nếu thiết bị trả về chuỗi text báo lỗi ADB hoặc banner HTML dài > 100 bytes, dữ liệu rác vẫn có thể vượt qua kiểm tra độ dài.
* **Chuẩn hóa**: Kiểm tra chính xác header PNG RFC:
  ```python
  if not png or len(png) < 100 or not png.startswith(b"\x89PNG\r\n\x1a\n"):
      reason = "invalid_screencap"
      logger.warning("ocr_screen_failed reason=%s serial=%s elapsed=%.3f", reason, self.serial, time.monotonic() - started)
      return []
  ```

### 3) Dọn dẹp file tạm bất biến (Deterministic Tempfile Cleanup in `finally`)
* **Sai lầm phổ biến**: Gọi `unlink()` trong khối `try`, nếu OCR văng timeout hoặc exception thì file tạm bị bỏ rơi trên đĩa, gây rò rỉ dung lượng khi chạy hàng trăm máy.
* **Chuẩn hóa**: Đặt việc xóa file trong khối `finally` kèm try-catch tránh crash do race condition trên Windows:
  ```python
  finally:
      if tpath is not None:
          try:
              Path(tpath).unlink(missing_ok=True)
          except OSError as exc:
              logger.warning("ocr_temp_cleanup_failed serial=%s error_type=%s", self.serial, type(exc).__name__)
  ```

### 4) Bộ Test Cases kiểm chứng nhánh lỗi (Negative & Resilience Testing)
Reviewer luôn trừ điểm nặng nếu test suite chỉ kiểm tra các nhánh thành công (Happy Path). Bắt buộc phải có các test sau:
1. `test_adapter_ocr_screen_telemetry`: Kiểm tra cả trường hợp screencap rỗng và screencap có header không hợp lệ (`NOT_A_PNG_HEADER_DATA`), assert log chứa `reason=invalid_screencap`.
2. `test_adapter_ocr_screen_cleanup_and_exception`: Giả lập hàm OCR văng `TimeoutError`, assert log ghi đúng `reason=timeout` và **assert `not created_paths[0].exists()`** để chứng minh file tạm đã bị xóa sạch sau lỗi.
3. `test_verify_after_tap_rescued_by_ocr_not_followed`: Kiểm tra khi OCR nhận diện text `"Follow"` (`not_followed`), hàm verify trả về status `"failed"` và gọi đúng `set_follow_failed()`.
4. `test_verify_after_tap_ocr_exception_falls_back_to_manual`: Kiểm tra khi OCR ném ngoại lệ, hàm ghi nhận log warning `follow_verify_ocr_fallback_failed` và rơi về `"manual"` an toàn.

### 5) Loại bỏ Dead Comments và Code Rác
* Không chèn các dòng comment vô nghĩa vào diff (như `# Luồng chuẩn: Không bỏ qua anchor`) mà không có logic code thay đổi thực tế đi kèm. Sol High sẽ phát hiện và ghi nhận vào key findings là diff rác không có giá trị cải tiến.
