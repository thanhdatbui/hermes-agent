# OpenCode CLI Model ID Specification & Fallback Routing Invariant

## 1. Bối cảnh & Hiện tượng
Khi Gemini cạn quota và hệ thống Hermes kích hoạt chuỗi fallback sang OpenCode (`custom:opencode` qua bridge `opencode_bridge.py` và runner `oc_farm.py`), xảy ra 2 hiện tượng lỗi:
1. **Model Vision Failure:** Người dùng gửi ảnh screenshot hiện trường qua Telegram, OpenCode trả lời "không thấy ảnh" hoặc request bị kẹt timeout 120s.
2. **Proxy Báo Lỗi Giả (False Proxy Blame):** `oc_farm.py` liên tục báo:
   ```text
   oc_farm: attempt 1/5 via mikrotik-1
   Error: {
     "name": "UnknownError",
     "data": {
       "message": "Unexpected server error. Check server logs for details.",
       "ref": "err_..."
     }
   }
   ```
   Dẫn đến việc `oc_farm.py` tưởng proxy chết, chuyển sang cooldown proxy và xoay vòng proxy vô ích.

---

## 2. Nguyên nhân kỹ thuật gốc rễ (Root Cause)

### A. Định danh Model trên OpenCode CLI (Model ID Fully-Qualified Invariant)
* **Bắt buộc full slug:** Khi gọi CLI `opencode run --model <model_id>`, máy chủ OpenCode yêu cầu chính xác tên định danh đầy đủ:
  - **ĐÚNG:** `opencode/muse-spark-1.3-contributor-free`
  - **SAI:** `muse-spark-1.3` (Máy chủ trả về `UnknownError: Unexpected server error`, ref: `err_...`).
* **Cơ chế Mapping tại Bridge:** File `opencode_bridge.py` nhận request từ client dưới dạng model alias (như `muse-spark-1.3`), BẮT BUỘC phải lookup qua bảng mapping chuẩn sang `opencode/<model>-contributor-free` trước khi truyền vào `oc_farm.py` hoặc `opencode run`.

### B. Bản chất Text-Only của cụm OpenCode Free Models
* Toàn bộ 8 model free của OpenCode (`muse-spark-1.3`, `nemotron-3-ultra`, `nemotron-3.5-lightning`, `mimo-v2.6-flash`, `ling-3.0-flash-fin`, `longcat-2.5-preview`, `big-pickle`, `space-bunny`) đều là **Text-Only LLM**.
* OpenCode CLI không nhận tham số ảnh trên command line. Hơn nữa, Muse Spark có prompt guardrail cứng từ chối ngay lập tức khi phát hiện câu hỏi chứa từ khóa "màn hình", "hình ảnh", "screenshot".

---

## 3. Quy tắc Vận hành & Cấu hình Bắt buộc

1. **Hierarchy Fallback Hermes (Bắt buộc có Vision trước OpenCode):**
   Trong `~/.hermes/config.yaml`, chuỗi `fallback_providers` BẮT BUỘC phải đặt model có Vision (như `cx/gpt-5.6-luna-high` trên OmniRoute `:20129`) đứng trước OpenCode:
   ```yaml
   fallback_providers:
     - model: cx/gpt-5.6-luna-high
       provider: custom:omni
     - model: muse-spark-1.3
       provider: custom:opencode
   ```
   *Không bao giờ để OpenCode làm fallback trực tiếp duy nhất sau Gemini.*

2. **Chẩn đoán Lỗi OpenCode CLI vs Proxy:**
   Khi thấy `oc_farm.py` văng `UnknownError: Unexpected server error`:
   - Bước 1: Test chạy trực tiếp không qua proxy: `opencode run --model opencode/muse-spark-1.3-contributor-free "1+1=?"`.
   - Bước 2: Nếu lệnh trực tiếp trả về `2`, nguyên nhân là do tên model truyền vào thiếu namespace `opencode/` hoặc tham số sai, CẤM vội kết luận proxy farm MikroTik/Mobi bị lỗi.
