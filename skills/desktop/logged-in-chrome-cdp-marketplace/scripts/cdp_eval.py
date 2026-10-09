import asyncio
import base64
import json
import os
import sys
import urllib.parse

async def cdp_call(ws_url, method, params=None, timeout=15):
    """Zero-dependency CDP caller using Python stdlib asyncio (RFC 6455 WebSocket)."""
    parsed = urllib.parse.urlparse(ws_url)
    host, port = parsed.hostname, parsed.port or 9222
    path = parsed.path

    reader, writer = await asyncio.open_connection(host, port)
    sec_key = base64.b64encode(os.urandom(16)).decode('utf-8')
    req = (
        f'GET {path} HTTP/1.1\r\n'
        f'Host: {host}:{port}\r\n'
        f'Upgrade: websocket\r\n'
        f'Connection: Upgrade\r\n'
        f'Sec-WebSocket-Key: {sec_key}\r\n'
        f'Sec-WebSocket-Version: 13\r\n\r\n'
    )
    writer.write(req.encode('utf-8'))
    await writer.drain()

    res = b''
    while b'\r\n\r\n' not in res:
        res += await reader.read(1024)

    msg_id = 1
    payload = {'id': msg_id, 'method': method}
    if params:
        payload['params'] = params
    msg_bytes = json.dumps(payload).encode('utf-8')
    length = len(msg_bytes)

    frame = bytearray([0x81])
    if length <= 125:
        frame.append(0x80 | length)
    elif length <= 65535:
        frame.append(0x80 | 126)
        frame.extend(length.to_bytes(2, 'big'))
    else:
        frame.append(0x80 | 127)
        frame.extend(length.to_bytes(8, 'big'))

    mask = os.urandom(4)
    frame.extend(mask)
    for i in range(length):
        frame.append(msg_bytes[i] ^ mask[i % 4])

    writer.write(frame)
    await writer.drain()

    full_payload = bytearray()
    while True:
        try:
            chunk = await asyncio.wait_for(reader.read(65536), timeout=timeout)
            if not chunk:
                break
            full_payload.extend(chunk)
            text = full_payload.decode('utf-8', errors='ignore')
            if f'"id":{msg_id}' in text and ('"result"' in text or '"error"' in text):
                idx = text.find(f'{{"id":{msg_id}')
                if idx != -1:
                    try:
                        obj = json.loads(text[idx:])
                        writer.close()
                        await writer.wait_closed()
                        return obj
                    except Exception:
                        pass
        except asyncio.TimeoutError:
            break

    writer.close()
    await writer.wait_closed()
    return None

async def cdp_eval(ws_url, expr, timeout=15):
    res = await cdp_call(ws_url, 'Runtime.evaluate', {'expression': expr, 'awaitPromise': True, 'returnByValue': True}, timeout)
    if res and 'result' in res:
        return res['result'].get('result', {}).get('value')
    return None

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python cdp_eval.py <ws_url> <js_expression>")
        sys.exit(1)
    ws_url = sys.argv[1]
    expr = sys.argv[2]
    val = asyncio.run(cdp_eval(ws_url, expr))
    print(json.dumps(val, indent=2, ensure_ascii=False))
