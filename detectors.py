import json
from pathlib import Path
from urllib.parse import urlparse

class ProviderRules:
    def __init__(self, rules_path: str | Path = "rules.json"):
        self.providers = json.loads(Path(rules_path).read_text())["providers"]

    def match(self, url: str):
        up = urlparse(url)
        host_path = f"{up.netloc}{up.path}".lower()
        for p in self.providers:
            for pat in p["patterns"]:
                if pat.lower() in host_path:
                    return p["name"]
        return None
