import json, math, os, re, time, uuid, urllib.error, urllib.request
from urllib.parse import urlparse
from tools.registry import registry

ADVISOR_ENDPOINT = os.getenv("HERMES_ADVISOR_ENDPOINT", "http://127.0.0.1:20129/v1/chat/completions")
ADVISOR_MODEL = "review"
MAX_RAW_ADVICE = 12000
DEFAULT_TIMEOUT = 15
MAX_PAYLOAD_BYTES = 16000
_SECRET_KEYS = {"password", "apikey", "accesstoken", "refreshtoken", "sessiontoken", "cookie", "authorization", "authheader", "secret", "token", "privatekey", "clientsecret"}
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_PAIR_RE = re.compile(r"(?i)\b(?:password|api[_-]?key|access[_-]?token|refresh[_-]?token|session[_-]?token|cookie|authorization|auth[_-]?header|secret|token|private[_-]?key|client[_-]?secret)(?P<separator>\s*[=:]\s*)[^\s,;]+")
_QUOTED_PAIR_RE = re.compile(r"(?i)([\"']?)(?:password|api[_-]?key|access[_-]?token|refresh[_-]?token|session[_-]?token|private[_-]?key|client[_-]?secret)\1\s*:\s*([\"']?)[^\"'\s,;}]+\2")
_COMMON_TOKEN_RE = re.compile(r"(?i)\b(?:sk|ghp|xox)-[A-Za-z0-9][A-Za-z0-9_-]*")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}(?:\.[A-Za-z0-9_-]+){2}\b")


def _redact(v):
    if isinstance(v, dict):
        return {k: "[REDACTED]" if re.sub(r"[-_]", "", str(k).lower()) in _SECRET_KEYS else _redact(item) for k, item in v.items()}
    if isinstance(v, list):
        return [_redact(x) for x in v]
    if isinstance(v, str):
        v = _BEARER_RE.sub("Bearer [REDACTED]", v)
        v = _PAIR_RE.sub(lambda m: m.group(0)[: m.start("separator") - m.start()] + m.group("separator") + "[REDACTED]", v)
        v = _QUOTED_PAIR_RE.sub("[REDACTED]", v)
        v = re.sub(r'(?i)(["\']?)(?:apikey|api[_-]?key|private[_-]?key|client[_-]?secret)\1\s*:\s*(["\'])(.*?)\2', r"\1[REDACTED]\1", v)
        v = _COMMON_TOKEN_RE.sub("[REDACTED]", v)
        return _JWT_RE.sub("[REDACTED]", v)
    return v


