# Routing-policy analysis method (user-prescribed, verify 2026-08-09)

Trigger: user yêu cầu "đọc config, policy và live catalog để đề xuất workflow model tối ưu theo quota" với multi-runtime (Codex/Hermes/OpenCode/AG Claude), thường kèm `CHỈ PHÂN TÍCH` = không sửa file, không chạy live.

## Workflow bắt buộc (user quy định, 6 bước)

1. **Coordinator đọc thực tế**: config.yaml (python yaml — provider/model/fallback/reasoning/channel_overrides), AGENTS.md/HANDOFF.md của repo, và live catalog `GET /v1/models` (Bearer NINEROUTER_API_KEY).
2. **Đúng MỘT read-only planner bằng model OpenCode MẠNH** — tuyệt đối tránh DeepSeek Flash (đã làm Hermes worker). Planner KHÔNG được sửa file.
3. **Coordinator tổng hợp** phương án (không để planner tự quyết).
4. **Đúng MỘT AG Claude/high qua 9Router** (`ag/claude-opus-4-6-thinking`) vừa phản biện phương án VỪA test account-health AG (2 tài khoản Google Pro, dùng 1 trong 1 lần). Không dùng Gemini.
5. **AG lỗi → final-audit fallback**: GPT/high (1 slot) → model OpenCode/9Router KHÁC (không lặp route đã fail).
6. **Không agent nào spawn agent khác** (nested delegation cấm).

## Đầu ra (đúng 5 mục)

1. Bảng model/quota ngắn (chỉ ID có trong live catalog; không suy đoán quota con số).
2. Workflow khuyến nghị cho Codex (planner / audit thường / audit auto-recovery).
3. Workflow khuyến nghị cho Hermes (planner / audit thường / audit auto-recovery).
4. Kết quả test AG Claude qua 9Router (PASS/FAIL + lỗi nếu có).
5. Danh sách file cần sửa — CHỈ sau khi user duyệt (analyze-only ≠ quyền sửa).

## Fact verify 2026-08-09 (probe qua /v1/chat/completions)

- `opencode-free` → response `"model":"deepseek-v4-flash-free"` — combo này KHÔNG phải model mạnh riêng; không dùng làm planner khi cấm DeepSeek Flash.
- `cmc/Qwen/Qwen3.6-Max-Preview`, `cmc/zai-org/GLM-5.1` → **429 ở probe đầu** (transient/rate-limit): re-probe cách quãng, không kết luận model chết.
- `ag/claude-opus-4-6-thinking` → HTTP 200, response SSE dù request non-stream; account sống.
- **AG Claude hallucinate catalog**: phủ nhận `claude-opus-4-6-thinking`/`gpt-5.6-luna`/`deepseek-v4-flash` tồn tại và bịa `gpt-4.1`/`o3`/`deepseek-reasoner` (knowledge cũ của nó). Không để auditor phủ quyết ID từ `/v1/models` — trust live catalog; auditor chỉ dùng critique/health.
- Probe: `reasoning high` + `max_tokens:5000` → reasoning ăn hết budget (`finish_reason:"length"`, content rỗng) → `max_tokens:8000+`, timeout 300s+ hoặc background.

## Routing rules đã chốt trong phân tích này

- Retry CÙNG model: chỉ transient (timeout/5xx), tối đa 1 lần. 429/quota/auth/model-not-found/empty response → chuyển model NGAY, ghi `AUDIT_ROUTE_SWITCH` kèm lý do.
- Chống fallback loop: route đã fail trong task không bao giờ quay lại; mỗi task đúng 1 lần AG; 2 chu kỳ REJECT cùng invariant → design/impact audit, không patch chắp vá.
- Claude Pro cá nhân: CHỈ khi AG + GPT/OpenCode fallback đều chết hoặc mâu thuẫn (APPROVED vs REJECT) — đúng 1 gate quyết định, không tự bật.
- Command Code: bỏ khỏi active route; Gemini: cấm.

## Chốt v6 2026-08-09 (user duyệt sau Sol vs AG cross-exam) — ĐÃ PHỦ toàn cây D:\Taadaa

**Chuỗi chốt (đã ghi vào mọi AGENTS.md dưới D:\Taadaa):**

```text
PLANNER (read-only, 1 call):
  case thường → cx/gpt-5.6-terra/HIGH
  case khó    → cx/gpt-5.6-sol/HIGH
  fallback    → ag/claude-opus-4-6-thinking/HIGH → opencode-audit combo

AUDIT THƯỜNG:
  ag/claude-opus-4-6-thinking/HIGH  (đúng 1 AG route/account mỗi task)
  AG hết quota → cx/gpt-5.6-terra-review/HIGH (thường) | cx/gpt-5.6-sol-review/HIGH (khó)
              → opencode-audit combo
              → AUDIT_ALL_ROUTES_FAILED

AUTO-RECOVERY (AG fail giữa chừng): terra-review/sol-review → opencode-audit → AUDIT_ALL_ROUTES_FAILED
```

- **CẤM làm planner/auditor**: `gpt-5.6-luna` (worker, thiếu trình — chỉ là worker), `cmc/*` (KHÔNG có quota — user xác nhận 2026-08-09), `opencode-free`/`oc/deepseek-v4-flash-free` (resolve thành DeepSeek Flash = worker Hermes), Gemini, Command Code.
- **Combo `opencode-audit` đã tạo trong 9Router** (combos table, 2026-08-09): `oc/nemotron-3-ultra-free` → `oc/big-pickle` → `oc/longcat-2.0-free` → `oc/ling-3.0-tiny-free`. Smoke 200. Dùng model ID `opencode-audit` qua `/v1/chat/completions`.
- **Probe 2026-08-09 (catalog 475 ID)**: `cx/gpt-5.6-luna-review`, `cx/gpt-5.6-terra-review`, `gpt-5.6-luna` → ROUTE_OK. `oc/nemotron-3-ultra-free`, `oc/big-pickle`, `oc/longcat-2.0-free` → 200. `oc/north-mini-code-free`, `oc/hy3-free`, `oc/glm-5.2`, `oc/kimi-k3`, `oc/qwen3.8-max` → **401** (opencode-go KHÔNG route qua prefix `oc/`). `oc/ling-3.0-tiny-free` → 503 (transient).
- **Workers bất biến**: Hermes = `deepseek-v4-flash`/HIGH; Codex = `gpt-5.6-luna`/HIGH; worker KHÔNG gọi/spawn worker. Codex tuyệt đối không gọi DeepSeek.
- **Khác biệt runtime**: Codex audit ưu tiên AG → opencode-audit sớm (cùng pool GPT với worker, không đốt quota worker); Hermes AG → GPT review → opencode-audit.
- Config Hermes đã đổi (2026-08-09): fallback `ag/gemini-3.6-flash-high` → `opencode-audit` (Gemini bị cấm), reasoning_overrides `opencode-audit: high`.
