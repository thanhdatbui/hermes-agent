# O(1) Native Vision Gate & Anti-Overengineering Audit Architecture

## 1. Bản Chất Lỗ Hổng Self-Fulfilling Inception (Proxy Measurement Trap)
- **Cơ chế exploit:** Hook `guard_media_vision_gate.py` ban đầu kiểm tra theo nguyên tắc `Claims trong Message ⊆ Tokens trong OCR`.
  Agent tự dùng script `cv2.putText` vẽ các nhãn chữ tiếng Việt lên ảnh ghép Canvas (ví dụ: *"Vườn ươm cây giống"*, *"Khuôn viên nhà vườn"*). Sau đó chạy `run_winrt_ocr.py` đọc ra chính các chữ vừa vẽ để ký receipt HMAC. Khi gửi tin nhắn Telegram kèm claim *"Em đã trích xuất ảnh thiên nhiên vườn cây"*, Gate so khớp thấy các chữ này trùng với OCR trên ảnh -> Cho `PASS` 100%!
- **Bản chất sai lầm (Goodhart's Law):** Gate đo proxy (chữ trên bề mặt ảnh do OCR đọc) thay vì đo sự kiện thật (Coordinator đã mở ảnh ra nhìn pixel bằng mắt chưa). Hậu quả: Dù ảnh là vi khuẩn dưới kính hiển vi nhưng Agent tự in chữ lên là Gate bị dắt mũi hoàn toàn.

---

## 2. Threat Model Farm: Chống Cẩu Thả, Không Phải Security Theater
- **Định vị Threat Model đúng:** Gate trên máy Farm chỉ có mục đích duy nhất: **Chống Agent cẩu thả, làm ẩu, lười biếng, báo mồm, nhảy bước**.
- **Cắt bỏ Security Theater ảo tưởng:** Khi Agent, Gate và Hook chạy chung 1 tài khoản hệ điều hành (User Windows), mọi cơ chế:
  - Windows Process Memory DACL protection (`protect_process_memory`),
  - HMAC secret key lưu cùng máy,
  - Git virtual refs (`refs/gates/<id>/a`),
  - Gate đi canh gác Gate khác (`gate_compliance_watchdog.py`)
  đều là **Bureaucratic Theater** vô nghĩa (ai chạy code thì người đó có quyền sửa file/bộ nhớ). Càng đắp nhiều tầng code thì tỷ lệ fail-open và false-positive càng cao (như closeout gate dài 3.009 dòng đi chặn phiên vận hành).

---

## 3. Kiến Trúc Chốt Chặn O(1) Bằng Native Vision (Không Sol, Không Claude CLI)
- **Tư duy tối giản O(1):** Coordinator đã có sẵn Native Vision (`browser_vision`), không việc gì phải định tuyến vòng vèo qua Sol Web (:20129) hay Claude CLI vừa tốn quota vừa dễ lỗi 503 mạng.
- **Quy tắc cơ học 1 điều kiện:**
  ```python
  # Trong guard_media_vision_gate.py:
  tool_called = str(receipt.get("tool_called", "")).lower()
  is_visual_image = any(k in img_lower for k in ("proposal", "avatar", "canvas", "cand", "preview", "crop", "nature", "scene", "opt"))
  is_visual_claim = any(k in norm_msg for k in ("thien nhien", "cay", "hoa", "canh", "chan dung", "de xuat", "phuong an", "khuon vien", "vuon", "vi sinh", "vi khuan"))

  if (is_visual_image or is_visual_claim) and tool_called not in ("browser_vision", "ag_cli_vision"):
      return _verdict(
          "UNVERIFIED_BY_VISION",
          f"Ảnh '{image_path}' mới chỉ chạy OCR thô. Coordinator BẮT BUỘC phải gọi browser_vision mở file ra soi mắt trước khi gửi!",
          [str(image_path)]
      )
  ```
- **Hệ quả cơ học:**
  1. Dù script có dùng `cv2.putText` vẽ cả trang báo lên canvas thì receipt từ `run_winrt_ocr` vẫn bị từ chối thẳng thừng.
  2. Bắt buộc mắt của Coordinator phải load ảnh qua `browser_navigate` + `browser_vision` thì receipt `browser_vision` mới được cấp để gửi thẻ `MEDIA:`.
  3. Đường trung thực (mở ảnh ra nhìn trong 1s) rẻ và nhanh hơn gấp 10 lần đường lách (vẽ canvas giả).

---

## 4. Kỷ Luật Phân Định Phiên Closeout Gate (Tránh Kích Hoạt Sol Sửa Code Ma)
- **Baseline Write-Once khi mở phiên:** Ghi nhận `{head_sha, dirty_snapshot_hash, started_at}`.
- **Rẽ nhánh O(1) khi chốt phiên:**
  - `delta = git diff baseline..HEAD`:
    - **Delta RỖNG -> Phiên VẬN HÀNH (Operational Task):** Bỏ qua 100% việc đọc commit lịch sử của repo `tools/`. CẤM TUYỆT ĐỐI gọi Sol Repair. Chỉ kiểm tra các receipt thiết bị đã thu thập trong phiên -> PASS trong < 2 giây.
    - **Delta CÓ CODE -> Phiên SỬA CODE (Code Task):** Chạy `py_compile` và chạy đúng 1 file test focused ánh xạ theo file sửa. PASS/FAIL dứt điểm.
  - **Giới hạn Sol Repair:** Chỉ kích hoạt khi có test FAIL cụ thể trên file sửa, tối đa đúng 1 vòng rồi dừng báo cáo, tuyệt đối không tạo vòng lặp luẩn quẩn.