def _request_payload(cls, q, state, evid, acts, constr, rid):
    env = {"decision_class": _redact(cls), "question": _redact(q), "current_state": _redact(state), "evidence": _redact(evid), "candidate_actions": _redact(acts), "constraints": _redact(constr), "request_id": rid}
    payload = {"model": ADVISOR_MODEL, "messages": [{"role": "system", "content": "You are a read-only planner/advisor. Do not use tools, cause side effects, or approve actions. Return JSON when possible."}, {"role": "user", "content": json.dumps(env, ensure_ascii=False)}], "tools": [], "tool_choice": "none", "stream": False, "max_tokens": 1200}

    def shrink(v):
        if isinstance(v, str): return v[: len(v) // 2] if len(v) > 1 else ""
        if isinstance(v, list): return v[: len(v) // 2] if len(v) > 1 else ([shrink(v[0])] if v else [])
        if isinstance(v, dict): return dict(list(v.items())[: len(v) // 2]) if len(v) > 1 else ({next(iter(v)): shrink(v[next(iter(v))])} if v else {})
        return None

    def sz(val):
        try: return len(json.dumps(val, ensure_ascii=False).encode("utf-8"))
        except (TypeError, ValueError): return None

    while True:
        s = sz(payload)
        if s is None: return None
        if s <= MAX_PAYLOAD_BYTES: return payload
        cands = [(sz(v), k, v) for k, v in env.items() if sz(v)]
        if not cands: return None
        _, k, v = max(cands)
        red = shrink(v)
        if red is None or red == v: return None
        env[k] = red
        payload["messages"][1]["content"] = json.dumps(env, ensure_ascii=False)


def _first_json_object(c):
    if not isinstance(c, str): return None
    t = c.strip()
    if t.startswith("```json"): t = t[7:]
    elif t.startswith("```"): t = t[3:]
    if t.endswith("```"): t = t[:-3]
    t = t.strip()
    dec = json.JSONDecoder()
    for idx, ch in enumerate(t):
        if ch != "{": continue
        try:
            val, _ = dec.raw_decode(t[idx:])
            if isinstance(val, dict): return val
        except json.JSONDecodeError: pass
    return None


def _loopback_endpoint(ep):
    try:
        p = urlparse(ep)
        return p.scheme in {"http", "https"} and p.hostname in {"localhost", "127.0.0.1", "::1"}
    except (TypeError, ValueError):
        return False


class _LoopbackRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _loopback_endpoint(newurl):
            raise urllib.error.HTTPError(req.full_url, code, "Advisor redirect target is not loopback", headers, None)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_ADVISOR_OPENER = urllib.request.build_opener(_LoopbackRedirectHandler())


def _telemetry(rid, lat_ms, ep=ADVISOR_ENDPOINT):
    return {"request_id": rid, "model": ADVISOR_MODEL, "endpoint": ep, "latency_ms": lat_ms}


def advisor_consult(decision_class, question, current_state=None, evidence=None, candidate_actions=None, constraints=None, request_id=None, timeout=DEFAULT_TIMEOUT):
    rid, t0, ep = request_id or str(uuid.uuid4()), time.monotonic(), os.getenv("HERMES_ADVISOR_ENDPOINT", ADVISOR_ENDPOINT)
    def _unavail(err): return {"status": "unavailable", "advice": None, "raw_advice": "", "error": str(err), "telemetry": _telemetry(rid, int((time.monotonic() - t0) * 1000), ep)}
    if not _loopback_endpoint(ep): return _unavail("Endpoint not loopback")
    try:
        b_to = min(max(float(timeout), 0.0), DEFAULT_TIMEOUT)
        if not math.isfinite(b_to): raise ValueError("timeout must be finite")
    except (TypeError, ValueError, OverflowError) as exc: return _unavail(f"Invalid timeout: {exc}")
    try:
        payload = _request_payload(decision_class, question, current_state, evidence, candidate_actions, constraints, rid)
        if payload is None: raise ValueError("payload exceeds maximum size or is not serializable")
        req_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(req_body) > MAX_PAYLOAD_BYTES: raise ValueError("payload exceeds maximum size")
        req = urllib.request.Request(ep, data=req_body, headers={"Content-Type": "application/json"}, method="POST")
    except (TypeError, ValueError) as exc: return _unavail(exc)
    try:
        with _ADVISOR_OPENER.open(req, timeout=b_to) as resp:
            body = resp.read()
        dec = json.loads(body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else body)
        choices = dec.get("choices") if isinstance(dec, dict) else None
        msg = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
        cnt = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(cnt, str) or not cnt.strip(): raise ValueError("empty response content")
        advice = _first_json_object(cnt)
        if not isinstance(advice, dict): raise ValueError("response content did not contain a JSON object")
        lat = int((time.monotonic() - t0) * 1000)
        res = {"status": "ok", "advice": advice, "raw_advice": cnt[:MAX_RAW_ADVICE], "telemetry": _telemetry(rid, lat, ep)}
        return res
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        res = {"status": "unavailable", "advice": None, "raw_advice": "", "error_type": type(exc).__name__, "error": str(exc)}
    except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError) as exc:
        res = {"status": "error", "advice": None, "raw_advice": "", "error_type": type(exc).__name__, "error": str(exc)}
    res["telemetry"] = _telemetry(rid, int((time.monotonic() - t0) * 1000), ep)
    return res


registry.register(
    name="advisor_consult",
    toolset="advisor",
    schema={"type": "object", "properties": {"decision_class": {"type": "string"}, "question": {"type": "string"}, "current_state": {}, "evidence": {}, "candidate_actions": {}, "constraints": {}, "request_id": {"type": "string"}, "timeout": {"type": "number"}}, "required": ["decision_class", "question"]},
    handler=lambda args, **kw: json.dumps(advisor_consult(**args), ensure_ascii=False),
    check_fn=lambda: False,
    description="Consult the read-only Dynamic Advisor for planning guidance; never approves or executes actions.",
)
