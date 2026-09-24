"""
Auto-updater for omni-free combo on OmniRoute (:20129).
Periodically discovers free models on OpenRouter, verifies liveness,
and updates the omni-free combo without any Gemini 3.8 models.
"""
import urllib.request
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

COMBO_ID = "5a72c9bc-94d8-4e35-a9c6-51545cb73d7a"
OMNI_BASE = "http://127.0.0.1:20129"
OR_CONN_ID = "d8e441bf-6659-49ec-a573-621535648a21"

KNOWN_PRIORITY_MODELS = [
    'openrouter/nex-agi/nex-n2.5-pro:free',
    'openrouter/liquid/lfm-2.5-2.6b:free',
    'openrouter/inclusionai/ling-3.0-flash-vl:free',
    'openrouter/dots-studio/dots-3-note-preview:free',
    'openrouter/nvidia/nemotron-3-super-120b-a12b:free-low',
    'openrouter/poolside/laguna-s-2.1:free',
    'openrouter/inclusionai/ling-3.0-flash-fin:free',
    'openrouter/inclusionai/ling-3.0-flash-sante:free'
]

def log_debug(msg: str):
    print(msg, file=sys.stderr, flush=True)

def report_error(msg: str):
    error_report = (
        f"⚡ *[OMNI-FREE] CẬP NHẬT ROUTING POOL*\n"
        f"───────────────────────────\n"
        f"• *Trạng thái:* ❌ Thất bại\n"
        f"• *Lỗi:* `{msg}`\n"
    )
    print(error_report)
    sys.exit(1)

def clean_model_name(mid: str) -> str:
    clean = mid
    for prefix in ("openrouter/", "chatgpt-web/"):
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):]
            break
    for suffix in (":free-low", ":free"):
        if clean.lower().endswith(suffix):
            clean = clean[:-len(suffix)]
            break
    return clean

def test_model_liveness(mid):
    t0 = time.time()
    req = urllib.request.Request(
        f"{OMNI_BASE}/v1/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": "Bearer any"},
        data=json.dumps({
            "model": mid,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5
        }).encode("utf-8")
    )
    try:
        with urllib.request.urlopen(req, timeout=7) as r:
            if r.status == 200:
                dt = time.time() - t0
                return (mid, dt, True)
    except Exception:
        pass
    return (mid, 999.0, False)

