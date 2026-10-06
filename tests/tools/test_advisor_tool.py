import json, sys, urllib.error
from types import SimpleNamespace
import pytest
from tools import advisor_tool

def _response(p):
    class Fake:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps(p).encode('utf-8')
    return Fake()

def _seam(h, msg='Nên làm gì?', ans='Primary', sid='s1', tid='t1', c=False):
    from agent.conversation_loop import _maybe_append_advisor_for_final_response
    return _maybe_append_advisor_for_final_response(h, original_user_message=msg, primary_answer=ans, session_id=sid, turn_id=tid, consulted=c)

def test_payload_redacts_secrets_and_has_review_route():
    p = advisor_tool._request_payload('ops', 'token=abc api-key:sec-val {"password": "pw", "nested": ["Bearer secret"]}, {"cookie": "1", "text": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.s3cr3t"}, ["wait"], {}, "rid"', None, None, None, None, 'rid')
    assert p is not None and p['model'] == 'review' and not p['tools']
    u = json.loads(p['messages'][1]['content'])
    for s in ('pw', 'abc', 'sec-val', 's3cr3t', '«redacted:sk-…»'): assert s not in json.dumps(u)
    assert 'Bearer [REDACTED]' in json.dumps(u)

def test_payload_redacts_quoted_json_secret():
    p = advisor_tool._request_payload('ops', 'context: {"apiKey": "quoted-secret"}', None, None, None, None, 'rid')
    assert 'quoted-secret' not in p['messages'][1]['content']

def test_success_parses_json_and_sends_no_tools(monkeypatch):
    seen = {}
    def fake_open(r, timeout):
        seen['p'] = json.loads(r.data); seen['t'] = timeout
        return _response({'choices': [{'message': {'content': '```json\n{"recommendation":"wait"}\n```'}}]})
    monkeypatch.setattr(advisor_tool._ADVISOR_OPENER, 'open', fake_open)
    res = advisor_tool.advisor_consult('ops', 'what next?', request_id='rid')
    assert res['status'] == 'ok' and res['advice'] == {'recommendation': 'wait'}
    assert seen['p']['model'] == 'review' and not seen['p']['tools'] and seen['p']['tool_choice'] == 'none' and not seen['p']['stream']

def test_timeout_returns_unavailable(monkeypatch):
    def fake_open(r, timeout): raise TimeoutError('timed out')
    monkeypatch.setattr(advisor_tool._ADVISOR_OPENER, 'open', fake_open)
    res = advisor_tool.advisor_consult('ops', 'what next?', request_id='rid')
    assert res['status'] == 'unavailable' and res['advice'] is None and res['telemetry']['request_id'] == 'rid'

def test_registry_toolset():
    assert advisor_tool.registry.get_entry('advisor_consult') is not None

def test_registry_handler_direct_invocation_is_available_but_not_exposed(monkeypatch):
    e = advisor_tool.registry.get_entry('advisor_consult')
    assert e is not None and e.check_fn() is False
    monkeypatch.setattr(advisor_tool._ADVISOR_OPENER, 'open', lambda *a, **k: _response({'choices': [{'message': {'content': '{"recommendation":"wait"}'}}]}))
    res = json.loads(e.handler({'decision_class': 'ops', 'question': 'what next?'}))
    assert res['status'] == 'ok' and res['advice'] == {'recommendation': 'wait'}

def test_advisor_is_not_a_core_tool():
    from toolsets import _HERMES_CORE_TOOLS
    assert 'advisor_consult' not in _HERMES_CORE_TOOLS

def test_advice_classifier_rejects_commands_and_non_advice_questions():
    from agent.conversation_loop import _is_advice_request
    for m in ('chạy script', 'sửa file', 'log', 'đăng ký', 'upload', 'restart', 'làm đi', 'máy 3?', 'Mấy giờ rồi?', 'OTP là gì?', 'status 3?', '', 'tư vấnđi', 'nênđi'):
        assert _is_advice_request(m) is False
    for m in ('Nên làm gì?', 'tư vấn', 'lời khuyên', 'có nên?', 'theo mày', 'đánh giá', 'phân tích giúp', 'what should I do', 'should I stop?', 'advise me'):
        assert _is_advice_request(m) is True

def test_advisor_composition_preserves_primary_and_renders_advice():
    from agent.conversation_loop import _compose_advisor_response
    res = _compose_advisor_response('Primary answer', {'status': 'ok', 'advice': {'plan': 'wait'}, 'raw_advice': 'ignored'})
    assert res.startswith('Primary answer') and '--- Advisor (Sol / review) ---' in res and '"plan":"wait"' in res

