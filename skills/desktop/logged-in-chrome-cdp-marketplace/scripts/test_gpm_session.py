import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cdp_eval import cdp_call, cdp_eval

async def test_session(ws_url):
    expr = "document.title"
    title = await cdp_eval(ws_url, expr)
    print("Page title:", title)

    # Navigate to myaccount
    await cdp_call(ws_url, "Page.navigate", {"url": "https://myaccount.google.com/?hl=vi"})
    await asyncio.sleep(4)

    info = await cdp_eval(ws_url, "({ url: window.location.href, title: document.title, text: document.body.innerText.slice(0, 300) })")
    print("Account check:", info)

if __name__ == '__main__':
    ws = sys.argv[1]
    asyncio.run(test_session(ws))
