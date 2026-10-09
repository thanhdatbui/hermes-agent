# TikTok Interrupted Draft Resume & Failure Recovery Pattern (Case 97, 2026-09-21)

## 1. Ngữ cảnh & Nguyên nhân lỗi
- Khi upload video TikTok trên farm Android gặp gián đoạn (timeout, rớt socket ADB, network drop, hoặc crash giữa chừng sau khi render), TikTok tự động lưu video vào mục **Bản nháp (Draft)** trên trang Hồ sơ (Profile) của tài khoản.
- Trước đây, workflow upload ở bước `ACCOUNT_READY` tự động gọi `_delete_all_profile_drafts()` để cố xoá sạch bản nháp. Hậu quả:
  1. Nếu bản nháp không xoá được hoặc đang trong quá trình xử lý, flow bị dừng hoặc văng ra ngoài.
  2. Bỏ phí video đã render sẵn trong draft, hệ thống lại phải tải lại và push media từ đầu gây lãng phí tài nguyên farm.
  3. Lưới video Profile (`_profile_video_tile_records`) nếu đọc phải ô "Bản nháp: N" có thể tính nhầm vào số video đã publish, làm sai lệch baseline so sánh sau khi post.

## 2. Kiến trúc giải pháp (Canonical Pattern)
### Tầng 1: Nhận diện & Giữ bản nháp tại `ACCOUNT_READY`
- Không xoá mù quáng `_delete_all_profile_drafts` nếu profile có draft.
- Quét XML profile xem có chuỗi `"bản nháp"` hoặc `"draft"`:
  ```python
  if "bản nháp" in profile_xml.casefold() or "draft" in profile_xml.casefold():
      logger.info("[ACCOUNT_READY] Phát hiện bản nháp trên profile; giữ nguyên để resume đăng tiếp ở VIDEO_PICK")
      self.context.has_profile_draft = True
  else:
      self.context.has_profile_draft = False
  ```

### Tầng 2: Loại trừ ô Bản nháp khỏi Baseline Video Scan (`_profile_video_tile_records`)
- Khi quét các tile video đã xuất bản trên profile, loại trừ triệt để các tile chứa text, content-desc hoặc resource-id bản nháp:
  ```python
  tile_texts = " ".join(
      f"{child.attrib.get('text', '')} {child.attrib.get('content-desc', '')} {child.attrib.get('resource-id', '')}"
      for child in node.iter("node")
  ).casefold()
  if any(k in tile_texts for k in ("bản nháp", "draft", "drafts", ":id/draft", "/draft")):
      continue
  ```

### Tầng 3: Kích hoạt luồng Resume tại `VIDEO_PICK` (`_handle_video_pick`)
- Tại bước chọn video, nếu `context.has_profile_draft` hoặc XML hiện tại có bản nháp, ưu tiên gọi `_resume_draft_from_profile(adapter, xml_text)`.
- Bổ sung fail-safe: Nếu `_resume_draft_from_profile` thất bại (không tìm thấy item draft, hoặc không vào được composer), log warning và **tiếp tục fallthrough** xuống luồng upload video chuẩn từ disk/camera, tuyệt đối không làm kẹt pipeline:
  ```python
  if self.context.has_profile_draft or "bản nháp" in (xml_text or "").casefold() or "draft" in (xml_text or "").casefold():
      logger.info("[VIDEO_PICK] Phát hiện bản nháp đăng dở; kích hoạt flow mở bản nháp để đăng tiếp")
      if self._resume_draft_from_profile(adapter, xml_text):
          logger.info("[VIDEO_PICK] Đã mở bản nháp vào màn hình Đăng thành công")
          return True
      logger.warning("[VIDEO_PICK] Mở bản nháp không thành công; tiếp tục fallthrough luồng upload chuẩn")
  ```

### Tầng 4: Hàm thực thi `_resume_draft_from_profile`
- Dùng `_tap_element_safe` (thử cả method public và private của adapter, không phụ thuộc cứng `_tap_if_found`).
- Các bước:
  1. Tap vào tile "Bản nháp" / "Draft" trên Profile.
  2. Tap vào video bản nháp đầu tiên (resource-id `cover`/`thumbnail`/`video_cover` hoặc fallback quét bounds clickable `[l, t][r, b]`). Tuyệt đối không fallback bấm mù tọa độ cố định để tránh click nhầm giao diện khác.
  3. Bấm "Tiếp" / "Next" trên màn hình Editor.
  4. Xác nhận bề mặt Composer ("Đăng", "Post", "Thêm mô tả").
- Ghi nhận đầy đủ Telemetry Checkpoint: `draft_resume_attempted`, `draft_resumed`, `draft_resume_status`, `draft_resume_duration_seconds`, `draft_resume_reason`.

## 3. Pitfall Reviewer & Closeout Gate
- **Reviewer Sol Auditor (< 85 điểm) thường phạt khi:**
  1. Dùng fallback tọa độ pixel mù cứng (`adapter.tap(180, 360)`) mà không có selector hoặc fail-safe.
  2. Thiếu failure telemetry & reason code (`COMPOSER_NOT_CONFIRMED`, `DRAFT_ITEM_NOT_FOUND`).
  3. Thiếu unit test chứng minh fallback an toàn khi resume thất bại (fallthrough về upload chuẩn).
- Luôn kiểm tra `closeout_gate.py` với model review và bổ sung đủ assertions telemetry trong test suite trước khi đóng phiên.
