import pytest
import logging
from agent.shell_hooks import _parse_response
from hermes_cli.plugins import _get_pre_tool_call_directive_details

def test_parse_response_rewrite():
    raw_json = '{"action": "rewrite", "updated_args": {"timeout": 60}, "notice": "auto-timeout"}'
    res = _parse_response('pre_tool_call', raw_json)
    assert res is not None
    assert res.get('action') == 'rewrite'
    assert res.get('updated_args') == {'timeout': 60}
    assert res.get('notice') == 'auto-timeout'

def test_parse_response_rewrite_legacy_input_key():
    raw_json = '{"action": "rewrite", "updated_input": {"offset": 100, "limit": 200}}'
    res = _parse_response('pre_tool_call', raw_json)
    assert res is not None
    assert res.get('action') == 'rewrite'
    assert res.get('updated_args') == {'offset': 100, 'limit': 200}

def test_parse_response_rewrite_precedence():
    # updated_args takes precedence over updated_input
    raw_json = '{"action": "rewrite", "updated_args": {"a": 1}, "updated_input": {"a": 2, "b": 3}}'
    res = _parse_response('pre_tool_call', raw_json)
    assert res is not None
    assert res.get('updated_args') == {'a': 1}

def test_parse_response_rewrite_malformed_type():
    # non-dict updated_args should safely fallback to empty dict
    raw_json = '{"action": "rewrite", "updated_args": "invalid_string", "notice": 123}'
    res = _parse_response('pre_tool_call', raw_json)
    assert res is not None
    assert res.get('action') == 'rewrite'
    assert res.get('updated_args') == {}
    assert res.get('notice') is None

def test_plugins_pre_tool_call_rewrite_mutates_args(monkeypatch, caplog):
    def mock_invoke_hook(event, **kwargs):
        if event == 'pre_tool_call':
            return [{'action': 'rewrite', 'updated_args': {'timeout': 60, 'injected': True}, 'notice': 'auto-inject'}]
        return []
    import hermes_cli.plugins as hp
    monkeypatch.setattr(hp, 'invoke_hook', mock_invoke_hook)

    args = {'command': 'ls -la'}
    with caplog.at_level(logging.INFO):
        directive = _get_pre_tool_call_directive_details('terminal', args)
    assert directive.action is None
    assert args.get('timeout') == 60
    assert args.get('injected') is True
    assert any("Hook rewritten arguments: auto-inject" in rec.message for rec in caplog.records)

def test_parse_response_rewrite_empty_dict_precedence():
    # When updated_args is present as empty dict, it should not fallback to updated_input
    raw_json = '{"action": "rewrite", "updated_args": {}, "updated_input": {"timeout": 30}}'
    res = _parse_response('pre_tool_call', raw_json)
    assert res is not None
    assert res.get('action') == 'rewrite'
    assert res.get('updated_args') == {}

def test_plugins_pre_tool_call_multiple_hooks_rewrite(monkeypatch, caplog):
    # Multiple hooks sequentially mutating args
    def mock_invoke_hook(event, **kwargs):
        if event == 'pre_tool_call':
            return [
                {'action': 'rewrite', 'updated_args': {'timeout': 60}, 'notice': 'inject-timeout'},
                {'action': 'rewrite', 'updated_args': {'workdir': '/tmp'}, 'notice': 'inject-workdir'},
            ]
        return []
    import hermes_cli.plugins as hp
    monkeypatch.setattr(hp, 'invoke_hook', mock_invoke_hook)

    args = {'command': 'pytest'}
    with caplog.at_level(logging.INFO):
        directive = _get_pre_tool_call_directive_details('terminal', args)
    assert directive.action is None
    assert args == {'command': 'pytest', 'timeout': 60, 'workdir': '/tmp'}
