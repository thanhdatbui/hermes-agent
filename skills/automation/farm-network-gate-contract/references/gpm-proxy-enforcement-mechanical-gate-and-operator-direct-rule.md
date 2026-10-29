# GPM Proxy Enforcement Mechanical Gate Implementation & Review Audit

## 1. Context & Incident
- **Root Incident:** When executing ad-hoc automation / account registration (e.g., AWS Free Tier / ChatGPT signup), Coordinator attempted to create new GPM profiles without proxy (`raw_proxy=""`) or considered using host machine direct IP (Kibe host), risking chain bans across farm account clusters.
- **Operator Mandate:** "CƠ GIỚI HOÁ" (Mechanical enforcement). Prompts, guidelines, and memory alone fail under pressure; an automated, fail-closed pre-tool hook is strictly mandatory.
- **Direct IP Exception Agreement:** Operator explicitly noted: "vẫn có profile tao muốn để IP direct mà (mấy gmail chính của tao)". Following Claude Opus review, **Approach A** was finalized:
  - **Agent:** 100% blocked from creating GPM profiles without a proxy. No bypass magic strings or flags.
  - **Operator:** Manually creates direct-IP profiles on the GPM desktop GUI if needed for primary personal accounts.
  - **Start/Run:** Hook NEVER blocks `/api/v3/profiles/start/{id}` or profile listing, so legitimate direct-IP profiles already in the fleet run unimpeded.

## 2. Gate Architecture (`guard_gpm_proxy.py`)
- **Location:** `D:/Taadaa/tools/guard_gpm_proxy.py`
- **Hook Hookup:** Registered in `D:/Taadaa/Hermes/deploy/hermes-home/config.yaml` under `pre_tool_call` for `terminal|execute_code`.
- **Latency & Footprint:** Synchronous, in-process stdlib only (`re`, `json`, `sys`, `ipaddress`). Zero outbound network requests in hook evaluation. Hook runs in < 5ms.
- **Fail-Closed Mechanics:**
  1. **Strict Path Suffix:** `CREATE_RE = re.compile(r'/profiles/create(?![\w-])', re.IGNORECASE)` captures base URL concatenations (e.g. `f"{GPM_API}/profiles/create"`).
  2. **Format Allowlist:** Rejects variable substitutions (`$`, `%`, `{`, `}`), keywords (`direct`, `none`, `null`), and loopbacks (`localhost`, `127.0.0.1`, `0.0.0.0`, `::1`). Validates `host:port[:u:p]` or `scheme://` with 1 <= port <= 65535.
  3. **Body Count vs Call Count:** Compares `len(create_matches)` against top-level profile-bearing JSON bodies (`extract_json_objects_by_form`). Compound commands (`&&`, `;`) or inline + file mixes (e.g. `create inline && create -d @file.json`) are blocked if bodies < create occurrences.
  4. **Batch Profile Completeness:** Recursively scans JSON trees; if ANY object with `profile_name` lacks a valid `raw_proxy`, the entire batch is rejected.
  5. **Windows UTF-8 Pipe Guard:** Explicitly handles console codepage quirks with `sys.stdout.reconfigure(encoding="utf-8")` and ASCII fallback to prevent `UnicodeEncodeError` in pre-tool execution pipes.

## 3. Verification Suite (`test_guard_gpm_proxy.py`)
- **Suite Size:** 129 offline mocked test cases (`D:/Taadaa/tools/tests/test_guard_gpm_proxy.py`).
- **Review History:** Iteratively audited through 6 rounds with Claude Opus CLI until reaching unconditional `VERDICT: APPROVED`.