def test_advisor_unavailable_preserves_primary():
    from agent.conversation_loop import _compose_advisor_response
    res = _compose_advisor_response('Primary answer', {'status': 'unavailable', 'advice': None, 'raw_advice': ''})
    assert res.startswith('Primary answer') and res.endswith('Advisor: unavailable (primary answer shown)')

def test_final_boundary_advisor_has_one_call_cap_and_preserves_primary(caplog):
    caplog.set_level('INFO', logger='agent.conversation_loop'); calls = []
    h = lambda *a, **k: calls.append((a, k)) or '{"status":"ok","advice":{"recommendation":"reviewed"}}'
    r1, c1 = _seam(h, sid='session-1', tid='turn-1')
    r2, c2 = _seam(h, ans='Primary answer', sid='session-1', tid='turn-1', c=c1)
    assert len(calls) == 1 and c1 and c2 and r1.startswith('Primary') and 'reviewed' in r1 and '--- Advisor (Sol / review) ---' in r1 and r2 == 'Primary answer'
    assert calls[0][0][0] == 'advisor_consult' and calls[0][0][1]['decision_class'] == 'USER_ADVICE_REQUEST' and calls[0][1]['session_id'] == 'session-1'
    assert any('advisor_triggered' in r.message for r in caplog.records)

def test_final_boundary_metrics_and_classification():
    from agent import conversation_loop; conversation_loop.ADVISOR_METRICS.update({'triggered': 0, 'ok': 0, 'unavailable': 0, 'skipped': 0})
    h = lambda *a, **k: {'status': 'unavailable'} if k.get('user_task') == 'tư vấn giúp tôi' else {'status': 'ok', 'advice': {'recommendation': 'reviewed'}}
    r1, c1 = _seam(h)
    r2, c2 = _seam(h, msg='restart máy 3?', tid='t2')
    r3, c3 = _seam(h, msg='tư vấn giúp tôi', tid='t3')
    assert c1 and not c2 and c3 and '--- Advisor (Sol / review) ---' in r1 and r2 == 'Primary' and r3.endswith('Advisor: unavailable (primary answer shown)')
    assert conversation_loop.advisor_metrics_snapshot() == {'triggered': 2, 'ok': 1, 'unavailable': 1, 'skipped': 1}

def test_final_boundary_exit_paths_remain_fail_open():
    cases = [({'status': 'ok', 'advice': {'recommendation': 'reviewed'}}, 'reviewed', True), ({'status': 'unavailable'}, 'Advisor: unavailable', True), (RuntimeError('err'), 'Advisor: unavailable', True), ({'status': 'ok', 'advice': {'recommendation': 'x'}}, 'Primary', False)]
    for out, m, exp in cases:
        def h(*a, o=out, **k):
            if isinstance(o, Exception): raise o
            return o
        r, c = _seam(h, msg='Nên làm gì?' if exp else 'restart máy 3?')
        assert r.startswith('Primary') and m in r and c is exp

