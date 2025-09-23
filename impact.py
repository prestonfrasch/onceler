from dataclasses import dataclass
from pathlib import Path
import json
from typing import Optional

_DEFAULT_CFG = {
    "grid_gco2_per_kwh": 400.0,
    "liters_per_kwh": 0.5,
    "energy_kwh_per_1k_tokens": {"default": 0.003, "large": 0.010},
    "tree_gco2_per_day": 21800.0/365.0,
}

def _load_cfg(path: str | Path = "config.json"):
    p = Path(path)
    if p.exists():
        try:
            data = json.loads(p.read_text())
            merged = _DEFAULT_CFG | data
            merged["energy_kwh_per_1k_tokens"] = _DEFAULT_CFG["energy_kwh_per_1k_tokens"] | data.get("energy_kwh_per_1k_tokens", {})
            return merged
        except Exception:
            pass
    return _DEFAULT_CFG

CFG = _load_cfg()

@dataclass
class Impact:
    kwh: float
    gco2: float
    liters: float

def pick_model_class(model_name: Optional[str]) -> str:
    if not model_name:
        return "default"
    n = model_name.lower()
    return "large" if any(k in n for k in ["gpt-4", "llama-70", "sonnet", "command-r+", "mixtral-8x7"]) else "default"

def estimate_impact(tokens_in: int, tokens_out: int, model_name: Optional[str] = None) -> Impact:
    cls = pick_model_class(model_name)
    per_1k = CFG["energy_kwh_per_1k_tokens"].get(cls, CFG["energy_kwh_per_1k_tokens"]["default"])
    kwh = per_1k * ((tokens_in + tokens_out) / 1000.0)
    gco2 = kwh * CFG["grid_gco2_per_kwh"]
    liters = kwh * CFG["liters_per_kwh"]
    return Impact(kwh=kwh, gco2=gco2, liters=liters)
