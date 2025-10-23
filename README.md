# AI Impact (Windows, Local Only) — v3

- Machine-wide capture via **mitmproxy** or Chrome-only via **Playwright/CDP**.
- **Chunky pixel-art evergreen + flames** tray icon.
- **Live updates for ChatGPT**: WebSocket traffic commits every ~2KB or after ~2s idle — no need to close the tab.

## Quick start
1) Create venv and install deps:

```bash
python -m venv .venv
```
on PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

or on bash:
```bash
source ./.venv/Scripts/activate
```

then (on any terminal)
```
pip install -r requirements.txt
```

2A) Proxy mode (recommended)
```powershell
mitmdump -s proxy_addon.py --set block_global=false
```
Set Windows proxy to 127.0.0.1:8080 for HTTP+HTTPS. Install mitmproxy cert via http://mitm.it.

2B) Chrome-only
```powershell
python -m playwright install chrome
python watch_chrome.py
```

3) Tray app
```powershell
python tray_app.py
```

4) Totals
```powershell
python cli.py
```
Mermaid diagram of codebase:
```mermaid
graph LR
  subgraph Onceler
    TA[tray_app.TrayApp]
    TA_DRAW[tray_app icon/draw helpers]
    ST[storage.DB / Hit]
    IM[impact.estimate_impact / CFG]
    PRS[parsers.tokens_in_from_body / tokens_out_from_len]
    DET[detectors.ProviderRules]
    PA[proxy_addon handlers]
    WC[watch_chrome.main]
    CLI[cli.totals]
    RULES[rules.json]
    CONF[config.json]
  end

  %% ensure 'end' is on its own line (blank line above) so parsers don't see "end TA" tokens
  TA --> ST    %% Tray app uses DB.totals and DB path
  TA --> IM    %% Tray app reads CFG from impact
  TA --> TA_DRAW

  PA --> DET   %% proxy_addon matches providers
  PA --> PRS   %% proxy_addon uses parsers
  PA --> IM    %% proxy_addon calls estimate_impact
  PA --> ST    %% proxy_addon writes Hit via DB.insert
  PA --> PA_WS[websocket helpers/_ws_commit_if_needed]

  WC --> DET   %% watch_chrome uses ProviderRules
  WC --> PRS   %% watch_chrome uses parsers for requests/responses
  WC --> IM    %% watch_chrome calls estimate_impact
  WC --> ST    %% watch_chrome inserts hits

  DET --> RULES %% ProviderRules loads rules.json
  IM --> CONF   %% impact.CFG merges config.json

  CLI --> ST    %% cli.totals queries sqlite directly
```