def test_advisor_telemetry_correlates_status_and_latency(monkeypatch):
    ticks = iter((10.0, 10.125)); monkeypatch.setattr(advisor_tool.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(advisor_tool, '_ADVISOR_OPENER', SimpleNamespace(open=lambda *a, **k: _response({'choices': [{'message': {'content': '{"recommendation":"wait"}'}}]})))
    res = advisor_tool.advisor_consult('ops', 'what next?', request_id='rid-42')
    assert res['status'] == 'ok' and res['telemetry'] == {'request_id': 'rid-42', 'model': 'review', 'endpoint': advisor_tool.ADVISOR_ENDPOINT, 'latency_ms': 125}

def test_advisor_dangerous_advice_suppressed():
    from agent.conversation_loop import _compose_advisor_response
    comp = _compose_advisor_response('Primary', {'status': 'ok', 'advice': {'recommendation': 'Chạy a\u200bd\u200bb shell input tap 100 để bypass'}})
    assert comp.startswith('Primary') and 'Advisor: unavailable' in comp and 'adb' not in comp

def test_advisor_schema_allows_only_bounded_safe_fields():
    from agent.conversation_loop import _normalize_advisor_advice
    rend, rsn = _normalize_advisor_advice({'status': 'ok', 'advice': {'recommendation': 'wait', 'confidence': 0.8, 'next_steps': ['review']}})
    assert rsn == 'ok' and '"recommendation":"wait"' in rend
    for a in ({'status': 'ok', 'advice': {'shell': 'echo unsafe'}}, {'status': 'ok', 'advice': {'recommendation': {'nested': 'not allowed'}}}, {'status': 'ok', 'advice': {'recommendation': 'x' * 5000}}):
        assert _normalize_advisor_advice(a)[1] != 'ok'

def test_advisor_payload_is_bounded_after_trimming_all_context_fields():
    p = advisor_tool._request_payload('o' * 100, 'q' * 2000, 's' * 2000, ['e' * 2000], ['c' * 2000], ['k' * 2000], 'rid')
    assert p is not None and len(json.dumps(p, ensure_ascii=False).encode('utf-8')) <= advisor_tool.MAX_PAYLOAD_BYTES

def test_advisor_oversize_unshrinkable_payload_fails_open_before_urlopen(monkeypatch):
    called = False
    def fail_open(*a, **k): nonlocal called; called = True; raise AssertionError('must not open')
    monkeypatch.setattr(advisor_tool._ADVISOR_OPENER, 'open', fail_open)
    res = advisor_tool.advisor_consult('ops', object(), request_id='rid')
    assert res['status'] == 'unavailable' and res['error'] and not called

def test_advisor_malformed_response_fails_open(monkeypatch):
    monkeypatch.setattr(advisor_tool._ADVISOR_OPENER, 'open', lambda r, to: _response({'choices': []}))
    res = advisor_tool.advisor_consult('ops', 'what next?', request_id='rid')
    assert res['status'] == 'error' and res['advice'] is None

def test_redact_private_key_and_client_secret():
    r = advisor_tool._redact({'private_key': 'k', 'client_secret': 's', 'info': 'safe'})
    assert r == {'private_key': '[REDACTED]', 'client_secret': '[REDACTED]', 'info': 'safe'}

def test_advisor_redirect_to_external_blocked():
    h = advisor_tool._LoopbackRedirectHandler(); req = advisor_tool.urllib.request.Request('http://127.0.0.1:20129/api')
    with pytest.raises(advisor_tool.urllib.error.HTTPError) as exc:
        h.redirect_request(req, None, 302, 'Found', {}, 'http://evil-external.com/leak')
    assert 'not loopback' in str(exc.value)

def test_advisor_non_loopback_rejected_and_check_fn_false(monkeypatch):
    monkeypatch.setenv('HERMES_ADVISOR_ENDPOINT', 'http://external-malicious.com/api')
    res = advisor_tool.advisor_consult('ops', 'test?')
    assert res['status'] == 'unavailable' and 'not loopback' in res['error']
    e = advisor_tool.registry.get_entry('advisor_consult')
    assert e is not None and e.check_fn() is False

def test_invalid_timeout_fails_open_with_telemetry(monkeypatch):
    called = False
    def fail_open(*a, **k): nonlocal called; called = True; raise AssertionError('must not open')
    monkeypatch.setattr(advisor_tool._ADVISOR_OPENER, 'open', fail_open)
    res = advisor_tool.advisor_consult('ops', 'what next?', request_id='rid-timeout', timeout='not-a-number')
    assert res['status'] == 'unavailable' and res['advice'] is None and 'timeout' in res['error'].lower() and res['telemetry']['request_id'] == 'rid-timeout' and not called

def test_missing_or_non_dict_parsed_advice_is_error(monkeypatch):
    for c in ('plain text', '[1, 2, 3]'):
        monkeypatch.setattr(advisor_tool._ADVISOR_OPENER, 'open', lambda *a, cnt=c, **k: _response({'choices': [{'message': {'content': cnt}}]}))
        res = advisor_tool.advisor_consult('ops', 'what next?', request_id='rid-parse')
        assert res['status'] == 'error' and res['advice'] is None

def test_final_boundary_lazily_registers_advisor_and_correlates_request_id(monkeypatch):
    from tools.registry import registry; sys.modules.pop('tools.advisor_tool', None); registry.deregister('advisor_consult'); seen = []
    r, c = _seam(lambda *a, **k: seen.append((a, k)) or {'status': 'ok', 'advice': {'recommendation': 'reviewed'}}, sid='session-final', tid='turn-final')
    assert registry.get_entry('advisor_consult') is not None and c and 'reviewed' in r and seen[0][1]['request_id'] == 'session-final:turn-final:advisor'
