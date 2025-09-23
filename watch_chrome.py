import asyncio, time
from playwright.async_api import async_playwright
from pathlib import Path
from detectors import ProviderRules
from parsers import tokens_in_from_body, tokens_out_from_len
from impact import estimate_impact
from storage import DB, Hit

RULES = ProviderRules("rules.json")
DBH = DB()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            args=["--disable-quic"]
        )
        ctx = await browser.new_context()
        page = await ctx.new_page()

        async def on_request(req):
            prov = RULES.match(req.url)
            if prov:
                req._ai_provider = prov
                try:
                    body = (req.post_data() or "").encode("utf-8","ignore")
                except Exception:
                    body = b""
                req._ai_tokens_in = tokens_in_from_body(body)

        async def on_response(res):
            req = res.request
            prov = getattr(req, "_ai_provider", None)
            if not prov:
                return
            tokens_out = 0
            try:
                body = await res.body()
                tokens_out = tokens_out_from_len(len(body))
            except Exception:
                pass
            tokens_in = int(getattr(req, "_ai_tokens_in", 0))
            im = estimate_impact(tokens_in, tokens_out, model_name=None)
            DBH.insert(Hit(
                ts_ms=int(time.time()*1000),
                url=req.url, provider=prov,
                tokens_in=tokens_in, tokens_out=tokens_out,
                kwh=im.kwh, gco2=im.gco2, liters=im.liters
            ))

        page.on("request", on_request)
        page.on("response", on_response)
        await page.goto("https://www.google.com")
        await page.wait_for_timeout(10**10)

if __name__ == "__main__":
    asyncio.run(main())
