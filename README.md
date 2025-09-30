# AI Impact (Windows, Local Only) — v3

- Machine-wide capture via **mitmproxy** or Chrome-only via **Playwright/CDP**.
- **Chunky pixel-art evergreen + flames** tray icon.
- **Live updates for ChatGPT**: WebSocket traffic commits every ~2KB or after ~2s idle — no need to close the tab.

## Quick start
1) Create venv and install deps:
#any terminal
```
python -m venv .venv
```

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
source ./.venv/Scripts/activate
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