def run_updater():
    try:
        log_debug("[OMNI-FREE-UPDATER] 1. Fetching OpenRouter catalog...")
        candidate_models = list(KNOWN_PRIORITY_MODELS)
        seen = set(candidate_models)

        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"User-Agent": "OmniRoute-HealthCheck/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                catalog = json.loads(r.read().decode("utf-8")).get("data", [])
            for m in catalog:
                pricing = m.get("pricing", {})
                mid = m.get("id", "")
                if float(pricing.get("prompt", 1)) == 0 and float(pricing.get("completion", 1)) == 0:
                    mid_lower = mid.lower()
                    if "gemini-3.8" in mid_lower or "3.8-flash" in mid_lower:
                        continue
                    if "content-safety" in mid_lower or "moderation" in mid_lower:
                        continue
                    full_id = f"openrouter/{mid}"
                    if full_id not in seen:
                        candidate_models.append(full_id)
                        seen.add(full_id)
        except Exception as e:
            log_debug(f"[OMNI-FREE-UPDATER] Catalog fetch warning: {e}. Using known priority models.")

        log_debug(f"[OMNI-FREE-UPDATER] Candidate pool size: {len(candidate_models)}. Testing liveness (max_workers=2, target: 4-5 live models)...")
        live_results = []
        
        target_live = 5
        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_to_mid = {}
            cand_iter = iter(candidate_models)
            
            for _ in range(2):
                try:
                    m = next(cand_iter)
                    fut_to_mid[executor.submit(test_model_liveness, m)] = m
                except StopIteration:
                    break

            while fut_to_mid:
                for fut in list(fut_to_mid.keys()):
                    if fut.done():
                        mid, latency, ok = fut.result()
                        del fut_to_mid[fut]
                        if ok:
                            live_results.append((mid, latency))
                            log_debug(f"  + LIVE: {mid} ({latency:.2f}s)")
                            if len(live_results) >= target_live:
                                break
                        if len(live_results) < target_live:
                            try:
                                next_m = next(cand_iter)
                                fut_to_mid[executor.submit(test_model_liveness, next_m)] = next_m
                            except StopIteration:
                                pass
                if len(live_results) >= target_live:
                    break
                time.sleep(0.1)

        # Sort by latency ascending
        live_results.sort(key=lambda x: x[1])
        top_models = live_results[:8]

        combo_models = []
        for idx, (mid, lat) in enumerate(top_models, 1):
            short_name = mid.split('/')[-1]
            combo_models.append({
                "id": f"omni-free-step-{idx}-{short_name[:30]}",
                "kind": "model",
                "model": mid,
                "providerId": "openrouter",
                "connectionId": OR_CONN_ID,
                "weight": 0,
                "label": f"Tier {idx}: {short_name} ({lat:.1f}s)"
            })

        # Always append ChatGPT Web free tiers as rock-solid fallbacks
        idx = len(combo_models) + 1
        combo_models.append({
            "id": f"omni-free-step-{idx}-luna-free",
            "kind": "model",
            "model": "chatgpt-web/gpt-5.6-luna-free",
            "providerId": "chatgpt-web",
            "weight": 0,
            "label": f"Tier {idx}: GPT-5.6 Luna Free (ChatGPT Web Pool)"
        })
        idx += 1
        combo_models.append({
            "id": f"omni-free-step-{idx}-sol-instant",
            "kind": "model",
            "model": "chatgpt-web/gpt-5.6-sol-instant",
            "providerId": "chatgpt-web",
            "weight": 0,
            "label": f"Tier {idx}: GPT-5.6 Sol Instant (ChatGPT Web Pool)"
        })

        payload = {
            "description": f"Pure Free Pool: {len(top_models)} OpenRouter Free + 2 ChatGPT Web Free (Auto-Updated)",
            "strategy": "priority",
            "config": {
                "maxRetries": 1,
                "retryDelayMs": 100,
                "targetTimeoutMs": 25000,
                "queueTimeoutMs": 1000,
                "stickyRoundRobinLimit": 1,
                "disableSessionStickiness": True,
                "maxGlobalAttempts": 8,
                "nestedComboMode": "execute",
                "failoverBeforeRetry": True
            },
            "models": combo_models
        }

        log_debug(f"[OMNI-FREE-UPDATER] Updating combo omni-free with {len(combo_models)} tiers...")
        req_patch = urllib.request.Request(
            f"{OMNI_BASE}/api/combos/{COMBO_ID}",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload).encode("utf-8"),
            method="PATCH"
        )
        try:
            with urllib.request.urlopen(req_patch, timeout=10) as r:
                if r.status != 200:
                    log_debug(f"[OMNI-FREE-UPDATER] PATCH failed: HTTP {r.status}")
                    report_error(f"PATCH combo failed: HTTP {r.status}")
        except Exception as e:
            log_debug(f"[OMNI-FREE-UPDATER] PATCH error: {e}")
            report_error(f"PATCH combo failed: {e}")

        # Verification ping with max_tokens=5 (non-blocking)
        log_debug("[OMNI-FREE-UPDATER] Running verification ping...")
        req_verify = urllib.request.Request(
            f"{OMNI_BASE}/v1/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": "Bearer any"},
            data=json.dumps({
                "model": "omni-free",
                "messages": [{"role": "user", "content": "ping verification"}],
                "max_tokens": 5
            }).encode("utf-8")
        )
        try:
            with urllib.request.urlopen(req_verify, timeout=10) as r:
                res = json.loads(r.read().decode("utf-8"))
                model_used = res.get("model", "unknown")
                log_debug(f"[OMNI-FREE-UPDATER] Verification ping success (served by: {model_used})")
        except Exception as e:
            log_debug(f"[OMNI-FREE-UPDATER] Verification warning: {e}")

        # Telegram Markdown Report to stdout
        total_tiers = len(combo_models)
        if top_models:
            top_model_short = clean_model_name(top_models[0][0])
            top_lat_info = f"⚡ {top_models[0][1]:.2f}s"
        else:
            top_model_short = clean_model_name(combo_models[0]["model"])
            top_lat_info = "Web Fallback"

        route_lines = []
        for r_idx, (mid, lat) in enumerate(top_models, 1):
            cname = clean_model_name(mid)
            if r_idx == 1:
                icon = "🥇"
            elif r_idx == 2:
                icon = "🥈"
            elif r_idx == 3:
                icon = "🥉"
            else:
                icon = "🔹"
            route_lines.append(f"{r_idx}. {icon} `{cname}` ({lat:.2f}s)")

        web_start = len(top_models) + 1
        web_fallbacks = [
            "GPT-5.6 Luna Free (ChatGPT Web Pool)",
            "GPT-5.6 Sol Instant (ChatGPT Web Pool)"
        ]
        for offset, w_name in enumerate(web_fallbacks):
            curr_idx = web_start + offset
            route_lines.append(f"{curr_idx}. 🌐 `{w_name}`")

        routing_str = "\n".join(route_lines)

        report = (
            f"⚡ *[OMNI-FREE] CẬP NHẬT POOL THÀNH CÔNG*\n"
            f"───────────────────────────\n"
            f"• *Trạng thái:* ✅ Hoạt động\n"
            f"• *Tổng tiers:* {total_tiers} models ({len(top_models)} OpenRouter + 2 ChatGPT Web)\n"
            f"• *Top Model:* `{top_model_short}` ({top_lat_info})\n"
            f"• *Endpoint:* `omni-free` (:20129)\n\n"
            f"📋 *Thứ tự ưu tiên (Priority Tiers):*\n"
            f"{routing_str}"
        )
        print(report)

    except Exception as e:
        log_debug(f"[OMNI-FREE-UPDATER] Unhandled exception: {e}")
        report_error(f"Unexpected error: {e}")

if __name__ == "__main__":
    run_updater()
