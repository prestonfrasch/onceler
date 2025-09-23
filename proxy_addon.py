from mitmproxy import http, websocket, ctx
import time
from detectors import ProviderRules
from parsers import tokens_in_from_body, tokens_out_from_len
from impact import estimate_impact
from storage import DB, Hit

RULES = ProviderRules("rules.json")
DBH = DB("ai_impact.sqlite")

WS_COMMIT_MIN_DELTA_BYTES = 2048
WS_COMMIT_MAX_IDLE_SEC    = 2.0

def _record_hit(url: str, provider: str, tokens_in: int, tokens_out: int):
    im = estimate_impact(tokens_in, tokens_out, model_name=None)
    DBH.insert(Hit(
        ts_ms=int(time.time()*1000),
        url=url,
        provider=provider,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        kwh=im.kwh, gco2=im.gco2, liters=im.liters
    ))

def request(flow: http.HTTPFlow):
    provider = RULES.match(flow.request.pretty_url)
    if provider:
        flow.metadata["ai_provider"] = provider
        flow.metadata["ai_tokens_in"] = tokens_in_from_body(flow.request.raw_content or b"")

def response(flow: http.HTTPFlow):
    provider = flow.metadata.get("ai_provider")
    if not provider:
        return

    ctype = (flow.response.headers.get("Content-Type", "") or "").lower()
    if "text/event-stream" in ctype:
        content_len = len(flow.response.raw_content or b"")
    else:
        try:
            content_len = int(flow.response.headers.get("Content-Length", "0"))
        except Exception:
            content_len = 0

    tokens_out = tokens_out_from_len(content_len)
    tokens_in  = int(flow.metadata.get("ai_tokens_in", 0))
    _record_hit(flow.request.pretty_url, provider, tokens_in, tokens_out)

def websocket_start(flow: http.HTTPFlow):
    provider = RULES.match(flow.request.pretty_url)
    if provider:
        flow.metadata["ai_provider_ws"] = provider
        flow.metadata["ai_ws_in_bytes"] = 0
        flow.metadata["ai_ws_out_bytes"] = 0
        flow.metadata["ai_ws_last_commit_out"] = 0
        flow.metadata["ai_ws_last_commit_in"] = 0
        flow.metadata["ai_ws_last_commit_ts"] = time.time()

def _ws_commit_if_needed(flow: http.HTTPFlow, force: bool = False):
    provider = flow.metadata.get("ai_provider_ws")
    if not provider:
        return
    now = time.time()
    last_ts = flow.metadata.get("ai_ws_last_commit_ts", now)
    out_b = int(flow.metadata.get("ai_ws_out_bytes", 0))
    in_b  = int(flow.metadata.get("ai_ws_in_bytes", 0))
    last_out = int(flow.metadata.get("ai_ws_last_commit_out", 0))
    last_in  = int(flow.metadata.get("ai_ws_last_commit_in", 0))

    delta_out = max(0, out_b - last_out)
    delta_in  = max(0, in_b  - last_in)

    idle_ok = (now - last_ts) >= WS_COMMIT_MAX_IDLE_SEC
    size_ok = delta_out + delta_in >= WS_COMMIT_MIN_DELTA_BYTES

    if force or idle_ok or size_ok:
        tokens_in  = max(0, delta_in // 4)
        tokens_out = max(0, delta_out // 4)
        if tokens_in > 0 or tokens_out > 0:
            _record_hit(flow.request.pretty_url, provider, tokens_in, tokens_out)
        flow.metadata["ai_ws_last_commit_out"] = out_b
        flow.metadata["ai_ws_last_commit_in"]  = in_b
        flow.metadata["ai_ws_last_commit_ts"]  = now

def websocket_message(flow: http.HTTPFlow, message: websocket.WebSocketMessage):
    provider = flow.metadata.get("ai_provider_ws")
    if not provider:
        return
    if message.from_client:
        flow.metadata["ai_ws_in_bytes"] = int(flow.metadata.get("ai_ws_in_bytes", 0)) + len(message.content or b"")
    else:
        flow.metadata["ai_ws_out_bytes"] = int(flow.metadata.get("ai_ws_out_bytes", 0)) + len(message.content or b"")
    _ws_commit_if_needed(flow, force=False)

def websocket_end(flow: http.HTTPFlow):
    _ws_commit_if_needed(flow, force=True)
