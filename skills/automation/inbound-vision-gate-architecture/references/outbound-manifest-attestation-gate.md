# Quy Trình Outbound Manifest Attestation & Khóa Mõm Ảo Giác Avatar (2026-11-03)

## 1. Bản Chất Sự Cố Outbound (The Outbound Hallucination Trap)
- **Triệu chứng:** Bot cắt một frame từ video (vd: `25.mp4`), lưu ra file `avatar.jpg`. Nhưng khi trả lời người dùng, bot KHÔNG nhìn lại ảnh vừa cắt mà tự động lấy kịch bản từ file Excel cũ (`Tik5.xlsx` ghi nhầm nhãn `Thú cưng / Chó cưng`) để tuôn ra văn mẫu: *"Khuôn mặt chú cún lông nâu nằm chính giữa tâm hình..."*.
- **Hậu quả:** File ảnh gửi đi là cảnh diễn viên người thật trong phim ngắn đường phố, nhưng text bot lại mô tả là cún cưng $\rightarrow$ Dối trá, ảo giác, khiến người dùng ức chế chửi bới.

---

## 2. Thiết Kế Cơ Giới Hoá Đã Thi Công (Commit `7df1c2a` trên repo `tools`)

### A. Cơ Chế Pre-flight Manifest Sinh Kèm Ảnh
- Khi cắt/gia công avatar xong, bắt buộc ghi file `.avatar_manifest.json` nằm cạnh file ảnh:
```json
{
  "attested_subject": "A muscular man confronting an elderly woman at a street food cart",
  "entity_type": "human",
  "clip": "25.mp4"
}
```

### B. Chốt Chặn Cơ Học Trong `guard_media_vision_gate.py` (`check_contradiction`)
- Khi bot gửi thẻ `MEDIA:<path_to_avatar>`, Gate tự động đọc file manifest trong **2ms**:
  1. Nếu manifest xác nhận `entity_type: human` mà tin nhắn chứa từ khóa chó/cún/mèo (`cun`, `cho`, `dog`, `puppy`, `cat`...) $\rightarrow$ **Gate trả về `ENTITY_MISMATCH`, passed=False, CHẶN ĐỨNG TIN NHẮN TỨC THÌ!**
  2. Ngược lại, nếu manifest ghi `dog` mà tin nhắn bot lại khẳng định `người` $\rightarrow$ Gate cũng trả về `ENTITY_MISMATCH` và chặn họng.
- **Fail-safe O(1):**
  - Chạy chỉ mất **2ms**, không gọi network, không gọi LLM suy luận thêm.
  - Được bọc `try...except`, nếu ảnh thường không có manifest thì Gate bỏ qua và cho pass bình thường, không gây false-blocking hay bại liệt.
  - Được bảo vệ bởi unit test: `test_manifest_contradiction_blocks` (102/102 tests passed).

---

## 3. Quy Tắc Bắt Buộc Cho Coordinator
1. **Video Thật Là Chân Lý (Ground Truth):** CẤM TUYỆT ĐỐI tin vào cột Keyword/Niche trong Excel khi chưa chạy `vision_analyze_tool` soi trực tiếp frame video trong kho gốc.
2. **Attestation Trước Khi Emit Response:** Cắt xong ảnh BẮT BUỘC sinh manifest và đọc manifest để neo câu trả lời, tuyệt đối không được dùng kịch bản trong đầu để bịa đặt.
